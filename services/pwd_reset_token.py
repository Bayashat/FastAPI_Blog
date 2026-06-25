import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.pwd_reset_tokens import PasswordResetToken


async def delete_existing_tokens(session: AsyncSession, user_id: uuid.UUID) -> None:
    stmt = delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
    await session.execute(stmt)


async def create_reset_token(
    session: AsyncSession,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
) -> PasswordResetToken:
    await delete_existing_tokens(session, user_id)
    reset_token = PasswordResetToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    session.add(reset_token)
    await session.commit()
    return reset_token


async def get_reset_token_by_hash(session: AsyncSession, token_hash: str) -> PasswordResetToken | None:
    stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
