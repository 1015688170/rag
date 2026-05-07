from pydantic import BaseModel, Field

from app.schemas.chat import EmbeddingModel


class IndexListResponse(BaseModel):
    indexes: list[str] = Field(default_factory=list)
    defaults: dict[str, str] = Field(default_factory=dict)


class DocumentUploadResponse(BaseModel):
    index_name: str
    filename: str
    embedding_model: EmbeddingModel
    chunk_count: int
    uploaded_count: int
