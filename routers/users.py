from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.security import OAuth2PasswordRequestForm

from auth import CurrentUser, create_access_token, verify_password
from config import settings
from dependencies import SessionDep
from models import User
from schemas.posts import PostResponse
from schemas.users import Token, UserCreate, UserPrivate, UserPublic, UserUpdate
from services.posts import get_posts_by_user_id
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reuqested user already created")
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


@router.get("/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, session: SessionDep):
    existing_user = await get_user_by_id(session, user_id)
    if not existing_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    posts = await get_posts_by_user_id(session, user_id)
    return posts


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(session: SessionDep, user: CurrentUser, user_id: int):
    if user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user",
        )
    await delete_user_service(session, user)
