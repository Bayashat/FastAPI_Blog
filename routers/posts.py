from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from auth import CurrentUser
from dependencies import SessionDep
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
from services.posts import count_posts
from services.posts import create_post as create_post_service
from services.posts import delete_post as delete_post_service
from services.posts import get_post_for_response, get_post_for_write, list_posts
from services.posts import update_post as update_post_service

router = APIRouter(prefix="/api/posts")


@router.get("/", response_model=PaginatedPostsResponse, status_code=status.HTTP_200_OK)
async def get_posts(
    session: SessionDep,
    # skip: Annotated[int, Query(ge=0)] = 0,
    # limit: Annotated[int, Query(ge=1, le=100)] = 10,
    filter_query: Annotated[PostListParams, Query()],
) -> PaginatedPostsResponse:
    total_count = await count_posts(session, filter_query)
    posts: list[Post] = await list_posts(session, filter_query)

    has_more = filter_query.skip + len(posts) < total_count

    return PaginatedPostsResponse(
        posts=posts,
        total=total_count,
        skip=filter_query.skip,
        limit=filter_query.limit,
        has_more=has_more,
    )


@router.get("/{post_id}", response_model=PostResponse, status_code=status.HTTP_200_OK)
async def get_post(post_id: PostIdPathParam, session: SessionDep) -> Post:
    existing_post = await get_post_for_response(session, post_id)
    if not existing_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    return existing_post


@router.patch("/{post_id}", response_model=PostResponse, status_code=status.HTTP_200_OK)
async def update_post_patch(
    post_id: PostIdPathParam,
    session: SessionDep,
    user: CurrentUser,
    new_post_data: PostUpdatePatch,
) -> Post:
    existing_post = await get_post_for_write(session, post_id)
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
    updated_post = await update_post_service(session, new_post_data, existing_post)
    return updated_post


@router.put("/{post_id}", response_model=PostResponse, status_code=status.HTTP_200_OK)
async def update_post_full(
    post_id: PostIdPathParam,
    session: SessionDep,
    user: CurrentUser,
    post: PostUpdatePut,
) -> Post:
    existing_post = await get_post_for_write(session, post_id)
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
    updated_post = await update_post_service(session, post, existing_post)
    return updated_post


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post: PostCreate,
    session: SessionDep,
    user: CurrentUser,
) -> Post:
    new_post = await create_post_service(session, post, user.id)
    return new_post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: PostIdPathParam,
    session: SessionDep,
    user: CurrentUser,
):
    existing_post = await get_post_for_write(session, post_id)
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
    await delete_post_service(session, existing_post)
