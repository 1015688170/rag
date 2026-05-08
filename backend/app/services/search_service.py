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
        from azure.core.exceptions import HttpResponseError, ResourceExistsError
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
                SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
                SearchableField(name="filename", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="filepath", type=SearchFieldDataType.String),
                SearchableField(name="section_title", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="section_path", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="source_type", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=vector_dimensions,
                    vector_search_profile_name=vector_profile_name,
                ),
                SimpleField(name="page_start", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
                SimpleField(name="page_end", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
                SimpleField(name="created_at", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SimpleField(name="file_hash", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="visibility", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="owner_id", type=SearchFieldDataType.String, filterable=True),
                SearchField(
                    name="allowed_departments",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    filterable=True,
                ),
                SearchField(
                    name="allowed_roles",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    filterable=True,
                ),
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
        except (ResourceExistsError, HttpResponseError) as exc:
            if not self._is_index_exists_error(exc):
                raise
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

    def _is_index_exists_error(self, exc: Exception) -> bool:
        error_code = str(getattr(getattr(exc, "error", None), "code", "") or getattr(exc, "error_code", ""))
        message = str(exc)
        exists_markers = (
            "ResourceNameAlreadyInUse",
            "CannotCreateExistingIndex",
            "already exists",
            "because it already exists",
        )
        return any(marker in error_code or marker in message for marker in exists_markers)

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

    def update_chunk_permissions_by_doc_id(
        self,
        index_name: str,
        doc_id: str,
        *,
        visibility: str,
        owner_id: str | None,
        allowed_departments: list[str],
        allowed_roles: list[str],
    ) -> int:
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
        updates = [
            {
                "id": str(row["id"]),
                "visibility": visibility,
                "owner_id": owner_id,
                "allowed_departments": allowed_departments,
                "allowed_roles": allowed_roles,
            }
            for row in results
            if row.get("id")
        ]
        if not updates:
            return 0
        update_results = client.merge_documents(documents=updates)
        return sum(1 for result in update_results if result.succeeded)

    def search(
        self,
        query_text: str,
        query_vector: list[float],
        embedding_model: EmbeddingModel,
        index_name: str | None = None,
        top_k: int = 10,
        user_id: str | None = None,
        department: str | None = None,
        roles: list[str] | None = None,
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
            filter=self._permission_filter(user_id=user_id, department=department, roles=roles),
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

    def _permission_filter(
        self,
        user_id: str | None = None,
        department: str | None = None,
        roles: list[str] | None = None,
    ) -> str:
        clauses = ["visibility eq 'public'"]
        normalized_user_id = user_id.strip() if user_id and user_id.strip() else None
        normalized_department = department.strip() if department and department.strip() else None
        normalized_roles: list[str] = []
        seen_roles: set[str] = set()
        for role in roles or []:
            normalized_role = str(role).strip()
            if not normalized_role or normalized_role in seen_roles:
                continue
            seen_roles.add(normalized_role)
            normalized_roles.append(normalized_role)

        if normalized_user_id:
            clauses.append(f"owner_id eq '{self._escape_odata_string(normalized_user_id)}'")
        if normalized_department:
            clauses.append(
                "allowed_departments/any(d: "
                f"d eq '{self._escape_odata_string(normalized_department)}'"
                ")"
            )
        if normalized_roles:
            escaped_roles = ",".join(self._escape_odata_string(role) for role in normalized_roles)
            clauses.append(f"allowed_roles/any(r: search.in(r, '{escaped_roles}'))")
        return " or ".join(clauses)

    def _escape_odata_string(self, value: str) -> str:
        return value.replace("'", "''")
