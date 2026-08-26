from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from schemas.posts import PostId


class PostLikeStateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    liked: bool = Field(description="Desired like state for the current user")


class PostLikeStateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    post_id: PostId
    liked: bool
    likes_count: int = Field(ge=0)
