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

    def vector_dimensions_for_model(self, embedding_model: EmbeddingModel) -> int:
        if embedding_model == EmbeddingModel.google_005:
            return self.settings.google_005_vector_dimensions
        return self.settings.ada002_vector_dimensions

    def resolve_index_name(self, embedding_model: EmbeddingModel, index_name: str | None = None) -> str:
        selected_index = (index_name or "").strip() or self.default_index_for_model(embedding_model)
        if not selected_index:
            raise ValueError("Azure AI Search index is not configured.")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,126}[A-Za-z0-9]", selected_index):
            raise ValueError("Invalid Azure AI Search index name.")
        return selected_index

    def create_chunk_index(self, embedding_model: EmbeddingModel, index_name: str | None = None) -> dict[str, Any]:
        from azure.core.credentials import AzureKeyCredential
        from azure.core.exceptions import ResourceExistsError
        from azure.search.documents.indexes import SearchIndexClient
        from azure.search.documents.indexes.models import (
            HnswAlgorithmConfiguration,
            SearchableField,
            SearchField,
            SearchFieldDataType,
            SearchIndex,
            SimpleField,
            VectorSearch,
            VectorSearchProfile,
        )

        selected_index = self.resolve_index_name(embedding_model, index_name)
        vector_dimensions = self.vector_dimensions_for_model(embedding_model)
        if vector_dimensions <= 0:
            raise ValueError("Vector dimensions must be greater than 0.")

        client = SearchIndexClient(
            endpoint=self.settings.search_endpoint,
            credential=AzureKeyCredential(self.settings.search_key),
        )
        vector_profile_name = "rag-vector-profile"
        vector_algorithm_name = "rag-hnsw"
        index = SearchIndex(
            name=selected_index,
            fields=[
                SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
                SimpleField(name="doc_id", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="chunk_id", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="filename", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="filepath", type=SearchFieldDataType.String),
                SearchableField(name="section_title", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="source_type", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=vector_dimensions,
                    vector_search_profile_name=vector_profile_name,
                ),
                SimpleField(name="created_at", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SimpleField(name="file_hash", type=SearchFieldDataType.String, filterable=True),
            ],
            vector_search=VectorSearch(
                algorithms=[HnswAlgorithmConfiguration(name=vector_algorithm_name)],
                profiles=[
                    VectorSearchProfile(
                        name=vector_profile_name,
                        algorithm_configuration_name=vector_algorithm_name,
                    )
                ],
            ),
        )

        try:
            client.create_index(index)
        except ResourceExistsError:
            return {
                "index_name": selected_index,
                "status": "already_exists",
                "message": "index already exists",
                "embedding_model": embedding_model,
                "vector_dimensions": vector_dimensions,
            }

        return {
            "index_name": selected_index,
            "status": "created",
            "message": "index created successfully",
            "embedding_model": embedding_model,
            "vector_dimensions": vector_dimensions,
        }

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

    def delete_chunks_by_doc_id(self, index_name: str, doc_id: str) -> int:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient

        client = SearchClient(
            endpoint=self.settings.search_endpoint,
            index_name=self.resolve_index_name(EmbeddingModel.ada_002, index_name),
            credential=AzureKeyCredential(self.settings.search_key),
        )
        escaped_doc_id = doc_id.replace("'", "''")
        results = client.search(
            search_text="*",
            filter=f"doc_id eq '{escaped_doc_id}'",
            select=["id"],
            top=1000,
        )
        keys = [{"id": str(row["id"])} for row in results if row.get("id")]
        if not keys:
            return 0
        delete_results = client.delete_documents(documents=keys)
        return sum(1 for result in delete_results if result.succeeded)

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
