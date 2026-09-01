import uuid
from typing import Annotated

from fastapi import Path
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from commons import ListQueryParamsBase
from schemas.posts import PostId
from schemas.users import UserPublic

CommentIdPathParam = Annotated[uuid.UUID, Path(title="Comment ID", description="The unique identifier of the comment")]
CommentId = Annotated[uuid.UUID, Field(title="Comment ID", description="The unique identifier of the comment")]
CommentContent = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=5000,
    ),
]


class CommentListParams(ListQueryParamsBase):
    pass


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
    model_config = ConfigDict(extra="forbid")

    content: CommentContent
