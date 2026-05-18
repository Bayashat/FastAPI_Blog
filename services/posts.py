"""Read-side post access shared by API routes and HTML routes."""

from turtle import title

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Post
from schemas.posts import PostCreate, PostUpdate


async def list_posts_ordered(session: AsyncSession) -> list[Post]:
    stmt = select(Post).options(selectinload(Post.author)).order_by(Post.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().unique().all()


async def get_post_by_id(session: AsyncSession, post_id: int) -> Post | None:
    stmt = select(Post).options(selectinload(Post.author)).where(Post.id == post_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_posts_by_user_id(session: AsyncSession, user_id: int) -> list[Post]:
    stmt = (
        select(Post).options(selectinload(Post.author)).where(Post.user_id == user_id).order_by(Post.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().unique().all()


async def create_post(session: AsyncSession, post: PostCreate, user_id: int) -> Post:
    new_post = Post(**post.model_dump(), user_id=user_id)
    session.add(new_post)
    await session.commit()
    await session.refresh(new_post, attribute_names=["author"])
    return new_post


async def update_post(session: AsyncSession, post_id: int, post: PostUpdate) -> Post | None:
    existing_post = await get_post_by_id(session, post_id)
    if existing_post:
        update_data = post.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_post, key, value)

        await session.commit()
        await session.refresh(existing_post, attribute_names=["author"])
        return existing_post
    return None


async def delete_post(session: AsyncSession, existing_post: Post) -> None:
    await session.delete(existing_post)
    await session.commit()
