from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import settings
from database import Base, async_engine
from dependencies import SessionDep
from models import Post
from routers import posts, users
from services import posts as posts_service
from services import users as users_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # startup
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # shutdown
    await async_engine.dispose()


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")

app.include_router(users.router, tags=["users"])
app.include_router(posts.router, tags=["posts"])

# ---------------- Auth pages ------------------


@app.get("/login", include_in_schema=False, name="login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"title": "Login"})


@app.get("/register", include_in_schema=False, name="register")
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"title": "Register"})


@app.get("/account", include_in_schema=False, name="account")
async def register_page(request: Request):
    return templates.TemplateResponse(request, "account.html", {"title": "Account"})


# ---------------- Exception handlers ------------------


@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
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
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Invalid request. Please check your input and try again",
    )


# ---------------- Web pages ------------------


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(request: Request, session: SessionDep):
    total_count = await posts_service.get_all_posts_count(session)
    posts: list[Post] = await posts_service.list_posts_ordered(session, limit=settings.posts_per_page)

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
async def post_page(post_id: int, request: Request, session: SessionDep):
    post = await posts_service.get_post_by_id(session, post_id)
    if post:
        return templates.TemplateResponse(request, "post.html", {"post": post, "title": post.title})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(request: Request, user_id: int, session: SessionDep):
    user = await users_service.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    total_count = await posts_service.get_all_posts_count_by_user_id(session, user_id)
    user_posts = await posts_service.get_posts_by_user_id(session, user_id, limit=settings.posts_per_page)

    has_more = len(user_posts) < total_count

    result = await posts_service.get_posts_by_user_id(session, user_id)
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {
            "posts": result,
            "user": user,
            "title": f"{user.username}'s Posts",
            "limit": settings.posts_per_page,
            "has_more": has_more,
        },
    )
