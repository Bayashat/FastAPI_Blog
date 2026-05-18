from fastapi import status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import hash_password, password_hash
from models import User
from schemas.users import UserCreate, UserUpdate


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.get(User, user_id)
    return result


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    stmt = select(User).where(func.lower(User.username) == username.lower())
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(func.lower(User.email) == email.lower())
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_username_or_email(session: AsyncSession, username: str, email: str) -> User | None:
    stmt = select(User).where(
        or_(func.lower(User.username) == username.lower(), func.lower(User.email) == email.lower())
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, user: UserCreate) -> User:
    new_user = User(username=user.username, email=user.email.lower(), password_hash=hash_password(user.password))
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


async def update_user(session: AsyncSession, user: UserUpdate, user_id: int) -> User | None:
    existing_user = await get_user_by_id(session, user_id)
    if not existing_user:
        return None

    if user.username is not None and user.username.lower() != existing_user.username.lower():
        if await get_user_by_username(session, user.username):
            raise ValueError("Username already exists")

    if user.email is not None and user.email.lower() != existing_user.email.lower():
        if await get_user_by_email(session, user.email):
            raise ValueError("Email already registered")

    update_data = user.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(existing_user, k, v)

    await session.commit()
    return existing_user


async def delete_user(session: AsyncSession, user_id: int) -> None:
    existing_user = await get_user_by_id(session, user_id)
    if not existing_user:
        raise ValueError("User not found")
    await session.delete(existing_user)
    await session.commit()
