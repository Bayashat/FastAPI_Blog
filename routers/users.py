import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from auth import (
    CurrentUser,
    create_access_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from config import settings
from dependencies import SessionDep
from email_utils import send_password_reset_email
from image_utils import delete_profile_image, process_profile_image
from models import User
from models.posts import Post
from schemas.posts import PostResponseWithoutAuthor, UserPostsResponse
from schemas.reset_tokens import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from schemas.users import Token, UserCreate, UserPrivate, UserPublic, UserUpdate
from services.posts import count_posts_by_user_id, get_posts_by_user_id
from services.pwd_reset_token import (
    create_reset_token,
    delete_existing_tokens,
    get_reset_token_by_hash,
)
from services.users import create_user as create_user_service
from services.users import delete_user as delete_user_service
from services.users import get_user_by_email, get_user_by_id, get_user_by_username
from services.users import update_user as update_user_service
from services.users import user_exists_by_username_or_email

router = APIRouter(prefix="/api/users")
logger = logging.getLogger(__name__)

ALLOWED_PROFILE_IMAGE_CONTENT_TYPES = {
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/webp",
}


def invalid_reset_token_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired reset token",
    )


def user_conflict_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Username or email is already in use",
    )


async def delete_profile_image_safely(file_name: str | None) -> None:
    if not file_name:
        return
    try:
        await run_in_threadpool(delete_profile_image, file_name)
    except OSError:
        logger.exception("Failed to delete profile image %s", file_name)


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, session: SessionDep) -> UserPublic:
    if await user_exists_by_username_or_email(session, user.username, user.email):
        raise user_conflict_exception()
    user.password = await run_in_threadpool(hash_password, user.password)
    try:
        new_user = await create_user_service(session, user)
    except IntegrityError as err:
        await session.rollback()
        raise user_conflict_exception() from err
    return new_user


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep
) -> Token:
    # Note: OAuth2PasswordRequestForm uses "username" field, but we treat it as email
    user: User | None = await get_user_by_email(session, form_data.username.strip().lower())

    # Don't reveal which one failed (security best practice)
    if not user or not await run_in_threadpool(
        verify_password,
        plain_password=form_data.password,
        hashed_password=user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token with user id as subject
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserPrivate)
async def get_me(user: CurrentUser) -> User:
    return user


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    request_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
):
    user = await get_user_by_email(session, request_data.email)
    if user:
        token = generate_reset_token()
        token_hash = hash_reset_token(token)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.reset_token_expire_minutes,
        )

        await create_reset_token(session, user.id, token_hash, expires_at)

        background_tasks.add_task(
            send_password_reset_email,
            to_email=user.email,
            username=user.username,
            token=token,
            expire_minutes=settings.reset_token_expire_minutes,
        )
    return {
        "message": "If an account exists with this email, you will receive password reset instructions.",
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request_data: ResetPasswordRequest,
    session: SessionDep,
):
    token_hash = hash_reset_token(request_data.token)
    now = datetime.now(UTC)

    reset_token = await get_reset_token_by_hash(session, token_hash)
    if not reset_token:
        raise invalid_reset_token_exception()
    if reset_token.expires_at < now:
        await session.delete(reset_token)
        await session.commit()
        raise invalid_reset_token_exception()

    user = await get_user_by_id(session, reset_token.user_id)
    if not user:
        # delete reset_token if user doesn't exist
        await session.delete(reset_token)
        await session.commit()
        raise invalid_reset_token_exception()

    user.password_hash = await run_in_threadpool(hash_password, request_data.new_password)
    await delete_existing_tokens(session, user.id)
    await session.commit()

    return {
        "message": "Password reset successfully. You can now log in with your new password.",
    }


@router.patch("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    session: SessionDep,
    user: CurrentUser,
    password_data: ChangePasswordRequest,
) -> dict[str, str]:
    if not await run_in_threadpool(verify_password, password_data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if password_data.current_password == password_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )
    user.password_hash = await run_in_threadpool(hash_password, password_data.new_password)

    await delete_existing_tokens(session, user.id)
    await session.commit()

    return {"message": "Password changed successfully"}


@router.patch("/me", response_model=UserPrivate)
async def update_user(
    session: SessionDep,
    current_user: CurrentUser,
    user_update: UserUpdate,
) -> User:
    if user_update.username is not None and user_update.username.lower() != current_user.username.lower():
        if await get_user_by_username(session, user_update.username):
            raise user_conflict_exception()
    if user_update.email is not None and user_update.email.lower() != current_user.email.lower():
        if await get_user_by_email(session, user_update.email):
            raise user_conflict_exception()

    try:
        updated_user = await update_user_service(session, user_update, current_user)
    except IntegrityError as err:
        await session.rollback()
        raise user_conflict_exception() from err
    return updated_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(session: SessionDep, user: CurrentUser):
    old_file_name = user.image_file
    await delete_user_service(session, user)

    await delete_profile_image_safely(old_file_name)


@router.patch("/me/picture", response_model=UserPrivate)
async def upload_profile_picture(
    session: SessionDep,
    user: CurrentUser,
    file: UploadFile,
) -> User:
    if file.content_type not in ALLOWED_PROFILE_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file. Please upload a valid image (JPEG, PNG, GIF, WebP).",
        )

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.max_upload_size_bytes // (1024 * 1024)}MB",
        )
    try:
        new_file_name = await run_in_threadpool(process_profile_image, content)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file. Please upload a valid image (JPEG, PNG, GIF, WebP).",
        ) from err

    old_file_name = user.image_file

    user.image_file = new_file_name
    await session.commit()
    await session.refresh(user)

    await delete_profile_image_safely(old_file_name)

    return user


@router.delete("/me/picture", response_model=UserPrivate)
async def delete_user_picture(
    session: SessionDep,
    user: CurrentUser,
) -> User:
    old_file_name = user.image_file

    if not old_file_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile picture to delete",
        )

    user.image_file = None
    await session.commit()
    await session.refresh(user)

    await delete_profile_image_safely(old_file_name)

    return user


@router.get("/{user_id}/posts", response_model=UserPostsResponse)
async def get_user_posts(
    user_id: uuid.UUID,
    session: SessionDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
) -> UserPostsResponse:
    existing_user = await get_user_by_id(session, user_id)
    if not existing_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    total_count = await count_posts_by_user_id(session, user_id)
    user_posts: list[Post] = await get_posts_by_user_id(session, user_id, skip=skip, limit=limit)

    has_more = skip + len(user_posts) < total_count

    return {
        "user": existing_user,
        "posts": user_posts,
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "has_more": has_more,
    }


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(session: SessionDep, user_id: uuid.UUID) -> User:
    user = await get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
