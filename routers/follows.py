from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, status

from dependencies import CurrentUser, SessionDep
from models.users import User
from schemas.common import UserId
from schemas.follows import FollowersResponse, FollowingsResponse
from services import follows as follow_service
from services import users as user_service

router = APIRouter(prefix="/api/users/{user_id}")


@router.put("/follow", status_code=status.HTTP_204_NO_CONTENT)
async def follow_user(
    session: SessionDep,
    user: CurrentUser,
    user_id: UserId,
) -> None:
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!",
        )
    if user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can't follow yourself!",
        )
    await follow_service.follow_user(
        session=session,
        follower_id=user.id,
        followed_user_id=user_id,
    )


@router.delete("/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user(
    session: SessionDep,
    user: CurrentUser,
    user_id: UserId,
) -> None:
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!",
        )
    if user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can't unfollow yourself!",
        )
    await follow_service.unfollow_user(
        session=session,
        follower_id=user.id,
        followed_user_id=user_id,
    )


@router.get("/followers", response_model=FollowersResponse, status_code=status.HTTP_200_OK)
async def get_followers(
    session: SessionDep,
    user_id: UserId,
) -> FollowersResponse:
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!",
        )

    followers: Sequence[User] = await follow_service.get_followers(
        session=session,
        user_id=user_id,
    )

    return FollowersResponse.model_validate({"user": user, "followers": followers})


@router.get("/following", response_model=FollowingsResponse, status_code=status.HTTP_200_OK)
async def get_followings(
    session: SessionDep,
    user_id: UserId,
) -> FollowingsResponse:
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!",
        )

    followings: Sequence[User] = await follow_service.get_followings(
        session=session,
        user_id=user_id,
    )

    return FollowingsResponse.model_validate({"user": user, "followings": followings})
