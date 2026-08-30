from fastapi import APIRouter, HTTPException, status

from auth import CurrentUser
from dependencies import SessionDep
from enums import PostStatus
from schemas.likes import PostLikeStateResponse, PostLikeStateUpdate
from schemas.posts import PostIdPathParam
from services import likes as like_service
from services import posts as post_service

router = APIRouter(prefix="/api/posts/{post_id}")


@router.put(
    "/like",
    response_model=PostLikeStateResponse,
    status_code=status.HTTP_200_OK,
)
async def set_post_like_status(
    session: SessionDep,
    user: CurrentUser,
    post_id: PostIdPathParam,
    like_data: PostLikeStateUpdate,
) -> like_service.PostLikeState:
    existing_post = await post_service.get_post_for_write(session, post_id)
    if not existing_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found!",
        )

    is_owner = user.id == existing_post.user_id

    if not is_owner and existing_post.status is not PostStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found!",
        )

    # even the owner itself shouldn't set like state when post is in draft/archived status
    if existing_post.status is not PostStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot set like state to an unpublished post!",
        )

    try:
        return await like_service.set_post_like_state(
            session=session,
            post_id=post_id,
            user_id=user.id,
            liked=like_data.liked,
        )
    except like_service.PostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        ) from exc
