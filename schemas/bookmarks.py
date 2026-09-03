from pydantic import AwareDatetime, BaseModel, ConfigDict

from schemas.common import PostId, UserId
from schemas.posts import PostResponse
from schemas.users import UserPublic


class SavedPostResponse(BaseModel):
    user: UserPublic
    posts: list[PostResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


class BookmarkItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    post_id: PostId
    user_id: UserId
    saved_at: AwareDatetime
