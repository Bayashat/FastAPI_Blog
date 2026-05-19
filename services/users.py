from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import hash_password
from models import Post, User
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


async def update_user(session: AsyncSession, user: UserUpdate, current_user: User) -> User | None:
    update_data = user.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(current_user, k, v)

    await session.commit()
    await session.refresh(current_user)
    return current_user


async def delete_user(session: AsyncSession, user: User) -> None:
    await session.delete(user)
    await session.commit()
