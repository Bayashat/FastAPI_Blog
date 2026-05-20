from curses import resetty
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Path,
    Query,
    UploadFile,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from PIL import UnidentifiedImageError
from sqlalchemy import delete as sql_delete
from sqlalchemy.sql.functions import current_user
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
from models.pwd_reset_tokens import PasswordResetToken
from schemas.posts import PaginatedPostsResponse, PostResponse
from schemas.reset_tokens import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from schemas.users import Token, UserCreate, UserPrivate, UserPublic, UserUpdate
from services.posts import get_all_posts_count_by_user_id, get_posts_by_user_id
from services.pwd_reset_token import delete_existing_tokens, get_reset_token_by_hash
from services.users import create_user as create_user_service
from services.users import delete_user as delete_user_service
from services.users import (
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    get_user_by_username_or_email,
)
from services.users import update_user as update_user_service

router = APIRouter(prefix="/api/users")


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, session: SessionDep):
    existing_user = await get_user_by_username_or_email(session, user.username, user.email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requested user already created")
    new_user = await create_user_service(session, user)
    return new_user


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep):
    # Note: OAuth2PasswordRequestForm uses "username" field, but we treat it as email
    user: User = await get_user_by_email(session, form_data.username)

    # Don't reveal which one failed (security best practice)
    if not user or not verify_password(form_data.password, user.password_hash):
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
async def get_current_user(user: CurrentUser):
    return user


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    request_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
):
    user = await get_user_by_email(session, request_data.email)
    if user:
        await delete_existing_tokens(session, user.id)

        token = generate_reset_token()
        token_hash = hash_reset_token(token)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.reset_token_expire_minutes,
        )

        reset_token = PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
        session.add(reset_token)

        await session.commit()

        background_tasks.add_task(
            send_password_reset_email,
            to_email=user.email,
            username=user.username,
            token=token,
        )
    return {"message": "If an account exists with this email, you will receive password reset instructions."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request_data: ResetPasswordRequest,
    session: SessionDep,
):
    token_hash = hash_reset_token(request_data.token)

    reset_token = await get_reset_token_by_hash(session, token_hash)
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    if reset_token.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        await session.delete(reset_token)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user = await get_user_by_id(session, reset_token.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.password_hash = hash_password(request_data.new_password)

    await delete_existing_tokens(session, user.id)

    await session.commit()
    return {"message": "Password reset succssfully. You can now log in with your new password."}


@router.patch("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    session: SessionDep,
    user: CurrentUser,
    password_data: ChangePasswordRequest,
):
    if not verify_password(password_data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    user.password_hash = hash_password(password_data.new_password)

    await delete_existing_tokens(session, user.id)

    await session.commit()
    return {"message": "Password changed successfully"}


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(session: SessionDep, user_id: int = Path(ge=1)):
    user = await get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserPrivate)
async def update_user(
    session: SessionDep,
    current_user: CurrentUser,
    user: UserUpdate,
    user_id: int = Path(ge=1),
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user",
        )
    if user.username is not None and user.username.lower() != current_user.username.lower():
        if await get_user_by_username(session, user.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )
    if user.email is not None and user.email.lower() != current_user.email.lower():
        if await get_user_by_email(session, user.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists",
            )

    updated_user = await update_user_service(session, user, current_user)
    return updated_user


@router.get("/{user_id}/posts", response_model=PaginatedPostsResponse)
async def get_user_posts(
    user_id: int,
    session: SessionDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
):
    existing_user = await get_user_by_id(session, user_id)
    if not existing_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    total_count = await get_all_posts_count_by_user_id(session, user_id)
    user_posts = await get_posts_by_user_id(session, user_id, skip=skip, limit=limit)

    has_more = skip + len(user_posts) < total_count

    return PaginatedPostsResponse(
        posts=[PostResponse.model_validate(post) for post in user_posts],
        total=total_count,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(session: SessionDep, user: CurrentUser, user_id: int):
    if user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user",
        )
    old_file_name = user.image_file
    if old_file_name:
        delete_profile_image(old_file_name)

    await delete_user_service(session, user)


@router.patch("/{user_id}/picture", response_model=UserPrivate)
async def upload_profile_picture(
    user_id: int,
    session: SessionDep,
    user: CurrentUser,
    file: UploadFile,
):
    if user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's picture",
        )

    content = await file.read()

    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.max_upload_size_bytes // (1024 * 1024)}MB",
        )

    try:
        new_file_name = await run_in_threadpool(process_profile_image, content)
    except UnidentifiedImageError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file. Please upload a valid image (JPEG, PNG, GIF, WebP).",
        ) from err

    old_file_name = user.image_file

    user.image_file = new_file_name
    await session.commit()
    await session.refresh(user)

    if old_file_name:
        delete_profile_image(old_file_name)

    return user


@router.delete("/{user_id}/picture", response_model=UserPrivate)
async def delete_user_picture(
    user_id: int,
    session: SessionDep,
    user: CurrentUser,
):
    if user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's picture",
        )

    old_file_name = user.image_file

    if not old_file_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile picture to delete",
        )

    user.image_file = None
    await session.commit()
    await session.refresh(user)

    delete_profile_image(old_file_name)

    return user
