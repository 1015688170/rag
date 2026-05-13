from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from app.rag.retrievers.azure_search_retriever import AzureSearchRetriever
from app.schemas.chat import ChatRequest, ChatResponse, SourceItem

if TYPE_CHECKING:
    from app.services.embedding_service import EmbeddingService
    from app.services.llm_service import LLMService
    from app.services.rerank_service import RerankService
    from app.services.search_service import SearchService


class RagState(TypedDict, total=False):
    request: ChatRequest
    index_name: str
    documents: list[Document]
    raw_docs: list[dict[str, Any]]
    reranked_docs: list[dict[str, Any]]


NO_RETRIEVAL_ANSWER = "抱歉，当前知识库中未检索到相关片段，无法生成可信回答。"

LOW_RELEVANCE_ANSWER_TEMPLATE = (
    "抱歉，当前检索到的资料与问题相关性不足，无法生成严谨合规的可信回答。\n\n"
    "系统已启用证据门槛：重排分低于 {threshold:g} 的片段不会进入生成阶段。"
    "建议补充更明确的问题关键词，或完善知识库中的相关运维规范、SOP、命令示例和故障说明。"
)


class RagChain:
    """LangChain orchestration layer that keeps existing services as execution backends."""

    def __init__(
        self,
        embedding_service: "EmbeddingService",
        search_service: "SearchService",
        rerank_service: "RerankService",
        llm_service: "LLMService",
    ) -> None:
        self.retriever = AzureSearchRetriever(
            embedding_service=embedding_service,
            search_service=search_service,
        )
        self.rerank_service = rerank_service
        self.llm_service = llm_service
        self.chain = (
            RunnableLambda(self._retrieve_step)
            | RunnableLambda(self._rerank_step)
            | RunnableLambda(self._answer_step)
        )

    def invoke(self, request: ChatRequest) -> ChatResponse:
        return self.chain.invoke({"request": request})

    def _retrieve_step(self, state: RagState) -> RagState:
        request: ChatRequest = state["request"]
        index_name = self.retriever.resolve_index_name(request.embedding_model, request.index_name)
        documents = self.retriever.retrieve(
            query_text=request.question,
            embedding_model=request.embedding_model,
            index_name=index_name,
            top_k=request.top_k,
            user_id=request.user_id,
            department=request.department,
            roles=request.roles,
        )
        return {
            "request": request,
            "index_name": index_name,
            "documents": documents,
        }

    def _rerank_step(self, state: RagState) -> RagState:
        request: ChatRequest = state["request"]
        raw_docs = [self._document_to_source_doc(document) for document in state["documents"]]
        try:
            final_docs = self.rerank_service.rerank(
                query=request.question,
                docs=raw_docs,
                top_n=request.top_n,
            )
        except Exception:
            final_docs = self._fallback_to_recall_docs(raw_docs, request.top_n)
        return {
            "request": request,
            "index_name": state["index_name"],
            "documents": state["documents"],
            "raw_docs": raw_docs,
            "reranked_docs": final_docs,
        }

    def _answer_step(self, state: RagState) -> ChatResponse:
        request: ChatRequest = state["request"]
        index_name: str = state["index_name"]
        reranked_docs: list[dict[str, Any]] = state["reranked_docs"]

        if not reranked_docs:
            return ChatResponse(
                answer=NO_RETRIEVAL_ANSWER,
                model=request.chat_model,
                embedding_model=request.embedding_model,
                index_name=index_name,
                sources=[],
                source_count=0,
            )

        rejected_docs = reranked_docs
        final_docs = self._filter_docs_by_rerank_score(reranked_docs)
        if not final_docs:
            sources = [SourceItem(**doc) for doc in rejected_docs]
            return ChatResponse(
                answer=LOW_RELEVANCE_ANSWER_TEMPLATE.format(
                    threshold=self.rerank_service.settings.min_rerank_score,
                ),
                model=request.chat_model,
                embedding_model=request.embedding_model,
                index_name=index_name,
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
            index_name=index_name,
            sources=sources,
            source_count=len(sources),
        )

    def _document_to_source_doc(self, document: Document) -> dict[str, Any]:
        return {
            **document.metadata,
            "content": document.page_content,
        }

    def _fallback_to_recall_docs(self, docs: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
        fallback_docs: list[dict[str, Any]] = []
        for doc in docs[:top_n]:
            content = str(doc.get("content", ""))
            preview = " ".join(content.split())[:180]
            fallback_docs.append(
                {
                    **doc,
                    "score": float(doc.get("recall_score") or 0.0),
                    "rerank_score": None,
                    "score_source": "recall",
                    "preview": preview,
                }
            )
        return fallback_docs

    def _filter_docs_by_rerank_score(self, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not any(doc.get("rerank_score") is not None for doc in docs):
            return docs
        threshold = self.rerank_service.settings.min_rerank_score
        return [
            doc
            for doc in docs
            if doc.get("rerank_score") is not None and float(doc["rerank_score"]) >= threshold
        ]
