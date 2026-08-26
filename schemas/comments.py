from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from schemas.users import UserPublic


class CommentListParams(BaseModel):
    limit: int = Field(10, ge=1, le=100, description="Maximum number of elements to return")
    skip: int = Field(0, ge=0, description="Number of elements to skip before starting to collect the result set")
    order_direction: Literal["asc", "desc"] = Field(
        "desc", description="Direction of ordering by created_at: ascending or descending"
    )

    model_config = ConfigDict(extra="forbid")


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    content: str
    created_at: datetime

    user: UserPublic | None


class ListCommentsResponse(BaseModel):
    comments: list[CommentResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


class CommentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
