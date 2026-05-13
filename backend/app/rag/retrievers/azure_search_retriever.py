from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.documents import Document

from app.schemas.chat import EmbeddingModel

if TYPE_CHECKING:
    from app.services.embedding_service import EmbeddingService
    from app.services.search_service import SearchService


class AzureSearchRetriever:
    """LangChain document adapter for the existing Azure AI Search service."""

    def __init__(self, embedding_service: EmbeddingService, search_service: SearchService) -> None:
        self.embedding_service = embedding_service
        self.search_service = search_service

    def resolve_index_name(self, embedding_model: EmbeddingModel, index_name: str | None = None) -> str:
        return self.search_service.resolve_index_name(embedding_model, index_name)

    def retrieve(
        self,
        *,
        query_text: str,
        embedding_model: EmbeddingModel,
        index_name: str,
        top_k: int,
        user_id: str | None = None,
        department: str | None = None,
        roles: list[str] | None = None,
    ) -> list[Document]:
        query_vector = self.embedding_service.embed(query_text, embedding_model)
        rows = self.search_service.search(
            query_text=query_text,
            query_vector=query_vector,
            embedding_model=embedding_model,
            index_name=index_name,
            top_k=top_k,
            user_id=user_id,
            department=department,
            roles=roles,
        )
        return [self._to_document(row) for row in rows]

    def _to_document(self, row: dict[str, Any]) -> Document:
        content = str(row.get("content", ""))
        metadata = {key: value for key, value in row.items() if key != "content"}
        return Document(page_content=content, metadata=metadata)
