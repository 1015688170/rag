import logging

from fastapi import APIRouter, HTTPException, status

from app.api.routes.chat import search_service
from app.schemas.knowledge import SearchIndexCreateRequest, SearchIndexCreateResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["search-index"])


@router.post("/search-index/create", response_model=SearchIndexCreateResponse, summary="Create a RAG chunk index")
async def create_search_index(request: SearchIndexCreateRequest = SearchIndexCreateRequest()) -> SearchIndexCreateResponse:
    try:
        result = search_service.create_chunk_index(
            embedding_model=request.embedding_model,
            index_name=request.index_name,
        )
        return SearchIndexCreateResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Search index creation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search index creation failed.",
        ) from exc
