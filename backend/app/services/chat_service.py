from __future__ import annotations

from app.rag.chains.rag_chain import RagChain
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.rerank_service import RerankService
from app.services.search_service import SearchService


class ChatService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        search_service: SearchService,
        rerank_service: RerankService,
        llm_service: LLMService,
    ) -> None:
        self.embedding_service = embedding_service
        self.search_service = search_service
        self.rerank_service = rerank_service
        self.llm_service = llm_service
        self.rag_chain = RagChain(
            embedding_service=embedding_service,
            search_service=search_service,
            rerank_service=rerank_service,
            llm_service=llm_service,
        )

    async def chat(self, request: ChatRequest) -> ChatResponse:
        return self.rag_chain.invoke(request)
