from typing import Annotated

from fastapi import APIRouter, Query, status

from dependencies import SessionDep
from models.tags import Tag
from schemas.tags import ListTagResponse, TagListParams
from services import tags as tag_service

router = APIRouter(prefix="/api/tags")


@router.get(
    "/",
    response_model=ListTagResponse,
    status_code=status.HTTP_200_OK,
)
async def get_all_tags(
    session: SessionDep,
    query_params: Annotated[TagListParams, Query()],
) -> list[Tag]:
    total_count = await tag_service.count_tags(session)
    tags: list[Tag] = await tag_service.list_tags(session, query_params)

    has_more = (query_params.skip + len(tags)) < total_count

    return ListTagResponse.model_validate(
        {
            "tags": tags,
            "total": total_count,
            "skip": query_params.skip,
            "limit": query_params.limit,
            "has_more": has_more,
        }
    )
