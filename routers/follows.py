from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from config import settings
from dependencies import CurrentUser, SessionDep
from models.users import User
from schemas.common import UserId
from schemas.follows import FollowersResponse, FollowingResponse
from services import follows as follow_service
from services import users as user_service

router = APIRouter(prefix="/api/users/{user_id}")


@router.put("/follow", status_code=status.HTTP_204_NO_CONTENT)
async def follow_user(
    session: SessionDep,
    current_user: CurrentUser,
    user_id: UserId,
) -> None:
    target_user = await user_service.get_user_by_id(session, user_id)

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!",
        )

    if current_user.id == target_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can't follow yourself!",
        )

    await follow_service.follow_user(
        session=session,
        follower_id=current_user.id,
        followed_user_id=target_user.id,
    )


@router.delete("/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user(
    session: SessionDep,
    current_user: CurrentUser,
    user_id: UserId,
) -> None:
    target_user = await user_service.get_user_by_id(session, user_id)
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!",
        )
    if current_user.id == target_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can't unfollow yourself!",
        )
    await follow_service.unfollow_user(
        session=session,
        follower_id=current_user.id,
        followed_user_id=target_user.id,
    )


@router.get("/followers", response_model=FollowersResponse, status_code=status.HTTP_200_OK)
async def list_followers(
    session: SessionDep,
    user_id: UserId,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
) -> FollowersResponse:
    target_user = await user_service.get_user_by_id(session, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!",
        )

    total_count = await follow_service.count_followers(session, target_user.id)
    followers: Sequence[User] = await follow_service.list_followers(
        session=session,
        user_id=target_user.id,
    )

    has_more = skip + len(followers) < total_count

    return FollowersResponse.model_validate(
        {
            "user": target_user,
            "followers": followers,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "has_more": has_more,
        }
    )


@router.get("/following", response_model=FollowingResponse, status_code=status.HTTP_200_OK)
async def list_following(
    session: SessionDep,
    user_id: UserId,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
) -> FollowingResponse:
    target_user = await user_service.get_user_by_id(session, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!",
        )

    total_count = await follow_service.count_followed_users(session, target_user.id)
    followed_users: Sequence[User] = await follow_service.list_followed_users(
        session=session,
        user_id=target_user.id,
    )

    has_more = skip + len(followed_users) < total_count

    return FollowingResponse.model_validate(
        {
            "user": target_user,
            "following": followed_users,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "has_more": has_more,
        }
    )
