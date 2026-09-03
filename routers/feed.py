from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Query, status

from config import settings
from dependencies import CurrentUser, SessionDep
from models.posts import Post
from schemas.posts import PaginatedPostsResponse
from services import feed as feed_service

router = APIRouter(prefix="/api/feed")


@router.get("", response_model=PaginatedPostsResponse, status_code=status.HTTP_200_OK)
async def get_feed(
    session: SessionDep,
    current_user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
) -> PaginatedPostsResponse:
    total_count = await feed_service.count_feed_posts(session, current_user.id)
    posts: Sequence[Post] = await feed_service.list_feed_posts(session, current_user.id, skip, limit)

    has_more = skip + len(posts) < total_count

    return PaginatedPostsResponse.model_validate(
        {
            "posts": posts,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "has_more": has_more,
        }
    )
