from enum import Enum

from pydantic import BaseModel, Field


class EmbeddingModel(str, Enum):
    ada_002 = "ada-002"
    google_005 = "google-005"


class ChatModel(str, Enum):
    gpt_4o = "gpt-4o"
    claude_opus_45 = "claude-opus-4.5"


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000, description="User input question")
    embedding_model: EmbeddingModel = Field(
        default=EmbeddingModel.ada_002,
        description="Embedding model used for retrieval",
    )
    chat_model: ChatModel = Field(
        default=ChatModel.claude_opus_45,
        description="LLM used for answer generation",
    )
    top_k: int = Field(default=10, ge=1, le=20, description="Recall size before rerank")
    top_n: int = Field(default=5, ge=1, le=10, description="Final size after rerank")
    prompt_template: str | None = Field(
        default=None,
        max_length=12000,
        description="Optional system prompt override used for answer generation",
    )


class SourceItem(BaseModel):
    doc_id: str = Field(..., description="Chunk or document identifier")
    filepath: str = Field(..., description="Original source path")
    score: float = Field(..., description="Primary UI score, rerank score when available")
    rerank_score: float | None = Field(default=None, description="BGE rerank score")
    recall_score: float | None = Field(default=None, description="Azure Search recall score")
    score_source: str = Field(default="rerank", description="Score source shown in UI")
    preview: str = Field(..., description="Short content preview for UI display")
    content: str = Field(..., description="Full chunk content returned by backend")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="LLM final answer")
    model: ChatModel = Field(..., description="Selected chat model")
    embedding_model: EmbeddingModel = Field(..., description="Selected embedding model")
    sources: list[SourceItem] = Field(default_factory=list, description="Retrieved source chunks")
    source_count: int = Field(..., description="Number of final sources returned")
