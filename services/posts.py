"""Read-side post access shared by API routes and HTML routes."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from models import Post
from models.users import User
from schemas.posts import PostCreate, PostUpdate


async def list_posts_ordered(session: AsyncSession, skip: int = 0, limit: int = 10) -> list[Post]:
    stmt = (
        select(Post)
        .options(
            selectinload(Post.author).load_only(
                User.id,
                User.username,
                User.image_file,
            )
        )
        .order_by(Post.created_at.desc(), Post.id.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_post_by_id(session: AsyncSession, post_id: uuid.UUID) -> Post | None:
    stmt = (
        select(Post)
        .options(
            joinedload(Post.author).load_only(
                User.id,
                User.username,
                User.image_file,
            )
        )
        .where(Post.id == post_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_post_for_write(session: AsyncSession, post_id: uuid.UUID) -> Post | None:
    return await session.get(Post, post_id)


async def get_posts_by_user_id(
    session: AsyncSession,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 10,
) -> list[Post]:
    stmt = (
        select(Post)
        .where(Post.user_id == user_id)
        .order_by(
            Post.created_at.desc(),
            Post.id.desc(),
        )
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def create_post(session: AsyncSession, post: PostCreate, user_id: uuid.UUID) -> Post:
    new_post = Post(**post.model_dump(), user_id=user_id)
    session.add(new_post)
    await session.commit()
    await session.refresh(new_post, attribute_names=["author"])
    return new_post


async def update_post(
    session: AsyncSession,
    post_data: PostCreate | PostUpdate,
    existing_post: Post,
) -> Post:
    if isinstance(post_data, PostUpdate):
        update_data = post_data.model_dump(exclude_unset=True)
    else:
        update_data = post_data.model_dump()

    for key, value in update_data.items():
        setattr(existing_post, key, value)

    await session.commit()
    await session.refresh(existing_post, attribute_names=["author"])
    return existing_post


async def delete_post(session: AsyncSession, existing_post: Post) -> None:
    await session.delete(existing_post)
    await session.commit()


async def get_all_posts_count(session: AsyncSession) -> int:
    count = await session.scalar(select(func.count(Post.id)))
    return count or 0


async def count_posts_by_user_id(session: AsyncSession, user_id: uuid.UUID) -> int:
    count = await session.scalar(select(func.count(Post.id)).where(Post.user_id == user_id))
    return count or 0
