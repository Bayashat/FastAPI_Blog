from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from auth import CurrentUser
from config import settings
from dependencies import SessionDep
from enums import PostStatus
from models.bookmarks import Bookmark
from schemas.bookmarks import (
    BookmarkItem,
    UserBookmarksResponse,
)
from schemas.common import PostId
from services import bookmarks as bookmark_service
from services import posts as post_service

router = APIRouter(prefix="/api/users/me")


@router.get(
    "/bookmarks",
    response_model=UserBookmarksResponse,
    status_code=status.HTTP_200_OK,
)
async def list_my_bookmarks(
    session: SessionDep,
    user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
) -> UserBookmarksResponse:
    total_count = await bookmark_service.count_bookmarks_by_user_id(session, user.id)
    bookmarks: Sequence[Bookmark] = await bookmark_service.get_bookmarks_by_user_id(
        session,
        user.id,
        skip,
        limit,
    )

    has_more = skip + len(bookmarks) < total_count

    return UserBookmarksResponse.model_validate(
        {
            "user": user,
            "bookmarks": bookmarks,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "has_more": has_more,
        }
    )


@router.put(
    "/bookmarks/{post_id}",
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
        post_id,
        user.id,
    )
    return new_bookmark


@router.delete(
    "/bookmarks/{post_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_bookmark(
    session: SessionDep,
    post_id: PostId,
    user: CurrentUser,
):
    existing_bookmark = await bookmark_service.get_bookmark_by_post_id(
        session,
        post_id,
        user.id,
    )
    if not existing_bookmark or (existing_bookmark.user_id != user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found!")

    await bookmark_service.delete_bookmark(
        session,
        existing_bookmark,
    )
