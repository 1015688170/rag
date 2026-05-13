from __future__ import annotations

from types import SimpleNamespace

from langchain_core.documents import Document

from app.rag.chains.rag_chain import LOW_RELEVANCE_ANSWER_TEMPLATE, NO_RETRIEVAL_ANSWER, RagChain
from app.rag.retrievers.azure_search_retriever import AzureSearchRetriever
from app.schemas.chat import ChatModel, ChatRequest, EmbeddingModel


class FakeEmbeddingService:
    def embed(self, text: str, model: EmbeddingModel) -> list[float]:
        return [0.1, 0.2, 0.3]


class FakeSearchService:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self.rows = rows or []
        self.last_query_vector = None

    def resolve_index_name(self, embedding_model: EmbeddingModel, index_name: str | None = None) -> str:
        return index_name or "default-index"

    def search(self, **kwargs) -> list[dict]:
        self.last_query_vector = kwargs["query_vector"]
        return self.rows


class FakeRerankService:
    def __init__(self, docs: list[dict] | None = None, min_score: float = 0.0) -> None:
        self.docs = docs
        self.settings = SimpleNamespace(min_rerank_score=min_score)

    def rerank(self, query: str, docs: list[dict], top_n: int = 5) -> list[dict]:
        if self.docs is not None:
            return self.docs[:top_n]
        ranked = []
        for doc in docs[:top_n]:
            ranked.append(
                {
                    **doc,
                    "score": 0.8,
                    "rerank_score": 0.8,
                    "score_source": "rerank",
                    "preview": doc["content"][:180],
                }
            )
        return ranked


class FakeLLMService:
    def __init__(self) -> None:
        self.calls = 0

    def generate(
        self,
        user_question: str,
        context_chunks: list[dict],
        chat_model: ChatModel,
        prompt_template: str | None = None,
    ) -> str:
        self.calls += 1
        return f"answer from {len(context_chunks)} chunks"


def test_azure_search_retriever_returns_documents() -> None:
    search_service = FakeSearchService(
        rows=[
            {
                "doc_id": "chunk-1",
                "filepath": "runbook.md",
                "content": "restart service steps",
                "recall_score": 2.5,
            }
        ]
    )
    retriever = AzureSearchRetriever(FakeEmbeddingService(), search_service)

    docs = retriever.retrieve(
        query_text="how to restart",
        embedding_model=EmbeddingModel.ada_002,
        index_name="ops-index",
        top_k=3,
        user_id="u1",
        department="ops",
        roles=["admin"],
    )

    assert len(docs) == 1
    assert isinstance(docs[0], Document)
    assert docs[0].page_content == "restart service steps"
    assert docs[0].metadata["doc_id"] == "chunk-1"
    assert docs[0].metadata["filepath"] == "runbook.md"
    assert search_service.last_query_vector == [0.1, 0.2, 0.3]


def test_rag_chain_refuses_when_retrieval_is_empty() -> None:
    llm_service = FakeLLMService()
    chain = RagChain(
        embedding_service=FakeEmbeddingService(),
        search_service=FakeSearchService(rows=[]),
        rerank_service=FakeRerankService(),
        llm_service=llm_service,
    )

    response = chain.invoke(ChatRequest(question="unknown", index_name="ops-index"))

    assert response.answer == NO_RETRIEVAL_ANSWER
    assert response.sources == []
    assert response.source_count == 0
    assert response.index_name == "ops-index"
    assert llm_service.calls == 0


def test_rag_chain_filters_by_rerank_threshold_and_refuses_generation() -> None:
    low_score_doc = {
        "doc_id": "chunk-1",
        "filepath": "runbook.md",
        "content": "weakly related content",
        "score": 0.2,
        "rerank_score": 0.2,
        "recall_score": 3.0,
        "score_source": "rerank",
        "preview": "weakly related content",
    }
    llm_service = FakeLLMService()
    chain = RagChain(
        embedding_service=FakeEmbeddingService(),
        search_service=FakeSearchService(
            rows=[
                {
                    "doc_id": "chunk-1",
                    "filepath": "runbook.md",
                    "content": "weakly related content",
                    "recall_score": 3.0,
                }
            ]
        ),
        rerank_service=FakeRerankService(docs=[low_score_doc], min_score=0.5),
        llm_service=llm_service,
    )

    response = chain.invoke(ChatRequest(question="deploy rollback", index_name="ops-index"))

    assert response.answer == LOW_RELEVANCE_ANSWER_TEMPLATE.format(threshold=0.5)
    assert response.source_count == 1
    assert response.sources[0].rerank_score == 0.2
    assert llm_service.calls == 0
