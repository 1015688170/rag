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
        rejected_docs = final_docs
        final_docs = self._filter_docs_by_rerank_score(final_docs)
        if not final_docs:
            sources = [SourceItem(**doc) for doc in rejected_docs]
            return ChatResponse(
                answer=(
                    "抱歉，当前检索到的资料与问题相关性不足，无法生成严谨合规的可信回答。\n\n"
                    f"系统已启用证据门槛：重排分低于 {self.rerank_service.settings.min_rerank_score:g} 的片段不会进入生成阶段。"
                    "建议补充更明确的问题关键词，或完善知识库中的相关运维规范、SOP、命令示例和故障说明。"
                ),
                model=request.chat_model,
                embedding_model=request.embedding_model,
                sources=sources,
                source_count=len(sources),
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

    def _filter_docs_by_rerank_score(self, docs: list[dict]) -> list[dict]:
        if not any(doc.get("rerank_score") is not None for doc in docs):
            return docs
        threshold = self.rerank_service.settings.min_rerank_score
        return [
            doc
            for doc in docs
            if doc.get("rerank_score") is not None and float(doc["rerank_score"]) >= threshold
        ]
