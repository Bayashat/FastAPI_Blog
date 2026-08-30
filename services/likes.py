from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.likes import Like
from schemas.common import UserId
from schemas.posts import PostId
from services.posts import check_post_exists


class PostNotFoundError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class PostLikeState:
    post_id: PostId
    liked: bool
    likes_count: int


async def set_post_like_state(
    session: AsyncSession,
    post_id: PostId,
    user_id: UserId,
    liked: bool,
) -> PostLikeState:
    try:
        post_exists = await check_post_exists(session, post_id)

        if not post_exists:
            raise PostNotFoundError

        if liked:
            insert_stmt = (
                insert(Like)
                .values(
                    user_id=user_id,
                    post_id=post_id,
                )
                .on_conflict_do_nothing(
                    index_elements=[
                        Like.user_id,
                        Like.post_id,
                    ]
                )
            )
            await session.execute(insert_stmt)
        else:
            delete_stmt = delete(Like).where(
                Like.post_id == post_id,
                Like.user_id == user_id,
            )
            await session.execute(delete_stmt)

        state_stmt = (
            select(
                (func.count().filter(Like.user_id == user_id) > 0).label("liked"),
                func.count().label("likes_count"),
            )
            .select_from(Like)
            .where(Like.post_id == post_id)
        )
        state_row = (await session.execute(state_stmt)).one()

        state = PostLikeState(
            post_id=post_id,
            liked=state_row.liked,
            likes_count=state_row.likes_count,
        )

        await session.commit()
        return state

    except IntegrityError as exc:
        await session.rollback()

        constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)

        # 防止检查完 Post 后, Post 又被其他事务删除的竞态条件。
        if constraint_name == "fk_likes_post_id_posts":
            raise PostNotFoundError from exc

        raise

    except Exception:
        await session.rollback()
        raise
