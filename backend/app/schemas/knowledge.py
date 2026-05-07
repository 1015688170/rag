from pydantic import BaseModel, Field

from app.schemas.chat import EmbeddingModel


class IndexListResponse(BaseModel):
    indexes: list[str] = Field(default_factory=list)
    defaults: dict[str, str] = Field(default_factory=dict)


class DocumentUploadResponse(BaseModel):
    document_id: str
    task_id: str
    filename: str
    file_hash: str
    chunk_count: int
    status: str
    index_name: str | None = None
    embedding_model: EmbeddingModel | None = None
