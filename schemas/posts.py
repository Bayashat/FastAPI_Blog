import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from schemas.users import UserPublic

PostTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
PostContent = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PostBase(BaseModel):
    title: PostTitle
    content: PostContent


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: PostTitle | None = None
    content: PostContent | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_values(cls, data: Any) -> Any:
        if isinstance(data, dict):
            null_fields = [field for field in ("title", "content") if field in data and data[field] is None]
            if null_fields:
                raise ValueError("Post update fields cannot be null")
        return data

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    created_at: datetime

    author: UserPublic | None


class PostResponseWithoutAuthor(PostBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime


class PaginatedPostsResponse(BaseModel):
    posts: list[PostResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


class UserPostsResponse(BaseModel):
    user: UserPublic
    posts: list[PostResponseWithoutAuthor]
    total: int
    skip: int
    limit: int
    has_more: bool
