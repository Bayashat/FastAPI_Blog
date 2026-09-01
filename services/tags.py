from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.post_tags import PostTag
from models.tags import Tag
from schemas.common import PostId, UserId
from schemas.tags import TagId, TagListParams, TagName


async def list_tags(
    session: AsyncSession,
    query_params: TagListParams,
) -> Sequence[Tag]:
    sort_column = Tag.created_at

    stmt = (
        select(Tag)
        .order_by(
            sort_column.desc() if query_params.order_direction == "desc" else sort_column.asc(),
            Tag.id.desc() if query_params.order_direction == "desc" else Tag.id.asc(),
        )
        .offset(query_params.skip)
        .limit(query_params.limit)
    )

    result = await session.execute(stmt)

    return result.scalars().all()


async def count_tags(
    session: AsyncSession,
) -> int:
    stmt = select(func.count()).select_from(
        Tag,
    )
    return (await session.execute(stmt)).scalar_one()


async def ensure_tags_exist(
    session: AsyncSession,
    names: list[TagName],
) -> None:
    if not names:
        return

    unique_names = list(dict.fromkeys(names))

    stmt = (
        insert(Tag)
        .values([{"name": name} for name in unique_names])
        .on_conflict_do_nothing(
            index_elements=[func.lower(Tag.name)],
        )
        .returning(Tag)
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


async def add_post_tags(
    session: AsyncSession,
    post_id: PostId,
    added_by_user_id: UserId,
    adds: set[TagId],
    removes: set[TagId],
) -> None:
    if adds:
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
            for tag_id in adds
        ]

        await session.execute(insert_stmt, bind_data)
    if removes:
        delete_stmt = delete(PostTag).where(
            PostTag.post_id == post_id,
            PostTag.tag_id.in_(removes),
        )
        await session.execute(delete_stmt)


async def get_post_tags_by_post_id(
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

    # 这里不管提供的tags是否已在系统存在,直接全扔给该函数来处理添加
    await ensure_tags_exist(session, names)

    existing_post_tags: Sequence[PostTag] = await get_post_tags_by_post_id(session, post_id)
    existing_post_tag_ids = [post_tag.tag_id for post_tag in existing_post_tags]

    new_tags: Sequence[Tag] = await get_tags_by_names(session, names)
    new_tag_ids = [tag.id for tag in new_tags]

    adds = set(new_tag_ids) - set(existing_post_tag_ids)
    removes = set(existing_post_tag_ids) - set(new_tag_ids)

    if len(existing_post_tag_ids) + len(adds) > settings.post_tag_limit:
        raise PostTagLimitExceededError(f"A post can't have more than {settings.post_tag_limit} tags!")

    await add_post_tags(
        session=session,
        post_id=post_id,
        added_by_user_id=added_by_user_id,
        adds=adds,
        removes=removes,
    )
