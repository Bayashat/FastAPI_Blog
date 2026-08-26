from fastapi import APIRouter, HTTPException, status

from auth import CurrentUser
from dependencies import SessionDep
from schemas.likes import PostLikeStateResponse, PostLikeStateUpdate
from schemas.posts import PostIdPathParam
from services.likes import (
    PostLikeState,
    PostNotFoundError,
    set_post_like_state,
)

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
) -> PostLikeState:
    try:
        return await set_post_like_state(
            session=session,
            post_id=post_id,
            user_id=user.id,
            liked=like_data.liked,
        )
    except PostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        ) from exc
