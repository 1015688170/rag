from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.rerank_service import RerankService
from app.services.search_service import SearchService

router = APIRouter(tags=["chat"])

chat_service = ChatService(
    embedding_service=EmbeddingService(settings),
    search_service=SearchService(settings),
    rerank_service=RerankService(settings),
    llm_service=LLMService(settings),
)


@router.post("/chat", response_model=ChatResponse, summary="RAG chat entrypoint")
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        return await chat_service.chat(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG pipeline failed: {exc}",
        ) from exc


@router.get("/rerank/status", summary="Inspect local reranker health")
async def rerank_status() -> dict:
    return chat_service.rerank_service.status()
