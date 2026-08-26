from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from auth import CurrentUser
from dependencies import SessionDep
from models import Comment
from schemas.comments import (
    CommentCreateRequest,
    CommentListParams,
    CommentResponse,
    ListCommentsResponse,
)
from schemas.posts import PostIdPathParam
from services.comments import count_comments
from services.comments import create_comment as create_comment_service
from services.comments import list_post_comments as list_post_comments_service

router = APIRouter(prefix="/api/posts/{post_id}")


@router.get("/comments", response_model=ListCommentsResponse, status_code=status.HTTP_200_OK)
async def list_post_comments(
    session: SessionDep,
    post_id: PostIdPathParam,
    filter_query: Annotated[CommentListParams, Query()],
) -> ListCommentsResponse:
    total_count = await count_comments(session, post_id)
    comments: list[Comment] = await list_post_comments_service(session, post_id, filter_query)

    has_more = filter_query.skip + len(comments) < total_count

    return ListCommentsResponse(
        comments=comments,
        total=total_count,
        skip=filter_query.skip,
        limit=filter_query.limit,
        has_more=has_more,
    )


@router.post("/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_post_comment(
    session: SessionDep,
    post_id: PostIdPathParam,
    user: CurrentUser,
    comment: CommentCreateRequest,
) -> Comment:
    new_comment = await create_comment_service(session, post_id, user.id, comment)
    return new_comment
