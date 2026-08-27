"""Read-side post access shared by API routes and HTML routes."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, with_expression

from models import Post
from models.comments import Comment
from models.likes import Like
from models.users import User
from schemas.common import UserId
from schemas.posts import (
    PostCreate,
    PostId,
    PostListParams,
    PostSortField,
    PostUpdatePatch,
    PostUpdatePut,
)

POST_COMMENT_COUNT_EXPR = (
    select(func.count(Comment.id))
    .where(Comment.post_id == Post.id)
    .correlate_except(Comment)
    .scalar_subquery()
    .label("comments_count")
)
POST_LIKE_COUNT_EXPR = (
    select(func.count())
    .select_from(Like)
    .where(Like.post_id == Post.id)
    .correlate_except(Like)
    .scalar_subquery()
    .label("likes_count")
)

POST_SORT_EXPRESSIONS = {
    PostSortField.CREATED_AT: Post.created_at,
    PostSortField.UPDATED_AT: Post.updated_at,
    PostSortField.COMMENTS_COUNT: POST_COMMENT_COUNT_EXPR,
    PostSortField.LIKES_COUNT: POST_LIKE_COUNT_EXPR,
}

if set(POST_SORT_EXPRESSIONS) != set(PostSortField):
    raise RuntimeError("POST_SORT_EXPRESSIONS must define every PostSortField")


def apply_post_filters[SelectRow: tuple[Any, ...]](
    stmt: Select[SelectRow],
    filters: PostListParams,
) -> Select[SelectRow]:
    if filters.author_id is not None:
        stmt = stmt.where(Post.user_id == filters.author_id)

    if filters.q:
        stmt = stmt.where(Post.title.ilike(f"%{filters.q}%") | Post.content.ilike(f"%{filters.q}%"))

    if filters.created_from is not None:
        stmt = stmt.where(Post.created_at >= filters.created_from)

    if filters.created_before is not None:
        stmt = stmt.where(Post.created_at < filters.created_before)

    return stmt


async def list_posts(
    session: AsyncSession,
    filter_query: PostListParams,
) -> Sequence[Post]:
    sort_expression = POST_SORT_EXPRESSIONS[filter_query.order_by]

    # basic select
    stmt = select(Post).options(
        joinedload(Post.author).load_only(
            User.id,
            User.username,
            User.image_file,
        ),
        with_expression(
            Post.comments_count,
            POST_COMMENT_COUNT_EXPR,
        ),
        with_expression(
            Post.likes_count,
            POST_LIKE_COUNT_EXPR,
        ),
    )
    # add filters
    stmt = apply_post_filters(stmt, filter_query)
    # sorting, pagination
    stmt = (
        stmt.order_by(
            sort_expression.desc() if filter_query.order_direction == "desc" else sort_expression.asc(),
            Post.id.desc() if filter_query.order_direction == "desc" else Post.id.asc(),
        )
        .offset(filter_query.skip)
        .limit(filter_query.limit)
    )

    return (await session.scalars(stmt)).all()


async def get_post_for_response(session: AsyncSession, post_id: PostId) -> Post | None:
    stmt = (
        select(Post)
        .options(
            joinedload(Post.author).load_only(
                User.id,
                User.username,
                User.image_file,
            ),
            with_expression(
                Post.comments_count,
                POST_COMMENT_COUNT_EXPR,
            ),
            with_expression(
                Post.likes_count,
                POST_LIKE_COUNT_EXPR,
            ),
        )
        .where(Post.id == post_id)
        .execution_options(populate_existing=True)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_post_for_write(session: AsyncSession, post_id: PostId) -> Post | None:
    return await session.get(Post, post_id)


async def get_posts_by_user_id(
    session: AsyncSession,
    user_id: UserId,
    skip: int = 0,
    limit: int = 10,
) -> Sequence[Post]:
    stmt = (
        select(Post)
        .options(
            with_expression(Post.comments_count, POST_COMMENT_COUNT_EXPR),
            with_expression(Post.likes_count, POST_LIKE_COUNT_EXPR),
        )
        .where(Post.user_id == user_id)
        .order_by(
            Post.created_at.desc(),
            Post.id.desc(),
        )
        .offset(skip)
        .limit(limit)
    )

    return (await session.scalars(stmt)).all()


async def create_post(session: AsyncSession, post_data: PostCreate, user_id: UserId) -> Post:
    post = Post(**post_data.model_dump(), user_id=user_id)

    session.add(post)
    await session.commit()

    new_post = await get_post_for_response(session, post.id)

    if new_post is None:
        raise RuntimeError("Created post could not be loaded")

    return new_post


async def update_post(
    session: AsyncSession,
    post_data: PostUpdatePut | PostUpdatePatch,
    existing_post: Post,
) -> Post:
    if isinstance(post_data, PostUpdatePatch):
        update_data = post_data.model_dump(
            exclude_none=True,
            exclude_unset=True,
        )
    else:
        update_data = post_data.model_dump()

    for key, value in update_data.items():
        setattr(existing_post, key, value)

    await session.commit()

    updated_post = await get_post_for_response(session, existing_post.id)
    assert updated_post is not None

    return updated_post


async def delete_post(session: AsyncSession, existing_post: Post) -> None:
    await session.delete(existing_post)
    await session.commit()


async def count_posts(session: AsyncSession, filter_query: PostListParams) -> int:
    stmt = select(func.count()).select_from(Post)
    stmt = apply_post_filters(stmt, filter_query)

    return (await session.execute(stmt)).scalar_one()


async def count_posts_by_user_id(session: AsyncSession, user_id: UserId) -> int:
    stmt = select(func.count()).select_from(Post).where(Post.user_id == user_id)

    return (await session.execute(stmt)).scalar_one()


async def check_post_exists(session: AsyncSession, post_id: PostId) -> bool:
    stmt = select(
        select(Post.id).where(Post.id == post_id).exists(),
    )
    return await session.scalar(stmt)
