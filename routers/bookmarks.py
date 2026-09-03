from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from config import settings
from dependencies import CurrentUser, SessionDep
from enums import PostStatus
from models.bookmarks import Bookmark
from models.posts import Post
from schemas.bookmarks import (
    BookmarkItem,
    SavedPostResponse,
)
from schemas.common import PostId
from services import bookmarks as bookmark_service
from services import posts as post_service

router = APIRouter(prefix="/api/users/me/bookmarks")


@router.get(
    "",
    response_model=SavedPostResponse,
    status_code=status.HTTP_200_OK,
)
async def list_my_bookmarks(
    session: SessionDep,
    user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
) -> SavedPostResponse:
    total_count = await bookmark_service.count_bookmarks_by_user_id(session, user.id)
    bookmarked_posts: Sequence[Post] = await bookmark_service.list_bookmarked_posts(
        session,
        user.id,
        skip,
        limit,
    )

    has_more = skip + len(bookmarked_posts) < total_count

    return SavedPostResponse.model_validate(
        {
            "user": user,
            "posts": bookmarked_posts,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "has_more": has_more,
        }
    )


@router.put(
    "/{post_id}",
    response_model=BookmarkItem,
    status_code=status.HTTP_200_OK,
)
async def add_bookmark(
    session: SessionDep,
    post_id: PostId,
    user: CurrentUser,
) -> Bookmark:
    post = await post_service.get_post_for_write(session, post_id)
    if not post or post.status is not PostStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found!",
        )

    new_bookmark = await bookmark_service.add_bookmark(
        session,
        user.id,
        post_id,
    )
    return new_bookmark


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_bookmark(
    session: SessionDep,
    post_id: PostId,
    user: CurrentUser,
) -> None:
    existing_bookmark = await bookmark_service.get_bookmark(
        session,
        user.id,
        post_id,
    )
    if not existing_bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found!")

    await bookmark_service.delete_bookmark(
        session,
        existing_bookmark,
    )
