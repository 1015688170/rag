from pydantic import BaseModel, Field
from datetime import datetime

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


class DocumentListItem(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem] = Field(default_factory=list)


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
