from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import hash_password
from models import Post, User
from models.pwd_reset_tokens import PasswordResetToken
from schemas.users import UserCreate, UserUpdate


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.get(User, user_id)
    return result


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    stmt = select(User).where(func.lower(User.username) == username.lower())
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email.lower())
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def delete_existing_tokens(session: AsyncSession, user_id: int):
    stmt = delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
    await session.execute(stmt)


async def get_reset_token_by_hash(session: AsyncSession, token_hash: str):
    stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
