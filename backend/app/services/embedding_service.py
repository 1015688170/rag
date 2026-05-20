from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, Optional

import requests

from app.core.config import Settings
from app.schemas.chat import EmbeddingModel

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._ada_session = requests.Session()
        self._google_client: Optional[Any] = None

    def embed(self, text: str, model: EmbeddingModel) -> list[float]:
        started_at = perf_counter()
        try:
            if model == EmbeddingModel.ada_002:
                return self._embed_with_ada(text)
            if model == EmbeddingModel.google_005:
                return self._embed_with_google(text)
            raise ValueError(f"Unsupported embedding model: {model}")
        finally:
            logger.info(
                "rag.embedding elapsed=%.3fs model=%s input_chars=%s",
                perf_counter() - started_at,
                model,
                len(text),
            )

    def _embed_with_ada(self, text: str) -> list[float]:
        headers = {
            "Content-Type": "application/json",
            "api-key": self.settings.nexus_api_key,
        }
        payload = {"input": text, "user": "rag-eval-web"}
        response = self._ada_session.post(
            self.settings.ada002_api_url,
            json=payload,
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    def _embed_with_google(self, text: str) -> list[float]:
        client = self._get_google_client()
        result = client.models.embed_content(
            model=self.settings.google_embedding_model_name,
            contents=text,
        )
        return result.embeddings[0].values

    def _get_google_client(self) -> Any:
        if self._google_client is not None:
            return self._google_client

        from google import genai
        from google.genai.types import HttpOptions

        self._google_client = genai.Client(
            vertexai=True,
            http_options=HttpOptions(base_url=self.settings.google_005_base_url),
            api_key=self.settings.nexus_api_key,
        )
        return self._google_client
