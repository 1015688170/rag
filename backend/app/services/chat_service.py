from __future__ import annotations

from app.schemas.chat import ChatRequest, ChatResponse, SourceItem
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

    async def chat(self, request: ChatRequest) -> ChatResponse:
        query_vector = self.embedding_service.embed(request.question, request.embedding_model)
        raw_docs = self.search_service.search(
            query_text=request.question,
            query_vector=query_vector,
            embedding_model=request.embedding_model,
            top_k=request.top_k,
        )
        try:
            final_docs = self.rerank_service.rerank(
                query=request.question,
                docs=raw_docs,
                top_n=request.top_n,
            )
        except Exception:
            # Hard fallback: if rerank stack is broken (transformers/torch mismatch),
            # still return something usable by taking the first top_n recall chunks.
            final_docs = []
            for doc in raw_docs[: request.top_n]:
                content = str(doc.get("content", ""))
                preview = " ".join(content.split())[:180]
                final_docs.append(
                    {
                        **doc,
                        "score": float(doc.get("recall_score") or 0.0),
                        "rerank_score": None,
                        "score_source": "recall",
                        "preview": preview,
                    }
                )
        if not final_docs:
            return ChatResponse(
                answer="抱歉，当前知识库中未检索到相关片段，无法生成可信回答。",
                model=request.chat_model,
                embedding_model=request.embedding_model,
                sources=[],
                source_count=0,
            )
        answer = self.llm_service.generate(
            user_question=request.question,
            context_chunks=final_docs,
            chat_model=request.chat_model,
            prompt_template=request.prompt_template,
        )
        sources = [SourceItem(**doc) for doc in final_docs]
        return ChatResponse(
            answer=answer,
            model=request.chat_model,
            embedding_model=request.embedding_model,
            sources=sources,
            source_count=len(sources),
        )
