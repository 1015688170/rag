from __future__ import annotations

from typing import Any
import re

from app.core.config import Settings
from app.schemas.chat import EmbeddingModel


class SearchService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def list_indexes(self) -> list[str]:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents.indexes import SearchIndexClient

        client = SearchIndexClient(
            endpoint=self.settings.search_endpoint,
            credential=AzureKeyCredential(self.settings.search_key),
        )
        return sorted(client.list_index_names())

    def default_index_for_model(self, embedding_model: EmbeddingModel) -> str:
        if embedding_model == EmbeddingModel.google_005:
            return self.settings.index_005
        return self.settings.index_ada

    def resolve_index_name(self, embedding_model: EmbeddingModel, index_name: str | None = None) -> str:
        selected_index = (index_name or "").strip() or self.default_index_for_model(embedding_model)
        if not selected_index:
            raise ValueError("Azure AI Search index is not configured.")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,126}[A-Za-z0-9]", selected_index):
            raise ValueError("Invalid Azure AI Search index name.")
        return selected_index

    def upload_documents(self, index_name: str, documents: list[dict[str, Any]]) -> int:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient

        client = SearchClient(
            endpoint=self.settings.search_endpoint,
            index_name=self.resolve_index_name(EmbeddingModel.ada_002, index_name),
            credential=AzureKeyCredential(self.settings.search_key),
        )
        results = client.merge_or_upload_documents(documents=documents)
        return sum(1 for result in results if result.succeeded)

    def index_chunks(self, index_name: str, chunks: list[dict[str, Any]], batch_size: int = 100) -> int:
        uploaded_count = 0
        for start in range(0, len(chunks), batch_size):
            uploaded_count += self.upload_documents(index_name, chunks[start : start + batch_size])
        return uploaded_count

    def search(
        self,
        query_text: str,
        query_vector: list[float],
        embedding_model: EmbeddingModel,
        index_name: str | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient
        from azure.search.documents.models import VectorizedQuery

        index_name = self.resolve_index_name(embedding_model, index_name)

        client = SearchClient(
            endpoint=self.settings.search_endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(self.settings.search_key),
        )
        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=top_k,
            fields="content_vector",
        )
        results = client.search(
            search_text=query_text,
            vector_queries=[vector_query],
            select=["id", "filepath", "content"],
            top=top_k,
        )

        documents: list[dict[str, Any]] = []
        for row in results:
            recall_score = row.get("@search.score")
            documents.append(
                {
                    "doc_id": str(row.get("id", "")),
                    "filepath": str(row.get("filepath", "unknown")),
                    "content": str(row.get("content", "")),
                    "recall_score": float(recall_score) if recall_score is not None else None,
                }
            )
        return documents
