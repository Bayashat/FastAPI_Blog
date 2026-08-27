import uuid
from typing import Annotated, Literal

from fastapi import Path
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
)

from schemas.posts import PostId
from schemas.users import UserPublic

CommentIdPathParam = Annotated[uuid.UUID, Path(title="Comment ID", description="The unique identifier of the comment")]
CommentId = Annotated[uuid.UUID, Field(title="Comment ID", description="The unique identifier of the comment")]
CommentContent = Annotated[str, Field(title="Comment content", description="The content of the comment")]


class CommentListParams(BaseModel):
    limit: int = Field(10, ge=1, le=100, description="Maximum number of elements to return")
    skip: int = Field(0, ge=0, description="Number of elements to skip before starting to collect the result set")
    order_direction: Literal["asc", "desc"] = Field(
        "desc", description="Direction of ordering by created_at: ascending or descending"
    )

    model_config = ConfigDict(extra="forbid")


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: CommentId
    post_id: PostId
    content: CommentContent
    created_at: AwareDatetime
    updated_at: AwareDatetime

    user: UserPublic | None


class ListCommentsResponse(BaseModel):
    comments: list[CommentResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


class CommentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: CommentContent


class UpdateCommentRequest(BaseModel):
    content: CommentContent
