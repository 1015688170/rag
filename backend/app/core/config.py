from typing import List, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RAG Eval Workbench API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    cors_allow_origins: List[str] = Field(default=["*"])
    source_preview_length: int = Field(default=180, alias="SOURCE_PREVIEW_LENGTH")

    nexus_api_key: str = Field(default="", alias="NEXUS_API_KEY")
    aws_bearer_token_bedrock: str = Field(default="", alias="AWS_BEARER_TOKEN_BEDROCK")

    ada002_api_url: str = Field(default="", alias="ADA002_API_URL")
    google_005_base_url: str = Field(default="", alias="GOOGLE_005_BASE_URL")
    google_embedding_model_name: str = Field(default="text-embedding-005", alias="GOOGLE_MODEL_NAME")

    gpt4o_api_url: str = Field(default="", alias="GPT4O_API_URL")
    claude_endpoint: str = Field(default="", alias="CLAUDE_ENDPOINT")
    claude_model_id: str = Field(default="claude-opus-4.5", alias="CLAUDE_MODEL_ID")

    search_endpoint: str = Field(default="", alias="SEARCH_ENDPOINT")
    search_key: str = Field(default="", alias="SEARCH_KEY")
    index_ada: str = Field(default="", alias="INDEX_ADA")
    index_005: str = Field(default="", alias="INDEX_005")

    reranker_model_path: str = Field(default="", alias="RERANKER_MODEL_PATH")
    reranker_use_fp16: bool = Field(default=True, alias="RERANKER_USE_FP16")

    hf_endpoint: str = Field(default="https://hf-mirror.com", alias="HF_ENDPOINT")
    hf_hub_offline: str = Field(default="1", alias="HF_HUB_OFFLINE")
    transformers_offline: str = Field(default="1", alias="TRANSFORMERS_OFFLINE")

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_allow_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, list):
            return value
        if not value:
            return ["*"]
        if value.startswith("["):
            raw_value = value.strip("[]")
            items = [item.strip().strip("\"'") for item in raw_value.split(",")]
            return [item for item in items if item]
        return [item.strip() for item in value.split(",") if item.strip()]


settings = Settings()
