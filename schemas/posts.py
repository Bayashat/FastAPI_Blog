import uuid
from enum import StrEnum
from typing import Annotated, Any, Literal

from fastapi import Path
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from enums import PostStatus
from schemas.common import UserId
from schemas.users import UserPublic

PostId = Annotated[
    uuid.UUID,
    Field(title="Post ID", description="The unique identifier of the post"),
]
PostTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
PostContent = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
PostIdPathParam = Annotated[uuid.UUID, Path(title="Post ID", description="The unique identifier of the post")]
PostSearchParam = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class PostSortField(StrEnum):
    PUBLISHED_AT = "published_at"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    COMMENTS_COUNT = "comments_count"
    LIKES_COUNT = "likes_count"


class PostListParams(BaseModel):
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of elements to return")
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of elements to skip before starting to collect the result set",
    )
    # status: PostStatus = Field(default=PostStatus.PUBLISHED, description="Field used to filter by post status")
    order_by: PostSortField = Field(default=PostSortField.PUBLISHED_AT, description="Field used to order posts")
    order_direction: Literal["asc", "desc"] = Field(
        default="desc", description="Direction of ordering: ascending or descending"
    )

    author_id: uuid.UUID | None = Field(default=None, description="Filter posts by author ID")
    q: PostSearchParam | None = Field(
        default=None,
        description="Case-insensitive search in post title and content",
        examples=["fastapi"],
    )

    created_from: AwareDatetime | None = Field(
        default=None,
        description="Filter posts created from this date, inclusive",
        examples=["2024-01-01T00:00:00Z"],
    )
    created_before: AwareDatetime | None = Field(
        default=None,
        description="Filter posts created before this date, exclusive",
        examples=["2024-12-31T23:59:59Z"],
    )

    # tags: list[str] = []

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_created_range(self) -> "PostListParams":
        if (
            self.created_from is not None
            and self.created_before is not None
            and self.created_from >= self.created_before
        ):
            raise ValueError("created_from must be earlier than created_before")

        return self


class PostBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: PostTitle
    content: PostContent


class PostCreate(PostBase):
    status: Literal[
        PostStatus.DRAFT,
        PostStatus.PUBLISHED,
    ] = PostStatus.DRAFT


class PostUpdatePut(PostBase):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"title": "Updated Title", "content": "Updated content"}],
        },
    )


class PostUpdatePatch(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"title": "Updated Title", "content": "Updated content"}],
        },
    )

    title: PostTitle | None = None
    content: PostContent | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_patch_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        fields = {"title", "content"}
        provided_fields = fields & data.keys()

        if not provided_fields:
            raise ValueError("At least one field must be provided")

        null_fields = [field for field in provided_fields if data[field] is None]
        if null_fields:
            raise ValueError(f"Fields cannot be null: {', '.join(null_fields)}")

        return data


class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)

    id: PostId
    status: PostStatus
    user_id: UserId | None
    created_at: AwareDatetime
    updated_at: AwareDatetime
    published_at: AwareDatetime | None

    comments_count: int
    likes_count: int

    author: UserPublic | None

    @model_validator(mode="after")
    def validate_status_published_at(self) -> "PostResponse":
        if self.status is PostStatus.DRAFT:
            if self.published_at is not None:
                raise ValueError("Draft post cannot have published_at")
        else:
            if self.published_at is None:
                raise ValueError("Published or archived post must have published_at")

        return self


class PaginatedPostsResponse(BaseModel):
    posts: list[PostResponse]
    total: int
    skip: int
    limit: int
    has_more: bool

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "posts": [
                        {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "Sample Post",
                            "content": "This is a sample post content.",
                            "user_id": "123e4567-e89b-12d3-a456-426614174001",
                            "created_at": "2024-06-01T12:00:00Z",
                            "updated_at": "2024-06-01T12:00:00Z",
                            "comments_count": 3,
                            "likes_count": 10,
                            "author": {
                                "id": "123e4567-e89b-12d3-a456-426614174001",
                                "username": "sampleuser",
                                "image_file": "profile.jpg",
                                "image_path": "/images/profile.jpg",
                            },
                        }
                    ],
                    "total": 1,
                    "skip": 0,
                    "limit": 10,
                    "has_more": False,
                }
            ]
        }
    )


class UserPostItem(PostBase):
    model_config = ConfigDict(from_attributes=True)

    id: PostId
    status: PostStatus
    created_at: AwareDatetime
    updated_at: AwareDatetime
    published_at: AwareDatetime | None

    comments_count: int
    likes_count: int


class UserPostsResponse(BaseModel):
    user: UserPublic
    posts: list[UserPostItem]
    total: int
    skip: int
    limit: int
    has_more: bool
