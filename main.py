import uuid
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from enum import StrEnum

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from config import settings
from database import async_engine
from dependencies import SessionDep
from enums import PostStatus
from middleware import RequestBodySizeLimitMiddleware
from models import Post
from routers import bookmarks, comments, feeds, follows, likes, posts, tags, users
from schemas.posts import PostListParams, PostSortField
from services import posts as posts_service
from services import users as users_service


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # startup

    # For SQLite:
    # async with async_engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

    yield
    # shutdown
    await async_engine.dispose()


class Tags(StrEnum):
    users = "users"
    posts = "posts"
    comments = "comments"
    likes = "likes"
    tags = "tags"
    bookmarks = "bookmarks"
    follows = "follows"
    feeds = "feeds"


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    RequestBodySizeLimitMiddleware,
    max_body_size=settings.max_upload_size_bytes + 1024 * 1024,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://ui.cryptids.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")

app.include_router(users.router, tags=[Tags.users])
app.include_router(posts.router, tags=[Tags.posts])
app.include_router(comments.post_comments_router, tags=[Tags.comments])
app.include_router(comments.comments_router, tags=[Tags.comments])
app.include_router(likes.router, tags=[Tags.likes])
app.include_router(tags.router, tags=[Tags.tags])
app.include_router(bookmarks.router, tags=[Tags.bookmarks])
app.include_router(follows.router, tags=[Tags.follows])
app.include_router(feeds.router, tags=[Tags.feeds])

# ---------------- Auth pages ------------------


@app.get("/login", include_in_schema=False, name="login")
async def login_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "login.html", {"title": "Login"})


@app.get("/register", include_in_schema=False, name="register")
async def register_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "register.html", {"title": "Register"})


@app.get("/account", include_in_schema=False, name="account")
async def account_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "account.html", {"title": "Account"})


@app.get("/forgot-password", include_in_schema=False)
async def forgot_password_page(request: Request) -> Response:
    return templates.TemplateResponse(
        request,
        "forgot_password.html",
        {"title": "Forgot Password"},
    )


@app.get("/reset-password", include_in_schema=False)
async def reset_password_page(request: Request) -> Response:
    response = templates.TemplateResponse(
        request,
        "reset_password.html",
        {"title": "Reset Password"},
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


# ---------------- Exception handlers ------------------


@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException) -> Response:
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

    message = exception.detail if exception.detail else "An error occurred. Please check your request and try again."

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError) -> Response:
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Invalid request. Please check your input and try again",
    )


# ---------------- Web pages ------------------


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(request: Request, session: SessionDep) -> Response:
    filter_query = PostListParams(
        limit=settings.posts_per_page, skip=0, order_by=PostSortField.CREATED_AT, order_direction="desc"
    )
    total_count = await posts_service.count_posts(session, filter_query)
    posts: Sequence[Post] = await posts_service.list_posts(session, filter_query)

    has_more = len(posts) < total_count
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "posts": posts,
            "title": "Home",
            "limit": settings.posts_per_page,
            "has_more": has_more,
        },
    )


@app.get("/posts/{post_id}", include_in_schema=False, name="post")
async def post_page(post_id: uuid.UUID, request: Request, session: SessionDep) -> Response:
    post = await posts_service.get_post_for_response(session, post_id)
    if post and post.status is PostStatus.PUBLISHED:
        return templates.TemplateResponse(request, "post.html", {"post": post, "title": post.title})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(request: Request, user_id: uuid.UUID, session: SessionDep) -> Response:
    user = await users_service.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    total_count = await posts_service.count_posts_by_user_id(session, user_id, is_owner=False)
    user_posts = await posts_service.get_posts_by_user_id(
        session, user_id, is_owner=False, limit=settings.posts_per_page
    )

    has_more = len(user_posts) < total_count

    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {
            "posts": user_posts,
            "user": user,
            "title": f"{user.username}'s Posts",
            "limit": settings.posts_per_page,
            "has_more": has_more,
        },
    )
