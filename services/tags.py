from collections.abc import Sequence

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from enums import PostStatus
from models.post_tags import PostTag
from models.posts import Post
from models.tags import Tag
from schemas.common import PostId, UserId
from schemas.tags import TagId, TagListParams, TagName

TAG_SORT_EXPRESSIONS = {
    "name": Tag.name,
    "created_at": Tag.created_at,
}


def tag_is_visible():
    is_unused = ~Tag.post_links.any()

    has_published_post = Tag.post_links.any(
        PostTag.post.has(
            Post.status == PostStatus.PUBLISHED,
        )
    )

    return or_(is_unused, has_published_post)


async def list_tags(
    session: AsyncSession,
    query_params: TagListParams,
) -> Sequence[Tag]:
    sort_column = TAG_SORT_EXPRESSIONS[query_params.order_by]

    """
    Tag 可以显示, 如果:
    1. 它完全没被任何 Post 使用
    或者
    2. 至少有一个 Published Post 使用它
    """
    stmt = (
        select(Tag)
        .where(tag_is_visible())
        .order_by(
            sort_column.desc() if query_params.order_direction == "desc" else sort_column.asc(),
            Tag.id.desc() if query_params.order_direction == "desc" else Tag.id.asc(),
        )
        .offset(query_params.skip)
        .limit(query_params.limit)
    )

    return (await session.scalars(stmt)).all()


async def count_tags(
    session: AsyncSession,
) -> int:
    stmt = (
        select(
            func.count(),
        )
        .select_from(Tag)
        .where(tag_is_visible())
    )
    return (await session.execute(stmt)).scalar_one()


async def ensure_tags_exist(
    session: AsyncSession,
    names: list[TagName],
) -> None:
    if not names:
        return

    stmt = (
        insert(Tag)
        .values([{"name": name} for name in names])
        .on_conflict_do_nothing(
            index_elements=[func.lower(Tag.name)],
        )
        # .returning(Tag)
    )

    await session.execute(stmt)
    # inserted_tags = result.scalars().all()
    # return inserted_tags


async def get_tags_by_names(
    session: AsyncSession,
    names: list[TagName],
) -> Sequence[Tag]:
    stmt = select(Tag).where(Tag.name.in_(names))
    return (await session.scalars(stmt)).all()


async def apply_post_tag_changes(
    session: AsyncSession,
    post_id: PostId,
    added_by_user_id: UserId,
    tag_ids_to_add: set[TagId],
    tag_ids_to_remove: set[TagId],
) -> None:
    if tag_ids_to_add:
        # basic stmt
        insert_stmt = insert(PostTag).on_conflict_do_nothing(
            index_elements=[
                PostTag.post_id,
                PostTag.tag_id,
            ]
        )

        # bulk insert
        bind_data = [
            {
                "post_id": post_id,
                "tag_id": tag_id,
                "added_by_user_id": added_by_user_id,
            }
            for tag_id in tag_ids_to_add
        ]

        await session.execute(insert_stmt, bind_data)
    if tag_ids_to_remove:
        delete_stmt = delete(PostTag).where(
            PostTag.post_id == post_id,
            PostTag.tag_id.in_(tag_ids_to_remove),
        )
        await session.execute(delete_stmt)


async def list_post_tag_links(
    session: AsyncSession,
    post_id: PostId,
) -> Sequence[PostTag]:
    stmt = select(PostTag).where(PostTag.post_id == post_id)

    return (await session.scalars(stmt)).all()


class PostTagLimitExceededError(Exception):
    """Raised when a post exceeds the maximum allowed number of tags."""


async def sync_post_tags(
    session: AsyncSession,
    post_id: PostId,
    tag_names: list[TagName] | None,
    added_by_user_id: UserId,
) -> None:
    names = tag_names or []

    if len(names) > settings.post_tag_limit:
        raise PostTagLimitExceededError(f"A post can't have more than {settings.post_tag_limit} tags!")

    # 这里不管提供的tags是否已在系统存在,直接全扔给该函数来处理添加
    await ensure_tags_exist(session, names)

    existing_links: Sequence[PostTag] = await list_post_tag_links(session, post_id)
    existing_tag_ids = {post_tag.tag_id for post_tag in existing_links}

    requested_tags: Sequence[Tag] = await get_tags_by_names(session, names)
    requested_tag_ids = {tag.id for tag in requested_tags}

    adds = requested_tag_ids - existing_tag_ids
    removes = existing_tag_ids - requested_tag_ids

    await apply_post_tag_changes(
        session=session,
        post_id=post_id,
        added_by_user_id=added_by_user_id,
        tag_ids_to_add=adds,
        tag_ids_to_remove=removes,
    )
