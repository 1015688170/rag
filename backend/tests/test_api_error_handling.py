from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from app.api.routes import chat as chat_route
from app.schemas.chat import ChatRequest


class FailingChatService:
    async def chat(self, request: ChatRequest):
        raise RuntimeError("secret endpoint https://internal.example.invalid")


def test_chat_route_does_not_expose_raw_exception(monkeypatch) -> None:
    monkeypatch.setattr(chat_route, "chat_service", FailingChatService())

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(chat_route.chat(ChatRequest(question="will fail")))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "RAG pipeline failed."
    assert "internal.example" not in exc_info.value.detail
