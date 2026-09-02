"""Read-side post access shared by API routes and HTML routes."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload, with_expression

from enums import PostStatus
from models import Post
from models.comments import Comment
from models.likes import Like
from models.post_tags import PostTag
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
from services import tags as tag_service

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
    PostSortField.PUBLISHED_AT: Post.published_at,
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
    stmt = stmt.where(Post.status == PostStatus.PUBLISHED)

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
        # 2 queries: SELECT ... FROM posts WHERE ...
        # +
        # SELECT post_tags.*, tags.* FROM post_tags LEFT JOIN tags ...
        # WHERE post_tags.post_id in (P1.id, P2.id)
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
    # add filters
    stmt = apply_post_filters(stmt, filter_query)

    # sorting, pagination
    stmt = (
        stmt.order_by(
            sort_expression.desc() if filter_query.order_direction == "desc" else sort_expression.asc(),
            (Post.created_at.desc() if filter_query.order_direction == "desc" else Post.created_at.asc()),
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
        .where(Post.id == post_id)
        .execution_options(populate_existing=True)
    )
    return await session.scalar(stmt)


async def get_post_for_write(session: AsyncSession, post_id: PostId) -> Post | None:
    return await session.get(Post, post_id)


async def get_posts_by_user_id(
    session: AsyncSession,
    user_id: UserId,
    is_owner: bool,
    skip: int = 0,
    limit: int = 10,
) -> Sequence[Post]:
    stmt = (
        select(Post)
        .options(
            selectinload(Post.tag_links).joinedload(PostTag.tag),
            with_expression(Post.comments_count, POST_COMMENT_COUNT_EXPR),
            with_expression(Post.likes_count, POST_LIKE_COUNT_EXPR),
        )
        .where(Post.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    if is_owner:
        stmt = stmt.order_by(
            Post.created_at.desc(),
            Post.id.desc(),
        )
    else:
        stmt = stmt.where(
            Post.status == PostStatus.PUBLISHED,
        ).order_by(
            Post.published_at.desc(),
            Post.id.desc(),
        )
    return (await session.scalars(stmt)).all()


async def create_post(session: AsyncSession, post_data: PostCreate, user_id: UserId) -> Post:
    post = Post(
        **post_data.model_dump(),
        user_id=user_id,
    )

    if post_data.status is PostStatus.PUBLISHED:
        post.published_at = datetime.now(UTC)

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
    actor_user_id: UserId,
) -> Post:
    if isinstance(post_data, PostUpdatePatch):
        tags_were_provided = "tags" in post_data.model_fields_set
        requested_tags = post_data.tags

        update_data = post_data.model_dump(
            exclude_unset=True,
            exclude={"tags"},
        )
    else:
        tags_were_provided = False
        requested_tags = None
        update_data = post_data.model_dump()

    for key, value in update_data.items():
        setattr(existing_post, key, value)

    if tags_were_provided:
        await tag_service.sync_post_tags(
            session=session,
            post_id=existing_post.id,
            tag_names=requested_tags,
            added_by_user_id=actor_user_id,
        )

    await session.commit()

    updated_post = await get_post_for_response(session, existing_post.id)
    if updated_post is None:
        raise RuntimeError("Updated post could not be loaded!")

    return updated_post


async def delete_post(session: AsyncSession, existing_post: Post) -> None:
    await session.delete(existing_post)
    await session.commit()


async def count_posts(session: AsyncSession, filter_query: PostListParams) -> int:
    stmt = select(func.count()).select_from(Post)
    stmt = apply_post_filters(stmt, filter_query)

    return (await session.execute(stmt)).scalar_one()


async def count_posts_by_user_id(session: AsyncSession, user_id: UserId, is_owner: bool) -> int:
    stmt = select(func.count()).select_from(Post).where(Post.user_id == user_id)

    if not is_owner:
        stmt = stmt.where(Post.status == PostStatus.PUBLISHED)

    return (await session.execute(stmt)).scalar_one()


async def check_post_exists(session: AsyncSession, post_id: PostId) -> bool:
    stmt = select(
        select(Post.id).where(Post.id == post_id).exists(),
    )
    return (await session.execute(stmt)).scalar_one()


class InvalidPostTransitionError(Exception):
    pass


async def publish_post(session: AsyncSession, post: Post) -> Post:
    if post.status != PostStatus.DRAFT:
        raise InvalidPostTransitionError

    post.status = PostStatus.PUBLISHED
    post.published_at = datetime.now(UTC)

    await session.commit()

    published_post = await get_post_for_response(session, post.id)
    if published_post is None:
        raise RuntimeError("Published post could not be loaded")

    return published_post


async def archive_post(session: AsyncSession, post: Post) -> Post:
    if post.status != PostStatus.PUBLISHED:
        raise InvalidPostTransitionError

    post.status = PostStatus.ARCHIVED

    await session.commit()

    archived_post = await get_post_for_response(session, post.id)
    if archived_post is None:
        raise RuntimeError("Archived post could not be loaded")

    return archived_post
