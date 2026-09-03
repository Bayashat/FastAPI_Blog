from pydantic import BaseModel

from schemas.users import UserPublic


class FollowersResponse(BaseModel):
    user: UserPublic
    followers: list[UserPublic]
    total: int
    skip: int
    limit: int
    has_more: bool


class FollowingResponse(BaseModel):
    user: UserPublic
    following: list[UserPublic]
    total: int
    skip: int
    limit: int
    has_more: bool
