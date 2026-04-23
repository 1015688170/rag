from __future__ import annotations

import os
from typing import Any, Optional

from app.core.config import Settings


class RerankService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._reranker: Optional[Any] = None

    def rerank(self, query: str, docs: list[dict[str, Any]], top_n: int = 5) -> list[dict[str, Any]]:
        if not docs:
            return []

        try:
            reranker = self._get_reranker()
            pairs = [[query, doc["content"]] for doc in docs]
            scores = reranker.compute_score(pairs)
            if isinstance(scores, float):
                scores = [scores]

            ranked_docs: list[dict[str, Any]] = []
            for index, doc in enumerate(docs):
                score = float(scores[index])
                ranked_docs.append(
                    {
                        **doc,
                        "score": score,
                        "rerank_score": score,
                        "score_source": "rerank",
                        "preview": self._build_preview(doc["content"]),
                    }
                )

            ranked_docs.sort(key=lambda item: item["score"], reverse=True)
            return ranked_docs[:top_n]
        except Exception:
            # If the local reranker stack (FlagEmbedding/transformers/torch) is mis-installed
            # or incompatible, degrade gracefully by skipping rerank.
            fallback: list[dict[str, Any]] = []
            for doc in docs[:top_n]:
                fallback.append(
                    {
                        **doc,
                        "score": self._fallback_score(doc),
                        "rerank_score": None,
                        "score_source": "recall",
                        "preview": self._build_preview(doc.get("content", "")),
                    }
                )
            return fallback

    def _fallback_score(self, doc: dict[str, Any]) -> float:
        recall_score = doc.get("recall_score")
        return float(recall_score) if recall_score is not None else 0.0

    def _get_reranker(self) -> Any:
        if self._reranker is not None:
            return self._reranker

        os.environ["HF_ENDPOINT"] = self.settings.hf_endpoint
        os.environ["HF_HUB_OFFLINE"] = self.settings.hf_hub_offline
        os.environ["TRANSFORMERS_OFFLINE"] = self.settings.transformers_offline

        from FlagEmbedding import FlagReranker

        self._reranker = FlagReranker(
            self.settings.reranker_model_path,
            use_fp16=self.settings.reranker_use_fp16,
        )
        return self._reranker

    def _build_preview(self, content: str) -> str:
        compact = " ".join(content.split())
        return compact[: self.settings.source_preview_length]
