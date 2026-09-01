import uuid
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from commons import ListQueryParamsBase
from schemas.common import PostId, UserId

TagId = Annotated[
    uuid.UUID,
    Field(title="Tag ID", description="The unique identifier of the Tag"),
]

TagName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=1,
        max_length=64,
    ),
]


class TagListParams(ListQueryParamsBase):
    pass


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: TagId
    name: TagName
    created_at: AwareDatetime


class PostTagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    post_id: PostId
    tag_id: TagId
    added_by_user_id: UserId | None
    added_at: AwareDatetime


class ListTagResponse(BaseModel):
    tags: list[TagResponse]
    total: int
    skip: int
    limit: int
    has_more: bool
