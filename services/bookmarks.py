from collections.abc import Sequence

from sqlalchemy import delete, func, select
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


async def list_bookmarked_posts(
    session: AsyncSession,
    user_id: UserId,
    skip: int,
    limit: int,
) -> Sequence[Post]:
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
            Bookmark.post_id.desc(),
        )
        .offset(skip)
        .limit(limit)
    )
    return (await session.scalars(stmt)).all()


async def add_bookmark(
    session: AsyncSession,
    user_id: UserId,
    post_id: PostId,
) -> Bookmark:
    stmt = (
        insert(Bookmark)
        .values(
            post_id=post_id,
            user_id=user_id,
        )
        .on_conflict_do_nothing(
            index_elements=[
                Bookmark.user_id,
                Bookmark.post_id,
            ],
        )
    )

    await session.execute(stmt)
    await session.commit()

    bookmark = await get_bookmark(session, user_id, post_id)
    if bookmark is None:
        raise RuntimeError("Bookmark could not be loaded")

    return bookmark


async def get_bookmark(
    session: AsyncSession,
    user_id: UserId,
    post_id: PostId,
) -> Bookmark | None:
    # 推荐 复合 PK 永远用 dict, 不用记顺序
    return await session.get(
        Bookmark,
        {
            "user_id": user_id,
            "post_id": post_id,
        },
    )


async def delete_bookmark(
    session: AsyncSession,
    existing_bookmark: Bookmark,
) -> None:
    await session.delete(existing_bookmark)
    await session.commit()


async def delete_bookmarks_for_post(
    session: AsyncSession,
    post_id: PostId,
) -> None:
    stmt = delete(Bookmark).where(
        Bookmark.post_id == post_id,
    )
    await session.execute(stmt)
