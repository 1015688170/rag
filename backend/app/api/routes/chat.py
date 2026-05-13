import logging

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse, EmbeddingModel
from app.schemas.knowledge import IndexListResponse
from app.services.chat_service import ChatService
from app.services.document_ingest_service import DocumentIngestService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.rerank_service import RerankService
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

embedding_service = EmbeddingService(settings)
search_service = SearchService(settings)

chat_service = ChatService(
    embedding_service=embedding_service,
    search_service=search_service,
    rerank_service=RerankService(settings),
    llm_service=LLMService(settings),
)
document_ingest_service = DocumentIngestService(
    embedding_service=embedding_service,
    search_service=search_service,
)


@router.post("/chat", response_model=ChatResponse, summary="RAG chat entrypoint")
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        return await chat_service.chat(request)
    except Exception as exc:
        logger.exception("RAG pipeline failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG pipeline failed.",
        ) from exc


@router.get("/rerank/status", summary="Inspect local reranker health")
async def rerank_status() -> dict:
    return chat_service.rerank_service.status()


@router.get("/indexes", response_model=IndexListResponse, summary="List Azure AI Search indexes")
async def list_indexes() -> IndexListResponse:
    defaults = {
        EmbeddingModel.ada_002.value: search_service.default_index_for_model(EmbeddingModel.ada_002),
        EmbeddingModel.google_005.value: search_service.default_index_for_model(EmbeddingModel.google_005),
    }
    try:
        indexes = search_service.list_indexes()
    except Exception:
        logger.exception("Failed to list Azure AI Search indexes")
        indexes = sorted({index for index in defaults.values() if index})
    return IndexListResponse(indexes=indexes, defaults=defaults)
