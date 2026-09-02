from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Query, status

from dependencies import SessionDep
from models.tags import Tag
from schemas.tags import PaginatedTagsResponse, TagListParams
from services import tags as tag_service

router = APIRouter(prefix="/api/tags")


@router.get(
    "",
    response_model=PaginatedTagsResponse,
    status_code=status.HTTP_200_OK,
)
async def list_tags(
    session: SessionDep,
    query_params: Annotated[TagListParams, Query()],
) -> PaginatedTagsResponse:
    total_count = await tag_service.count_tags(session)
    tags: Sequence[Tag] = await tag_service.list_tags(session, query_params)

    has_more = (query_params.skip + len(tags)) < total_count

    return PaginatedTagsResponse.model_validate(
        {
            "tags": tags,
            "total": total_count,
            "skip": query_params.skip,
            "limit": query_params.limit,
            "has_more": has_more,
        }
    )
