import uuid
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from commons import ListQueryParamsBase

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
    order_by: Literal["name", "created_at"] = Field(
        default="name",
        description="Field used to order tags",
    )


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: TagId
    name: TagName
    created_at: AwareDatetime


class PaginatedTagsResponse(BaseModel):
    tags: list[TagResponse]
    total: int
    skip: int
    limit: int
    has_more: bool
