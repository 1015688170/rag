# RAG 平台审查报告（两轮）

**项目**: https://github.com/1015688170/rag  
**分支**: `main`  
**第一轮审查**: 2026-05-13 — 基线审查（commit `39d75b4`）  
**第二轮审查**: 2026-05-13 — Codex 修改验证（commit `b422dbc`）  
**审查范围**: 全仓代码，按公司级 RAG 平台架构标准审查  

---

## 1. 当前架构总结

### 1.1 技术栈

| 层 | 技术选型 |
|---|---|
| Web 框架 | FastAPI + Uvicorn |
| 配置管理 | pydantic-settings |
| 数据库 | SQLite + SQLAlchemy ORM |
| 向量存储 | Azure AI Search（HNSW 索引） |
| Embedding | ada-002（via REST）+ google/text-embedding-005（via Vertex AI SDK） |
| Rerank | FlagEmbedding BGE Reranker（本地模型） |
| LLM | GPT-4o（via REST）+ Claude Opus 4.5（via Bedrock SDK） |
| 编排 | langchain-core（RunnableLambda + Document） |
| 前端 | React 18 + Vite + Tailwind CSS |
| 认证 | HMAC-SHA256 session cookie（单用户 admin） |

### 1.2 目录结构评价

```
backend/app/
  api/routes/          # FastAPI 路由层
  core/                # 配置、数据库、认证、权限
  models/              # SQLAlchemy ORM 模型
  rag/                 # LangChain 编排层（chains + retrievers）
  schemas/             # Pydantic 请求/响应模型
  services/            # 业务服务层（实际执行者）
tests/                 # 单元测试
```

**评价：清晰，职责分离合理。** `rag/` 只放编排逻辑，`services/` 放执行逻辑——这个边界是正确的。

### 1.3 RAG 流程（端到端）

```
POST /api/chat (ChatRequest)
  │
  ▼
ChatService.chat()
  │
  ▼
RagChain.invoke()
  ├─ _retrieve_step:
  │   AzureSearchRetriever.retrieve()
  │     ├─ EmbeddingService.embed(text, model)       → list[float]
  │     ├─ SearchService.search(..., permission_filter) → list[dict]
  │     └─ _to_document(row)                          → list[Document]
  │
  ├─ _rerank_step:
  │   RerankService.rerank(query, docs, top_n)
  │     ├─ FlagReranker.compute_score(pairs)          → list[dict] (with rerank_score)
  │     └─ fallback → recall_score as score
  │
  └─ _answer_step:
      ├─ _filter_docs_by_rerank_score(threshold)
      │   ├─ all below threshold → LOW_RELEVANCE_ANSWER_TEMPLATE
      │   └─ empty              → NO_RETRIEVAL_ANSWER
      └─ LLMService.generate(question, chunks, model) → str answer
```

### 1.4 Service 职责边界

| 服务 | 职责 | 边界清晰度 |
|---|---|---|
| `ChatService` | 门面，组装 RagChain，暴露 `async chat()` | 很好 |
| `SearchService` | Azure AI Search 的 CRUD + 全文/向量搜索 + OData 权限过滤 | 很好 |
| `EmbeddingService` | 两个 embedding 后端的统一 `embed()` 接口 | 很好 |
| `RerankService` | BGE reranker 懒加载 + 优雅降级 + 健康检查 | 很好 |
| `LLMService` | GPT-4o / Claude 两个后端的统一 `generate()` 接口 | 可改进 |
| `DocumentIngestService` | 文档上传→解析→分块→向量化→索引，含状态机 | 很好 |

---

## 2. 逐项审查结果（对应 Issue 2 审查重点）

### 2.1 `/api/chat` 兼容性 — 通过

`ChatRequest` 和 `ChatResponse` 的 Pydantic schema 未变。前端 `sendChatMessage()` 调用的 endpoint、payload、响应结构不变。LangChain 的引入对 API 合约完全透明。

### 2.2 LangChain 是否过度侵入业务代码 — 适度，但有问题

**好的方面：**
- 只用了 `langchain-core`（`requirements.txt` 第 7 行），未引入 `langchain` 全家桶
- `AzureSearchRetriever` 只是一个薄适配器，将 `dict` → `Document`
- `RagChain` 是独立类，不侵入 `SearchService` / `EmbeddingService` / `LLMService`
- ADR 001 记录了这个决策，架构意图明确

**问题：**
- 3 个 `RunnableLambda` 串联本质上就是函数组合。对于 `A → B → C` 这种线性流程，RunnableLambda 没有带来比直接函数调用更多的价值，反而增加了调试成本（Lambda 调用栈在 traceback 中不可读）
- `RagChain` 的 `_retrieve_step`、`_rerank_step`、`_answer_step` 通过 dict `state` 传递数据，类型安全完全丢失——任何 key 拼写错误都是运行时错误
- 但**不构成严重问题**——当前只是为了后续引入 LangGraph 做的准备

### 2.3 Retriever 是否返回 `langchain_core.documents.Document` — 通过

`azure_search_retriever.py:48-51`：
```python
def _to_document(self, row: dict[str, Any]) -> Document:
    content = str(row.get("content", ""))
    metadata = {key: value for key, value in row.items() if key != "content"}
    return Document(page_content=content, metadata=metadata)
```

单元测试 `test_rag_chain.py:67-94` 验证了类型和内容正确性。`content` 与 `metadata` 分离正确。

**注意**：`content` 字段在 `SearchService.search()` 中只 select 了 `["id", "filepath", "content"]`（`search_service.py:261`），这意味着 metadata 中只有 `doc_id` 和 `filepath`，缺失了 `section_title`、`source_type`、`page_start` 等字段。如果需要丰富的 source attribution，需要扩展 `select` 列表。

### 2.4 权限过滤是否仍在 Azure AI Search 查询阶段 — 通过

`search_service.py:259`：
```python
filter=self._permission_filter(user_id=user_id, department=department, roles=roles),
```

权限过滤逻辑 `_permission_filter()`（行 277-306）构建 OData 表达式：
```
visibility eq 'public' or owner_id eq 'alice' or allowed_departments/any(d: d eq 'sre') or allowed_roles/any(r: search.in(r, 'admin,oncall'))
```

- 过滤发生在数据库层面（Azure AI Search），不是应用层
- OData 字符串做了 escape（`_escape_odata_string`）
- 索引 schema 中 `visibility`、`owner_id`、`allowed_departments`、`allowed_roles` 均设为 `filterable=True`

**注意**：`allowed_roles` 使用 `search.in()` 而非逐条 `eq`，正确避免了 OData `any` + `or` 嵌套的性能问题。

### 2.5 Rerank 阈值拒答逻辑 — 通过

`rag_chain.py:18-24` 定义了两个拒答模板：
- `NO_RETRIEVAL_ANSWER`：检索结果为空
- `LOW_RELEVANCE_ANSWER_TEMPLATE`：所有文档 rerank 分低于 `min_rerank_score`

`_filter_docs_by_rerank_score()`（行 155-163）在存在有效 rerank_score 时才做阈值过滤，否则保留全部（向后兼容 rerank 不可用的场景）。

`_answer_step`（行 87-131）的分支逻辑正确：
1. 无文档 → 拒答
2. 有文档但全部低于阈值 → 拒答（返回被拒文档的 sources）
3. 有文档且至少一个高于阈值 → 生成回答

单元测试覆盖了分支 1 和 2。

### 2.6 异常处理是否会泄露密钥或底层错误 — 需要修复

**问题点（多处泄露底层错误信息到客户端）：**

| 位置 | 问题 |
|---|---|
| `chat.py:38` | `f"RAG pipeline failed: {exc}"` — 裸异常信息返回客户端 |
| `documents.py:64` | `f"Document upload failed: {exc}"` |
| `documents.py:148` | `f"Document permission update failed: {exc}"` |
| `search_index.py:20` | `f"Search index creation failed: {exc}"` |
| `documents.py:197` | `f"Document deletion failed: {exc}"` |

这些异常消息可能包含：
- Azure Search endpoint URL（`SearchService.search()` 中 `client.search()` 的异常可能携带连接信息）
- 内部文件路径（`DocumentIngestService` 异常可能包含服务器文件路径）
- Azure KeyCredential 相关的连接错误信息

**处理较好的地方：**
- `RerankService.rerank()`（`rerank_service.py:52-68`）捕获异常后只记录日志，不回传客户端，并优雅降级
- `auth.py` 使用 `secrets.compare_digest` 防止时序攻击

**修复建议：** 所有 API route 的 `except Exception` 应该只返回通用错误消息，将详细异常记录到服务端日志。

### 2.7 单元测试覆盖 — 不足

当前 `tests/test_rag_chain.py` 只有 3 个测试：

| 测试 | 覆盖路径 |
|---|---|
| `test_azure_search_retriever_returns_documents` | Retriever → Document 转换 |
| `test_rag_chain_refuses_when_retrieval_is_empty` | 空检索 → 拒答 |
| `test_rag_chain_filters_by_rerank_threshold_and_refuses_generation` | 低分 rerank → 拒答 |

**缺失的关键测试：**
- LLM 成功生成回答的 golden path
- Rerank 降级（fallback to recall）路径
- 多文档、多来源的 rerank 排序
- 权限过滤器 OData 表达式正确性（独立测试 `_permission_filter`）
- `ChatRequest` schema 校验
- `ChatService` 的 async 路径
- DocumentIngestService 的各文件类型解析

### 2.8 是否适合后续扩展 LangGraph、评估、观测 — 需要调整

**有利因素：**
- Service 边界清晰，替换编排层不影响执行层
- `RagChain` 已经用 LangChain Runnable 原语，过渡到 LangGraph 的 `StateGraph` 是自然的
- `ChatService` 是单一门面，方便插入 tracing middleware

**不利因素：**
- `RagChain` 的 `state: dict[str, Any]` 在成为 LangGraph `TypedDict` state 后需要大量重构签名
- 没有结构化日志/span（当前只有 `logging.exception`），引入观测需要从头搭建
- 缺少 evaluation 基础设施（无 golden dataset、无 metric 计算）

---

## 3. 主要问题（优先级排序）

### P0 — 安全

1. **异常消息泄露**：5 处 API route 的 `except Exception` 将底层异常原文返回给客户端。需要全部改为通用错误消息 + 服务端日志。

### P1 — 架构

2. **RagChain 的 state dict 无类型安全**：`state: dict[str, Any]` 在整个 chain 中传递，key 拼写错误是运行时才发现。建议引入 TypedDict 或 dataclass 作为 state schema。

3. **SearchService.search() select 字段不完整**：只返回 `id, filepath, content`，丢失了 `section_title, source_type, page_start, page_end` 等元数据，影响 answer 中的来源标注质量。

4. **LLMService 的 SYSTEM_PROMPT 硬编码在后端**：前端也维护了一份完全相同的 `DEFAULT_PROMPT_TEMPLATE`（`App.tsx:20-51`）。两端不同步时会让人困惑——实际以后端为准。

### P2 — 工程化

5. **单用户 admin 模型**：认证系统只支持一个 admin 用户。公司级需要多用户 + RBAC。
6. **无 rate limiting**：`/api/chat` 没有频率限制，LLM API 调用成本无保护。
7. **SQLite 不适合公司级**：虽然当前用于文档元数据管理（不是向量存储），但并发写入能力有限。
8. **`_is_index_exists_error` 异常匹配脆弱**：通过检查异常字符串判断"索引已存在"，依赖 Azure SDK 的错误消息格式不变化。

---

## 4. 第一轮改造建议（Issue 2：引入 LangChain RAG Chain）

### 4.1 当前状态：已经完成

Issue 2 的目标——"引入 LangChain RAG Chain，保持 `/api/chat` 兼容"——**已经在 main 分支上实现了**。ADR 001 记录了设计决策。

当前实现可以接受，但需要以下微调：

### 4.2 建议调整（不改动行为，只提升质量）

**a) RagChain state 使用 TypedDict：**

```python
# rag/chains/rag_chain.py
from typing import TypedDict

class RagState(TypedDict):
    request: ChatRequest
    index_name: str
    documents: list[Document]
    raw_docs: list[dict[str, Any]]
    reranked_docs: list[dict[str, Any]]
```

替代当前的 `dict[str, Any]`，提升类型安全。

**b) 修复异常消息泄露（安全修复，应优先于任何功能开发）：**

将所有 API route 的 `except Exception as exc: raise HTTPException(detail=f"...{exc}")` 改为：
```python
except Exception:
    logger.exception("RAG pipeline failed")
    raise HTTPException(status_code=500, detail="Internal server error")
```

**c) 扩展 SearchService.search() 的 select 字段：**

将 `select=["id", "filepath", "content"]` 扩展为包含 `section_title, source_type` 等字段，以便 `AzureSearchRetriever._to_document()` 的 metadata 更丰富。

### 4.3 不需要做的事

- **不要**把 `SearchService.search()` 改成 LangChain 的 `BaseRetriever` 子类——它会侵入 Azure Search 的数据访问层
- **不要**引入 `langchain` 包（区别于 `langchain-core`）——全家桶会引入不必要的 PromptTemplate、Chain、Memory 等抽象
- **不要**把 `EmbeddingService` 包装成 LangChain `Embeddings` 基类——没必要，当前接口足够清晰
- **不要**改动 API schema（`ChatRequest` / `ChatResponse`）——这是本次改造的核心约束

---

## 5. 不建议改动的模块（第一轮重构禁区）

| 模块 | 理由 |
|---|---|
| `SearchService` | Azure AI Search 是基础设施，不是编排逻辑。其 OData 权限过滤、索引管理、批量写入在当前形态下已经正确且高效。引入 LangChain 的 `VectorStore` 抽象会破坏权限过滤这一关键逻辑 |
| `EmbeddingService` | 两个后端的适配已简洁，`embed()` 返回 `list[float]` 足够。包装成 LangChain `Embeddings` 基类只会加 indirection |
| `DocumentIngestService` | 文档解析/分块逻辑与 RAG 运行时是正交关注点。当前实现自成体系，状态机完整 |
| `auth.py` + `permissions.py` | 与 RAG 编排无关，属于基础设施层 |
| 前端 `ChatMessage` / `ChatResponse` 类型 | 已与后端 Pydantic schema 对齐，改动会破坏前后端契约 |

---

## 6. 后续 Issue 拆分建议

建议按以下顺序推进：

### Issue 3: 安全加固 + 异常处理规范化
- 修复 5 处异常消息泄露
- 添加结构化日志（`structlog` 或 `logging` + JSON formatter）
- 添加 rate limiting middleware
- **优先级**: 最高，应该在功能扩展前完成

### Issue 4: RagChain state 类型化 + 单元测试补齐
- RagState TypedDict
- 补齐核心路径测试（golden path、rerank 降级、权限过滤、多文档）
- 添加 `SearchService._permission_filter()` 的独立单元测试

### Issue 5: 引入 LangGraph StateGraph
- 将 `RunnableLambda` 三步链替换为 `StateGraph`
- 每个 step 成为独立 Node
- 添加条件边（rerank 失败 → fallback path / 无文档 → early exit）
- 保持 `/api/chat` 兼容不变

### Issue 6: 观测与评估基础设施
- 引入 LangSmith / LangFuse tracing
- 搭建 golden dataset + RAGAS 评估 pipeline
- 添加 latency 分步度量（embedding / search / rerank / generation）

### Issue 7: 认证与多租户
- 多用户支持（替换单 admin 模型）
- JWT token 替代 HMAC session cookie
- 用户与角色的 CRUD

### Issue 8: 生产化部署
- PostgreSQL 替代 SQLite
- Redis 缓存 embedding
- 异步 embedding / 并行 rerank
- Prometheus metrics + Grafana dashboard

---

## 7. 总结

**当前代码质量：中等偏上。** 核心 RAG 流程正确，服务边界清晰，LangChain 引入克制。主要风险点集中在安全（异常消息泄露）和测试覆盖不足。

**Issue 2（引入 LangChain RAG Chain）已经在 main 分支完成**，实现质量可接受，但需要：
1. 立即修复异常消息泄露（P0 安全）
2. RagChain state 从 `dict` 升级为 TypedDict（P1 架构）
3. 补齐测试覆盖（P2 工程化）

后续引入 LangGraph、评估、观测的架构基础已经打好，不需要对现有 service 层做任何破坏性修改。

---

---

# 第二轮审查：Codex 修改验证

**对比基线**: `39d75b4`（基线报告提交）→ `b422dbc`（Codex 修改）  
**变更范围**: 9 个文件，+187 / -19 行  

```
backend/app/api/routes/chat.py           |  8 +++--
backend/app/api/routes/documents.py      | 12 +++++--
backend/app/api/routes/search_index.py   |  8 ++++-
backend/app/rag/chains/rag_chain.py      | 16 ++++++---
backend/app/services/search_service.py   | 45 ++++++++++++++++++-----
backend/tests/conftest.py                |  4 +++
backend/tests/test_api_error_handling.py | 24 +++++++++++++ (new)
backend/tests/test_rag_chain.py          | 61 ++++++++++++++++++++++++++++++++
backend/tests/test_search_service.py     | 28 +++++++++++++++ (new)
```

---

## 逐项审查结果

### 1. `/api/chat` 兼容性 — ✅ 保持兼容

`ChatRequest` / `ChatResponse` schema 未变。`rag_chain.py` 中新增的 `RagState` TypedDict 是内部实现细节，不影响 API 合约。

### 2. LangChain 编排层 — ✅ 改善，引入 RagState TypedDict

`rag_chain.py:18-23` 新增：
```python
class RagState(TypedDict, total=False):
    request: ChatRequest
    index_name: str
    documents: list[Document]
    raw_docs: list[dict[str, Any]]
    reranked_docs: list[dict[str, Any]]
```

三步方法的签名从 `dict[str, Any]` → `RagState`。`total=False` 合理——state 是逐步构造的。

**小问题**：`_retrieve_step` 返回 `{**state, "index_name": ..., "documents": ...}` 时 mypy/pyright 会报 "RagState 不支持 `**` 展开"。运行时没问题，但静态类型检查器会警告。后续可改为显式构造每个 key。

### 3. Retriever 返回 `Document` — ✅ 未改动，基线已通过

### 4. 权限过滤在 Azure AI Search 查询阶段 — ✅ 不变，增强测试

`_permission_filter()` 逻辑未改，新增了独立单元测试 `test_search_service.py`：

| 测试 | 覆盖 |
|---|---|
| `test_permission_filter_defaults_to_public_only` | 无身份时仅 public |
| `test_permission_filter_escapes_and_deduplicates_identity_fields` | SQL 注入防护 + 去重 |

第二个测试包含 `alice'o` → `alice''o`、`on'call` → `on''call` 的 OData escape 验证，以及 `["admin", "admin", ...]` 的去重验证。测试质量好。

### 5. Rerank 阈值拒答 — ✅ 未改动，基线已通过

### 6. 异常处理 — ✅ P0 已修复

5 处异常泄露全部修复：

| 文件 | 修改 |
|---|---|
| `chat.py:35-39` | `f"RAG pipeline failed: {exc}"` → `"RAG pipeline failed."` + `logger.exception()` |
| `documents.py:61-65` | `f"Document upload failed: {exc}"` → `"Document upload failed."` + `logger.exception()` |
| `documents.py:147-151` | `f"Document permission update failed: {exc}"` → `"Document permission update failed."` + `logger.exception()` |
| `documents.py:196-200` | `f"Document deletion failed: {exc}"` → `"Document deletion failed."` + `logger.exception()` |
| `search_index.py:17-21` | `f"Search index creation failed: {exc}"` → `"Search index creation failed."` + `logger.exception()` |

额外改进：
- `search_index.py` 新增了 `ValueError` 单独 catch 返回 400（区分参数校验错误和服务器错误）
- `list_indexes` 的 `except Exception` 也加了 `logger.exception("Failed to list Azure AI Search indexes")`
- 新增 `test_api_error_handling.py` 验证异常不泄露："secret endpoint https://internal.example.invalid" 被拦截在通用错误消息之后

### 7. 单元测试 — ✅ 显著改善，从 3 个增至 8 个

| 测试（新增标记*） | 覆盖路径 |
|---|---|
| `test_azure_search_retriever_returns_documents` | Retriever → Document |
| `test_rag_chain_refuses_when_retrieval_is_empty` | 空检索拒答 |
| `test_rag_chain_filters_by_rerank_threshold_and_refuses_generation` | 低分拒答 |
| `test_rag_chain_generates_answer_with_high_rerank_score` * | Golden path：检索→rerank→生成 |
| `test_rag_chain_falls_back_to_recall_when_rerank_raises` * | Rerank 异常 → recall 降级 |
| `test_chat_route_does_not_expose_raw_exception` * | API 异常不泄露 |
| `test_permission_filter_defaults_to_public_only` * | 权限过滤默认值 |
| `test_permission_filter_escapes_and_deduplicates_identity_fields` * | OData 转义 + 去重 |

**Golden path 测试**（`test_rag_chain.py:155-177`）：确认了完整链路 `search → rerank → generate`、`llm_service.calls == 1`、source 包含 `section_title` 和 `source_type`。

**Rerank 降级测试**（`test_rag_chain.py:180-213`）：通过 `FailingRerankService` 模拟 rerank 异常，验证降级到 recall score、`rerank_score is None`、`score_source == "recall"`。

### 8. SearchService select 字段扩展 — ✅ 改善，有一个命名问题

`search_service.py:260-273` select 从 3 个字段扩展到 12 个：
```
id, doc_id, chunk_id, chunk_index, filename, filepath,
section_title, section_path, source_type, content, page_start, page_end
```

metadata 填充逻辑（行 286-300）使用映射：
```python
row_field_name = "doc_id" if field_name == "source_doc_id" else field_name
```

**⚠️ 命名混淆**：返回 dict 中 `doc_id` 来自 `row["id"]`（chunk 主键），而 `source_doc_id` 来自 `row["doc_id"]`（父文档 ID）。`doc_id` 这个名称暗示它是文档 ID，但实际存储的是 chunk ID。这是原始代码遗留问题，Codex 未修正，但不影响正确性。

---

## 第二轮发现的问题

### ⚠️ P1 — 测试依赖缺失

`test_api_error_handling.py:15` 使用 `@pytest.mark.anyio`，但 `requirements.txt` 中**没有 `anyio` 或 `pytest-asyncio` 包**。

pytest 会报 `Unknown marker: anyio` 警告，且 async 测试函数无法正确执行。需要在 `requirements.txt` 中添加：
```
pytest-asyncio
```

或者改用同步测试（不需要 `await`，直接用 `asyncio.run()`）：

```python
import asyncio

def test_chat_route_does_not_expose_raw_exception(monkeypatch) -> None:
    monkeypatch.setattr(chat_route, "chat_service", FailingChatService())
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(chat_route.chat(ChatRequest(question="will fail")))
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "RAG pipeline failed."
```

### 🟡 P2 — RagState 的 `**state` 展开与 TypedDict 不兼容

`rag_chain.py:72-76` 等处使用 `{**state, "index_name": index_name, ...}` 返回。TypedDict 不支持 `**` 解包的类型推断，mypy/pyright 会报错。后续可改为显式构造：

```python
return {
    "request": state["request"],
    "index_name": index_name,
    "documents": documents,
}
```

### 🟡 P2 — `_document_to_source_doc` 正确传递了新增字段

`rag_chain.py:141-144` 的 `_document_to_source_doc` 方法通过 `**document.metadata` 展开会正确传递 `SearchService.search()` 的新字段（`section_title`、`source_type` 等），因为它们在 `AzureSearchRetriever._to_document()` 中被放入了 `Document.metadata`。但 `RerankService.rerank()` 只使用 `doc["content"]` 进行 rerank，不会用到新字段——行为正确。

### 🟢 P3 — `conftest.py` 的 env var 时机

`conftest.py:8-9` 在 `sys.path` 修正之后才设置环境变量。如果 Settings 在 import chain 中被提前实例化（如 `from app.core.config import settings` 触发模块级实例化），则 env var 设置太晚。当前测试中通过 fake services 避免了 Settings 实例化，所以没问题，但如果后续测试直接 `from app.core.config import settings` 就会在 import 时触发 pydantic-settings 校验失败。

---

## 两轮对比总结

| 审查项 | 第一轮（基线） | 第二轮（Codex 修改） |
|---|---|---|
| `/api/chat` 兼容 | ✅ | ✅ 不变 |
| LangChain 侵入度 | ✅ 适度 | ✅ 新增 RagState TypedDict |
| Document 返回 | ✅ | ✅ 不变 |
| 权限过滤位置 | ✅ | ✅ 新增独立测试 |
| Rerank 拒答 | ✅ | ✅ 不变 |
| 异常泄露 | ❌ P0（5 处） | ✅ **已修复** |
| 单元测试 | ⚠️ 3 个 | ✅ 8 个（+golden path, +降级, +权限, +异常拦截） |
| Search select 字段 | ⚠️ 3 字段 | ✅ 12 字段（+section_title, +source_type 等） |
| State 类型安全 | ❌ `dict[str, Any]` | ✅ `RagState(TypedDict)` |
| 测试依赖 | — | ⚠️ 缺 `pytest-asyncio` |

## 最终结论

**Codex 修改质量：好。** 精准命中了基线报告中的 P0（异常泄露）和主要 P1（TypedDict、select 字段、测试覆盖）问题。无新增 bug，无过度重构，无破坏性变更。

**剩余待处理（非阻塞）：**
1. `requirements.txt` 添加 `pytest-asyncio` 或改用 `asyncio.run()`（P1）
2. RagState 的 `**state` 展开改为显式构造（P2，类型检查器兼容）
3. `search_service.py` 返回 dict 中 `doc_id` vs `source_doc_id` 命名澄清（P2，不影响正确性）

第二轮修改已达到可合并标准。
