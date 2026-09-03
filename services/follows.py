from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from models.follows import Follow
from models.users import User
from schemas.common import UserId


async def follow_user(
    session: AsyncSession,
    follower_id: UserId,
    followed_user_id: UserId,
) -> None:
    stmt = (
        insert(Follow)
        .values(
            follower_id=follower_id,
            followed_user_id=followed_user_id,
        )
        .on_conflict_do_nothing(
            index_elements=[
                Follow.follower_id,
                Follow.followed_user_id,
            ]
        )
    )
    await session.execute(stmt)
    await session.commit()


async def unfollow_user(
    session: AsyncSession,
    follower_id: UserId,
    followed_user_id: UserId,
) -> None:
    stmt = delete(Follow).where(
        Follow.follower_id == follower_id,
        Follow.followed_user_id == followed_user_id,
    )
    await session.execute(stmt)
    await session.commit()


# 查询谁关注了目标用户
async def list_followers(
    session: AsyncSession,
    user_id: UserId,
) -> Sequence[User]:
    stmt = (
        select(User)
        .options(
            load_only(
                User.id,
                User.username,
                User.image_file,
            )
        )
        .join(
            Follow,
            Follow.follower_id == User.id,
        )
        .where(
            Follow.followed_user_id == user_id,
        )
        .order_by(
            Follow.followed_at.desc(),
            Follow.follower_id.desc(),
        )
    )
    return (await session.scalars(stmt)).all()


async def count_followers(
    session: AsyncSession,
    user_id: UserId,
) -> int:
    stmt = (
        select(func.count())
        .select_from(Follow)
        .where(
            Follow.followed_user_id == user_id,
        )
    )
    return (await session.execute(stmt)).scalar_one()


# 查询目标用户关注了谁
async def list_followed_users(
    session: AsyncSession,
    user_id: UserId,
) -> Sequence[User]:
    stmt = (
        select(User)
        .options(
            load_only(
                User.id,
                User.username,
                User.image_file,
            )
        )
        .join(
            Follow,
            Follow.followed_user_id == User.id,
        )
        .where(
            Follow.follower_id == user_id,
        )
        .order_by(
            Follow.followed_at.desc(),
            Follow.followed_user_id.desc(),
        )
    )
    return (await session.scalars(stmt)).all()


async def count_followed_users(
    session: AsyncSession,
    user_id: UserId,
) -> int:
    stmt = (
        select(func.count())
        .select_from(Follow)
        .where(
            Follow.follower_id == user_id,
        )
    )
    return (await session.execute(stmt)).scalar_one()
