from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from auth import CurrentUser, OptionalCurrentUser
from dependencies import SessionDep
from enums import PostStatus
from models import Comment
from schemas.comments import (
    CommentCreateRequest,
    CommentIdPathParam,
    CommentListParams,
    CommentResponse,
    ListCommentsResponse,
    UpdateCommentRequest,
)
from schemas.posts import PostIdPathParam
from services import comments as comment_service
from services import posts as post_service

post_comments_router = APIRouter(prefix="/api/posts/{post_id}/comments")
comments_router = APIRouter(prefix="/api/comments")


@post_comments_router.get("", response_model=ListCommentsResponse, status_code=status.HTTP_200_OK)
async def list_post_comments(
    session: SessionDep,
    user: OptionalCurrentUser,
    post_id: PostIdPathParam,
    filter_query: Annotated[CommentListParams, Query()],
) -> ListCommentsResponse:
    post_not_found_exception = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found!",
    )

    post = await post_service.get_post_for_response(session, post_id)
    if not post:
        raise post_not_found_exception

    is_owner = user.id == post.user_id if user and post else False
    if not is_owner and post.status is not PostStatus.PUBLISHED:
        raise post_not_found_exception

    total_count = await comment_service.count_comments(session, post_id)
    comments: Sequence[Comment] = await comment_service.list_post_comments(session, post_id, filter_query)

    has_more = filter_query.skip + len(comments) < total_count

    return ListCommentsResponse.model_validate(
        {
            "comments": comments,
            "total": total_count,
            "skip": filter_query.skip,
            "limit": filter_query.limit,
            "has_more": has_more,
        }
    )


@post_comments_router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_post_comment(
    session: SessionDep,
    post_id: PostIdPathParam,
    user: CurrentUser,
    comment: CommentCreateRequest,
) -> Comment:
    existing_post = await post_service.get_post_for_write(session, post_id)

    if not existing_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found!",
        )

    if existing_post.status is not PostStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannnot add new comments to unpublished posts!",
        )

    new_comment = await comment_service.create_comment(session, post_id, user.id, comment)
    return new_comment


@comments_router.patch("/{comment_id}", response_model=CommentResponse, status_code=status.HTTP_200_OK)
async def update_comment(
    session: SessionDep,
    comment_id: CommentIdPathParam,
    user: CurrentUser,
    update_comment_data: UpdateCommentRequest,
) -> Comment:
    existing_comment = await comment_service.get_comment_by_id(session, comment_id)
    if not existing_comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found!",
        )

    if existing_comment.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to update this comment!",
        )

    updated_comment = await comment_service.update_comment(
        session=session,
        comment=existing_comment,
        new_content=update_comment_data.content,
    )
    return updated_comment


@comments_router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    session: SessionDep,
    comment_id: CommentIdPathParam,
    user: CurrentUser,
) -> None:
    existing_comment = await comment_service.get_comment_by_id(session, comment_id)
    if not existing_comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found!",
        )

    if existing_comment.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to delete this comment!",
        )

    await comment_service.delete_comment(
        session=session,
        existing_comment=existing_comment,
    )
