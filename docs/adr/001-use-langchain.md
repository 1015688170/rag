# ADR 001: Use LangChain as the RAG orchestration layer

## Status

Accepted

## Context

The existing chat flow already has working implementations for Azure AI Search recall, embedding generation, local rerank, and LLM generation. Issue 2 requires introducing LangChain RAG Chain without changing the `/api/chat` request or response contract.

## Decision

Use `langchain-core` only for orchestration primitives and `Document` objects:

- `AzureSearchRetriever` adapts the existing `EmbeddingService` and `SearchService` into LangChain `Document` output.
- `RagChain` composes retrieval, rerank, evidence-threshold filtering, and answer generation with `RunnableLambda`.
- Azure AI Search access, embedding calls, rerank model execution, and LLM calls remain in the existing service classes.
- `ChatService` delegates chat execution to `RagChain` while preserving its constructor dependencies and public `chat()` method.

## Consequences

The API schema stays unchanged, and LangChain remains a thin composition layer. Future RAG steps can be inserted into `RagChain` without replacing the current model or Azure Search integrations.
