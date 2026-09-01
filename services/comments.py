from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from models.comments import Comment
from models.users import User
from schemas.comments import (
    CommentContent,
    CommentCreateRequest,
    CommentId,
    CommentListParams,
)
from schemas.common import UserId
from schemas.posts import PostIdPathParam


async def list_post_comments(
    session: AsyncSession,
    post_id: PostIdPathParam,
    filter_query: CommentListParams,
) -> Sequence[Comment]:
    # for now, it's only created_at
    sort_column = Comment.created_at

    # basic select
    stmt = (
        select(Comment)
        .options(
            joinedload(Comment.user).load_only(
                User.id,
                User.username,
                User.image_file,
            )
        )
        .where(Comment.post_id == post_id)
    )

    # add sorting, pagination
    stmt = (
        stmt.order_by(
            sort_column.desc() if filter_query.order_direction == "desc" else sort_column.asc(),
            Comment.id.desc() if filter_query.order_direction == "desc" else Comment.id.asc(),
        )
        .offset(filter_query.skip)
        .limit(filter_query.limit)
    )

    return (await session.scalars(stmt)).all()


async def count_comments(
    session: AsyncSession,
    post_id: PostIdPathParam,
) -> int:
    stmt = (
        select(func.count())
        .select_from(
            Comment,
        )
        .where(Comment.post_id == post_id)
    )

    return (await session.execute(stmt)).scalar_one()


async def create_comment(
    session: AsyncSession,
    post_id: PostIdPathParam,
    user_id: UserId,
    comment: CommentCreateRequest,
) -> Comment:
    new_comment = Comment(
        **comment.model_dump(),
        user_id=user_id,
        post_id=post_id,
    )
    session.add(new_comment)
    await session.commit()
    await session.refresh(new_comment, attribute_names=["user"])
    return new_comment


async def get_comment_by_id(session: AsyncSession, comment_id: CommentId) -> Comment | None:
    return await session.get(Comment, comment_id)


async def update_comment(session: AsyncSession, comment: Comment, new_content: CommentContent) -> Comment:
    comment.content = new_content
    await session.commit()
    await session.refresh(comment, attribute_names=["user", "updated_at"])
    return comment


async def delete_comment(session: AsyncSession, existing_comment: Comment) -> None:
    await session.delete(existing_comment)
    await session.commit()
