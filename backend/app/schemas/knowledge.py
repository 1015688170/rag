from pydantic import BaseModel, Field
from datetime import datetime

from pydantic import field_validator

from app.core.permissions import parse_string_list
from app.schemas.chat import EmbeddingModel


class IndexListResponse(BaseModel):
    indexes: list[str] = Field(default_factory=list)
    defaults: dict[str, str] = Field(default_factory=dict)


class SearchIndexCreateRequest(BaseModel):
    index_name: str | None = Field(default=None, min_length=1, max_length=128)
    embedding_model: EmbeddingModel = Field(default=EmbeddingModel.ada_002)


class SearchIndexCreateResponse(BaseModel):
    index_name: str
    status: str
    message: str
    embedding_model: EmbeddingModel
    vector_dimensions: int


class DocumentUploadResponse(BaseModel):
    document_id: str
    task_id: str
    filename: str
    file_hash: str
    chunk_count: int
    status: str
    index_name: str | None = None
    embedding_model: EmbeddingModel | None = None
    visibility: str
    owner_id: str | None = None
    allowed_departments: list[str] = Field(default_factory=list)
    allowed_roles: list[str] = Field(default_factory=list)

    @field_validator("allowed_departments", "allowed_roles", mode="before")
    @classmethod
    def parse_list_fields(cls, value: object) -> list[str]:
        return parse_string_list(value)  # type: ignore[arg-type]


class DocumentListItem(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    error_message: str | None = None
    visibility: str
    owner_id: str | None = None
    allowed_departments: list[str] = Field(default_factory=list)
    allowed_roles: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @field_validator("allowed_departments", "allowed_roles", mode="before")
    @classmethod
    def parse_list_fields(cls, value: object) -> list[str]:
        return parse_string_list(value)  # type: ignore[arg-type]


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem] = Field(default_factory=list)


class DocumentPermissionUpdateRequest(BaseModel):
    visibility: str = Field(default="public")
    owner_id: str | None = None
    allowed_departments: list[str] = Field(default_factory=list)
    allowed_roles: list[str] = Field(default_factory=list)

    @field_validator("allowed_departments", "allowed_roles", mode="before")
    @classmethod
    def parse_list_fields(cls, value: object) -> list[str]:
        return parse_string_list(value)  # type: ignore[arg-type]


class DocumentPermissionUpdateResponse(DocumentListItem):
    updated_chunks: int


class IngestTaskResponse(BaseModel):
    task_id: str
    document_id: str
    filename: str
    status: str
    stage: str | None = None
    chunk_count: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentDeleteResponse(BaseModel):
    document_id: str
    status: str
    deleted_chunks: int
