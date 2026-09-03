from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload, with_expression

from enums import PostStatus
from models.follows import Follow
from models.post_tags import PostTag
from models.posts import Post
from models.users import User
from schemas.common import UserId
from services.common import POST_COMMENT_COUNT_EXPR, POST_LIKE_COUNT_EXPR


async def list_feed_posts(
    session: AsyncSession,
    user_id: UserId,
    skip: int,
    limit: int,
) -> Sequence[Post]:
    stmt = (
        select(Post)
        .options(
            joinedload(Post.author).load_only(
                User.id,
                User.username,
                User.image_file,
            ),
            selectinload(Post.tag_links).joinedload(PostTag.tag),
            with_expression(
                Post.comments_count,
                POST_COMMENT_COUNT_EXPR,
            ),
            with_expression(
                Post.likes_count,
                POST_LIKE_COUNT_EXPR,
            ),
        )
        .join(
            Follow,
            Follow.followed_user_id == Post.user_id,
        )
        .where(
            Follow.follower_id == user_id,
            Post.status == PostStatus.PUBLISHED,
        )
        .order_by(
            Post.published_at.desc(),
            Post.id.desc(),
        )
        .offset(skip)
        .limit(limit)
    )
    return (await session.scalars(stmt)).all()


async def count_feed_posts(
    session: AsyncSession,
    user_id: UserId,
) -> int:
    stmt = (
        select(func.count())
        .select_from(Post)
        .join(
            Follow,
            Follow.followed_user_id == Post.user_id,
        )
        .where(
            Follow.follower_id == user_id,
            Post.status == PostStatus.PUBLISHED,
        )
    )
    return (await session.execute(stmt)).scalar_one()
