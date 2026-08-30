from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from auth import CurrentUser, OptionalCurrentUser
from dependencies import SessionDep
from enums import PostStatus
from models import Post
from schemas.posts import (
    PaginatedPostsResponse,
    PostCreate,
    PostIdPathParam,
    PostListParams,
    PostResponse,
    PostUpdatePatch,
    PostUpdatePut,
)
from services import posts as post_service

router = APIRouter(prefix="/api/posts")


@router.get("", response_model=PaginatedPostsResponse, status_code=status.HTTP_200_OK)
async def get_posts(
    session: SessionDep,
    # skip: Annotated[int, Query(ge=0)] = 0,
    # limit: Annotated[int, Query(ge=1, le=100)] = 10,
    query_params: Annotated[PostListParams, Query()],
) -> PaginatedPostsResponse:
    "List all published posts"
    total_count = await post_service.count_posts(session, query_params)
    posts: Sequence[Post] = await post_service.list_posts(session, query_params)

    has_more = query_params.skip + len(posts) < total_count

    return PaginatedPostsResponse.model_validate(
        {
            "posts": posts,
            "total": total_count,
            "skip": query_params.skip,
            "limit": query_params.limit,
            "has_more": has_more,
        }
    )


@router.get("/{post_id}", response_model=PostResponse, status_code=status.HTTP_200_OK)
async def get_post(
    post_id: PostIdPathParam,
    session: SessionDep,
    user: OptionalCurrentUser,
) -> Post:
    post_not_found_exception = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found",
    )
    post = await post_service.get_post_for_response(session, post_id)
    if not post:
        raise post_not_found_exception

    if post.status is PostStatus.PUBLISHED:
        return post

    if user is None or user.id != post.user_id:
        raise post_not_found_exception

    return post


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post: PostCreate,
    session: SessionDep,
    user: CurrentUser,
) -> Post:
    new_post = await post_service.create_post(session, post, user.id)
    return new_post


@router.post("/{post_id}/publish", response_model=PostResponse, status_code=status.HTTP_200_OK)
async def publish_post(
    post_id: PostIdPathParam,
    session: SessionDep,
    user: CurrentUser,
) -> Post:
    post_not_found_exception = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found",
    )
    existing_post = await post_service.get_post_for_write(session, post_id)
    if not existing_post:
        raise post_not_found_exception

    if user.id != existing_post.user_id:
        raise post_not_found_exception

    try:
        published_post = await post_service.publish_post(session, existing_post)
    except post_service.InvalidPostTransitionError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft posts can be published!",
        ) from err

    return published_post


@router.post("/{post_id}/archive", response_model=PostResponse, status_code=status.HTTP_200_OK)
async def archive_post(
    post_id: PostIdPathParam,
    session: SessionDep,
    user: CurrentUser,
) -> Post:
    post_not_found_exception = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found",
    )
    existing_post = await post_service.get_post_for_write(session, post_id)
    if not existing_post:
        raise post_not_found_exception

    if user.id != existing_post.user_id:
        raise post_not_found_exception
    try:
        archived_post = await post_service.archive_post(session, existing_post)
    except post_service.InvalidPostTransitionError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only published posts can be archived!",
        ) from err
    return archived_post


@router.patch("/{post_id}", response_model=PostResponse, status_code=status.HTTP_200_OK)
async def update_post_patch(
    post_id: PostIdPathParam,
    session: SessionDep,
    user: CurrentUser,
    new_post_data: PostUpdatePatch,
) -> Post:
    existing_post = await post_service.get_post_for_write(session, post_id)
    if not existing_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    if existing_post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post",
        )
    updated_post = await post_service.update_post(session, new_post_data, existing_post)
    return updated_post


@router.put("/{post_id}", response_model=PostResponse, status_code=status.HTTP_200_OK)
async def update_post_full(
    post_id: PostIdPathParam,
    session: SessionDep,
    user: CurrentUser,
    post: PostUpdatePut,
) -> Post:
    existing_post = await post_service.get_post_for_write(session, post_id)
    if not existing_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    if existing_post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post",
        )
    updated_post = await post_service.update_post(session, post, existing_post)
    return updated_post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: PostIdPathParam,
    session: SessionDep,
    user: CurrentUser,
) -> None:
    existing_post = await post_service.get_post_for_write(session, post_id)
    if not existing_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    if existing_post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post",
        )
    await post_service.delete_post(session, existing_post)
