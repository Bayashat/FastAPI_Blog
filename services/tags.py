from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

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


async def add_new_tags(
    session: AsyncSession,
    names: list[TagName],
) -> Sequence[Tag]:
    if not names:
        return []

    unique_names = list(set(names))

    stmt = insert(Tag).values([{"name": name} for name in unique_names])

    stmt = stmt.on_conflict_do_nothing(
        index_elements=[func.lower(Tag.name)],
    ).returning(Tag)

    result = await session.execute(stmt)
    await session.commit()

    inserted_tags = result.scalars().all()
    return inserted_tags


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
    adds: list[TagId],
    removes: list[TagId],
) -> None:
    if adds:
        # basic stmt
        stmt = insert(PostTag).on_conflict_do_nothing(
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

        await session.execute(stmt, bind_data)
    if removes:
        stmt = delete(PostTag).where(
            PostTag.post_id == post_id,
            PostTag.tag_id.in_(removes),
        )
        await session.execute(stmt)


async def get_post_tags_by_post_id(
    session: AsyncSession,
    post_id: PostId,
) -> Sequence[PostTag]:
    stmt = select(PostTag).where(PostTag.post_id == post_id)

    return (await session.scalars(stmt)).all()
