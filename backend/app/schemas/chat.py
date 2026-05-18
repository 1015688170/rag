from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class EmbeddingModel(str, Enum):
    ada_002 = "ada-002"
    google_005 = "google-005"


class ChatModel(str, Enum):
    gpt_4o = "gpt-4o"
    claude_opus_45 = "claude-opus-4.5"


class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"] = Field(..., description="Conversation message role")
    content: str = Field(..., min_length=1, max_length=4000, description="Conversation message content")


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000, description="User input question")
    history: list[ChatHistoryItem] = Field(
        default_factory=list,
        max_length=10,
        description="Recent conversation messages used only for follow-up question context",
    )
    user_id: str | None = Field(default=None, description="Current user id for document permission filtering")
    department: str | None = Field(default=None, description="Current user department for document permission filtering")
    roles: list[str] = Field(default_factory=list, description="Current user roles for document permission filtering")
    index_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Optional Azure AI Search index selected by the user",
    )
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
    source_doc_id: str | None = Field(default=None, description="Parent knowledge document identifier")
    chunk_id: str | None = Field(default=None, description="Original chunk identifier")
    chunk_index: int | None = Field(default=None, description="Chunk order in the source document")
    filename: str | None = Field(default=None, description="Original source filename")
    filepath: str = Field(..., description="Original source path")
    section_title: str | None = Field(default=None, description="Source section title")
    section_path: str | None = Field(default=None, description="Source section path")
    source_type: str | None = Field(default=None, description="Source document type")
    page_start: int | None = Field(default=None, description="First source page for paged documents")
    page_end: int | None = Field(default=None, description="Last source page for paged documents")
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
    index_name: str = Field(..., description="Azure AI Search index used for retrieval")
    sources: list[SourceItem] = Field(default_factory=list, description="Retrieved source chunks")
    source_count: int = Field(..., description="Number of final sources returned")
