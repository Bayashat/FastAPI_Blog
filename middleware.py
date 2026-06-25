from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_size: int) -> None:
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = self._content_length(scope)
        if content_length is not None and content_length > self.max_body_size:
            await self._send_too_large(scope, receive, send)
            return

        received_size = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received_size

            message = await receive()
            if message["type"] == "http.request":
                received_size += len(message.get("body", b""))
                if received_size > self.max_body_size:
                    raise RequestBodyTooLargeError
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started

            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except RequestBodyTooLargeError:
            if not response_started:
                await self._send_too_large(scope, receive, send)

    @staticmethod
    def _content_length(scope: Scope) -> int | None:
        headers = dict(scope["headers"])
        raw_content_length = headers.get(b"content-length")
        if raw_content_length is None:
            return None
        try:
            return int(raw_content_length)
        except ValueError:
            return None

    @staticmethod
    async def _send_too_large(scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            {"detail": "Request body too large"},
            status_code=413,
        )
        await response(scope, receive, send)


class RequestBodyTooLargeError(Exception):
    pass
