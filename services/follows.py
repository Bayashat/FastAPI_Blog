from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

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
async def get_followers(
    session: AsyncSession,
    user_id: UserId,
) -> Sequence[User]:
    stmt = (
        select(User)
        .join(
            Follow,
            Follow.follower_id == User.id,
        )
        .where(
            Follow.followed_user_id == user_id,
        )
        .order_by(
            Follow.followed_at.desc(),
            Follow.followed_user_id.desc(),
        )
    )
    return (await session.scalars(stmt)).all()


# 查询目标用户关注了谁
async def get_followings(
    session: AsyncSession,
    user_id: UserId,
) -> Sequence[User]:
    stmt = (
        select(User)
        .join(
            Follow,
            Follow.followed_user_id == User.id,
        )
        .where(
            Follow.follower_id == user_id,
        )
        .order_by(
            Follow.followed_at.desc(),
            Follow.follower_id.desc(),
        )
    )
    return (await session.scalars(stmt)).all()
