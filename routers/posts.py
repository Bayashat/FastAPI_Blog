from fastapi import APIRouter, Depends, HTTPException, status

from auth import CurrentUser
from dependencies import SessionDep
from schemas.posts import PostCreate, PostResponse, PostUpdate
from services.posts import create_post as create_post_service
from services.posts import delete_post as delete_post_service
from services.posts import get_post_by_id, list_posts_ordered
from services.posts import update_post as update_post_service

router = APIRouter(prefix="/api/posts")


@router.get("", response_model=list[PostResponse])
async def get_posts(session: SessionDep):
    return await list_posts_ordered(session)


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, session: SessionDep):
    existing_post = await get_post_by_id(session, post_id)
    if not existing_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    return existing_post


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    session: SessionDep,
    user: CurrentUser,
    post: PostUpdate,
):
    existing_post = await get_post_by_id(session, post_id)
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
    updated_post = await update_post_service(session, post_id, post)
    return updated_post


@router.put("/{user_id}", response_model=PostResponse)
async def update_post_full(
    post_id: int,
    session: SessionDep,
    user: CurrentUser,
    post: PostCreate,
):
    existing_post = await get_post_by_id(session, post_id)
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
    updated_post = await update_post_service(session, post_id, post)
    return updated_post


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post: PostCreate,
    session: SessionDep,
    user: CurrentUser,
):
    new_post = await create_post_service(session, post, user.id)
    return new_post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    session: SessionDep,
    user: CurrentUser,
):
    existing_post = await get_post_by_id(session, post_id)
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
    await delete_post_service(session, existing_post)
