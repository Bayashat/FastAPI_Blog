from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload, with_expression

from enums import PostStatus
from models.bookmarks import Bookmark
from models.post_tags import PostTag
from models.posts import Post
from models.users import User
from schemas.common import PostId, UserId
from services.common import POST_COMMENT_COUNT_EXPR, POST_LIKE_COUNT_EXPR


async def count_bookmarks_by_user_id(
    session: AsyncSession,
    user_id: UserId,
) -> int:
    stmt = (
        select(func.count())
        .select_from(Post)
        .join(
            Bookmark,
            Bookmark.post_id == Post.id,
        )
        .where(
            Bookmark.user_id == user_id,
            Post.status == PostStatus.PUBLISHED,
        )
    )
    return (await session.execute(stmt)).scalar_one()


async def get_bookmarks_by_user_id(
    session: AsyncSession,
    user_id: UserId,
    skip: int,
    limit: int,
) -> Sequence[Bookmark]:
    stmt = (
        select(Post)
        .join(
            Bookmark,
            Bookmark.post_id == Post.id,
        )
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
        .where(
            Bookmark.user_id == user_id,
            Post.status == PostStatus.PUBLISHED,
        )
        .order_by(
            Bookmark.saved_at.desc(),
            Post.id.desc(),
        )
        .offset(skip)
        .limit(limit)
    )
    return (await session.scalars(stmt)).all()


async def add_bookmark(
    session: AsyncSession,
    post_id: PostId,
    user_id: UserId,
) -> Bookmark:
    stmt = (
        insert(Bookmark)
        .values(
            post_id=post_id,
            user_id=user_id,
        )
        .on_conflict_do_nothing(
            index_elements=[Bookmark.post_id, Bookmark.user_id],
        )
        .returning(Bookmark)
    )

    result = await session.execute(stmt)
    await session.commit()

    return result.scalar_one()


async def get_bookmark_by_post_id(
    session: AsyncSession,
    post_id: PostId,
    user_id: UserId,
) -> Bookmark | None:
    return await session.get(Bookmark, (post_id, user_id))


async def delete_bookmark(
    session: AsyncSession,
    existing_bookmark: Bookmark,
) -> None:
    await session.delete(existing_bookmark)
    await session.commit()
