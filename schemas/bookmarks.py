from pydantic import AwareDatetime, BaseModel, ConfigDict

from enums import PostStatus
from schemas.common import PostContent, PostId, PostTitle, UserId
from schemas.tags import TagResponse
from schemas.users import UserPublic


class UserPostItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PostId
    title: PostTitle
    content: PostContent
    status: PostStatus
    created_at: AwareDatetime
    updated_at: AwareDatetime
    published_at: AwareDatetime | None

    comments_count: int
    likes_count: int

    author: UserPublic | None
    tags: list[TagResponse]


class UserBookmarksResponse(BaseModel):
    user: UserPublic
    bookmarks: list[UserPostItem]
    total: int
    skip: int
    limit: int
    has_more: bool


class BookmarkItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    post_id: PostId
    user_id: UserId
    saved_at: AwareDatetime
