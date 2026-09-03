from pydantic import BaseModel

from schemas.users import UserPublic


class FollowersResponse(BaseModel):
    user: UserPublic
    followers: list[UserPublic]


class FollowingsResponse(BaseModel):
    user: UserPublic
    followings: list[UserPublic]
