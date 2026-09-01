from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ListQueryParamsBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of elements to return")
    skip: int = Field(
        default=0, ge=0, description="Number of elements to skip before starting to collect the result set"
    )
    order_direction: Literal["asc", "desc"] = Field(
        default="desc", description="Direction of ordering by created_at: ascending or descending"
    )
