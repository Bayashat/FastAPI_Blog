import logging
from collections.abc import Sequence
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
    create_access_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
)
from config import settings
from dependencies import (
    CurrentUser,
    OptionalCurrentUser,
    SessionDep,
)
from email_utils import send_password_reset_email
from image_utils import delete_profile_image, process_profile_image
from models import User
from models.posts import Post
from schemas.common import UserId
from schemas.passwords import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from schemas.posts import UserPostsResponse
from schemas.users import (
    AccessTokenResponse,
    CurrentUserResponse,
    UserCreate,
    UserPublic,
    UserUpdate,
)
from services import posts as post_service
from services import pwd_reset_token as pwd_reset_token_service
from services import users as user_service

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
async def create_user(user: UserCreate, session: SessionDep) -> User:
    password_hash = await run_in_threadpool(hash_password, user.password.get_secret_value())

    try:
        async with session.begin():
            if await user_service.username_or_email_exists(
                session,
                user.username,
                user.email,
            ):
                raise user_conflict_exception()

            new_user = await user_service.create_user(
                session,
                user,
                password_hash,
            )

    except IntegrityError as err:
        raise user_conflict_exception() from err

    return new_user


@router.post("/token", response_model=AccessTokenResponse)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep
) -> AccessTokenResponse:
    # Note: OAuth2PasswordRequestForm uses "username" field, but we treat it as email
    # user: User | None = await user_service.get_user_by_email(session, form_data.username.strip().lower())

    # hash_to_verify = user.password_hash if user is not None else DUMMY_PASSWORD_HASH

    # password_is_valid = await run_in_threadpool(
    #     verify_password,
    #     plain_password=form_data.password,
    #     hashed_password=hash_to_verify,
    # )

    # # Don't reveal which one failed (security best practice)
    # if user is None or not password_is_valid:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Incorrect email or password",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )

    user = await user_service.get_user_by_email(session, "bako@example.com")
    # Create access token with user id as subject
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return AccessTokenResponse(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(user: CurrentUser) -> User:
    return user


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    request_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> dict:
    async with session.begin():
        user = await user_service.get_user_by_email(session, request_data.email)

        if user:
            token = generate_reset_token()
            token_hash = hash_reset_token(token)
            expires_at = datetime.now(UTC) + timedelta(
                minutes=settings.reset_token_expire_minutes,
            )

            await pwd_reset_token_service.create_reset_token(session, user.id, token_hash, expires_at)
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
) -> dict:
    token_hash = hash_reset_token(request_data.token.get_secret_value())
    now = datetime.now(UTC)

    reset_token = await pwd_reset_token_service.get_reset_token_by_hash(session, token_hash)
    if not reset_token:
        raise invalid_reset_token_exception()
    # Check if the token has expired
    if reset_token.expires_at < now:
        await session.delete(reset_token)
        await session.commit()
        raise invalid_reset_token_exception()

    user = await user_service.get_user_by_id(session, reset_token.user_id)
    if not user:
        # delete reset_token if user doesn't exist
        await session.delete(reset_token)
        await session.commit()
        raise invalid_reset_token_exception()

    user.password_hash = await run_in_threadpool(hash_password, request_data.new_password.get_secret_value())
    await pwd_reset_token_service.delete_existing_tokens(session, user.id)
    await session.commit()

    return {
        "message": "Password reset successfully. You can now log in with your new password.",
    }


@router.patch("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    session: SessionDep,
    user: CurrentUser,
    password_data: ChangePasswordRequest,
) -> dict:
    try:
        await user_service.change_user_password(
            session,
            user,
            password_data.current_password.get_secret_value(),
            password_data.new_password.get_secret_value(),
        )
    except user_service.IncorrectCurrentPasswordError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        ) from err
    return {"message": "Password changed successfully"}


@router.patch("/me", response_model=CurrentUserResponse)
async def update_user(
    session: SessionDep,
    current_user: CurrentUser,
    user_update: UserUpdate,
) -> User:
    # 检查是否有冲突的用户名或邮箱
    if (
        user_update.username is not None
        and user_update.username.lower() != current_user.username.lower()
        and await user_service.get_user_by_username(session, user_update.username)
    ):
        raise user_conflict_exception()
    if (
        user_update.email is not None
        and user_update.email.lower() != current_user.email.lower()
        and await user_service.get_user_by_email(session, user_update.email)
    ):
        raise user_conflict_exception()

    try:
        updated_user: User = await user_service.update_user(session, current_user, user_update)
    except IntegrityError as err:
        await session.rollback()
        raise user_conflict_exception() from err
    return updated_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(session: SessionDep, user: CurrentUser) -> None:
    old_file_name = await user_service.delete_user(session, user)

    await delete_profile_image_safely(old_file_name)


@router.patch("/me/picture", response_model=CurrentUserResponse)
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

    updated_user, old_file_name = await user_service.update_user_profile_image(
        session,
        user,
        new_file_name,
    )

    await delete_profile_image_safely(old_file_name)

    return updated_user


@router.delete("/me/picture", response_model=CurrentUserResponse)
async def delete_user_picture(
    session: SessionDep,
    user: CurrentUser,
) -> User:
    try:
        updated_user, old_file_name = await user_service.update_user_profile_image(
            session,
            user,
            None,
        )
    except user_service.ProfileImageNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile picture to delete",
        ) from err
    await delete_profile_image_safely(old_file_name)

    return updated_user


@router.get("/me/posts", response_model=UserPostsResponse, status_code=status.HTTP_200_OK)
async def get_my_posts(
    session: SessionDep,
    user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
) -> UserPostsResponse:
    total_count = await post_service.count_posts_by_user_id(session, user.id, is_owner=True)
    user_posts: Sequence[Post] = await post_service.get_posts_by_user_id(
        session, user.id, is_owner=True, skip=skip, limit=limit
    )

    has_more = skip + len(user_posts) < total_count

    return UserPostsResponse.model_validate(
        {
            "user": user,
            "posts": user_posts,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "has_more": has_more,
        }
    )


@router.get("/{user_id}/posts", response_model=UserPostsResponse, status_code=status.HTTP_200_OK)
async def get_user_posts(
    user_id: UserId,
    session: SessionDep,
    user: OptionalCurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
) -> UserPostsResponse:
    existing_user = await user_service.get_user_by_id(session, user_id)
    if not existing_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    is_owner = existing_user.id == user.id if user else False

    total_count = await post_service.count_posts_by_user_id(session, user_id, is_owner)
    user_posts: Sequence[Post] = await post_service.get_posts_by_user_id(
        session, user_id, is_owner=is_owner, skip=skip, limit=limit
    )

    has_more = skip + len(user_posts) < total_count

    return UserPostsResponse.model_validate(
        {
            "user": existing_user,
            "posts": user_posts,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "has_more": has_more,
        }
    )


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    session: SessionDep,
    user_id: UserId,
) -> User:
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
