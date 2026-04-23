from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.schemas.chat import EmbeddingModel


class SearchService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def search(
        self,
        query_text: str,
        query_vector: list[float],
        embedding_model: EmbeddingModel,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient
        from azure.search.documents.models import VectorizedQuery

        index_name = self.settings.index_ada
        if embedding_model == EmbeddingModel.google_005:
            index_name = self.settings.index_005

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
