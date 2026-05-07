# RAG 测试台

这是一个 FastAPI + React 的 RAG 测试台，用于 Azure AI Search 混合检索、本地 BGE 重排，以及多模型生成测试。

## 目录结构

```text
backend/   FastAPI 后端接口、Pydantic schema、配置和 RAG 服务
frontend/  React + Vite + Tailwind 前端单页应用
```

## 敏感配置

真实环境变量文件只能保留在本地或服务器上，不能提交到 GitHub。

使用模板生成本地配置：

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

后端常用配置项包括：

```env
NEXUS_API_KEY=
AWS_BEARER_TOKEN_BEDROCK=
ADA002_API_URL=
GOOGLE_005_BASE_URL=
GPT4O_API_URL=
CLAUDE_ENDPOINT=
SEARCH_ENDPOINT=
SEARCH_KEY=
RERANKER_MODEL_PATH=/opt/models/bge-reranker-v2-m3
MIN_RERANK_SCORE=0
```

`RERANKER_MODEL_PATH` 必须指向本地模型目录，目录里应包含 `config.json`、tokenizer 文件和模型权重文件。
`MIN_RERANK_SCORE` 是证据门槛，默认 `0`。当重排可用时，低于该值的片段不会进入生成阶段；如果过滤后没有可用片段，系统会拒答，避免低相关资料参与生成。

## 本地启动后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## 本地启动前端

```bash
cd frontend
npm install
npm run dev
```

如果生产环境通过 Nginx 反向代理后端，前端 `.env` 建议配置为：

```env
VITE_API_BASE_URL=/api
```

## Ubuntu 服务器部署

前端打包：

```bash
cd /opt/swp-rag-workbench/current/frontend
npm ci || npm install
npm run build
```

后端建议用 systemd 托管，并读取 `/opt/swp-rag-workbench/env/backend.env`。Nginx 用于托管 `frontend/dist`，并把 `/api/` 反向代理到 `http://127.0.0.1:8000/api/`。

推荐服务器目录：

```text
/opt/swp-rag-workbench/
├─ current/     GitHub 拉取的代码目录
├─ venv/        Python 虚拟环境
└─ env/         服务器私有环境变量文件

/opt/swp-models/
└─ bge-reranker-v2-m3/
```

## GitHub 上传检查

首次上传前：

```bash
git init
git status --short
git add .gitignore README.md backend frontend
git status --short
git commit -m "Initial RAG workbench"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

如果不小心把敏感文件加入暂存区，提交前先移出 Git 索引：

```bash
git rm --cached backend/.env frontend/.env
git rm --cached RAG_Eval_Bench_Hybrid_1.py
```

## Document upload and ingest

The workbench includes a document management view in the React UI. It supports uploading enterprise knowledge files, indexing them into Azure AI Search, and listing or deleting ingested documents.

Supported file types:

- `.md`
- `.txt`
- `.pdf`
- `.docx`
- `.json`

Upload flow:

1. Validate suffix and file size. The maximum single file size is 20MB.
2. Save the original file under `backend/storage/uploads/`.
3. Calculate `sha256` as `file_hash`.
4. If a document with the same `file_hash` has already reached `success`, return `already_exists` and skip Azure AI Search writes.
5. Parse text, split chunks, generate embeddings, write chunks to Azure AI Search, then update SQLite metadata.

SQLite is used for the first version. The database file is:

```text
backend/storage/rag.db
```

Runtime storage paths:

```text
backend/storage/
backend/storage/uploads/
backend/storage/rag.db
```

These runtime files are ignored by Git. For Docker or server deployments, mount `backend/storage` as a persistent volume; otherwise `rag.db` and uploaded source files will be lost when the container or release directory is replaced.

New backend dependencies are in `backend/requirements.txt`: `SQLAlchemy`, `python-multipart`, `pypdf`, and `python-docx`. Install them before starting the backend:

```bash
cd backend
pip install -r requirements.txt
```

### Ingest APIs

- `POST /api/documents/upload`: upload and synchronously ingest one document.
- `GET /api/documents`: list document metadata by `created_at` descending.
- `GET /api/ingest-tasks/{task_id}`: inspect an ingest task.
- `DELETE /api/documents/{document_id}?index_name=<index>&embedding_model=ada-002`: delete all Azure AI Search chunks for a document and soft-delete the SQLite record.

The existing `/api/chat` and `/api/rerank/status` endpoints remain available.

### Azure AI Search index fields

The upload pipeline writes these fields to Azure AI Search. The target index must contain them; otherwise indexing will fail and the document/task status will be set to `failed`.

| Field | Type | Required index behavior |
| --- | --- | --- |
| `id` | `Edm.String` | key |
| `doc_id` | `Edm.String` | filterable |
| `chunk_id` | `Edm.String` | filterable |
| `filename` | `Edm.String` | searchable/filterable |
| `filepath` | `Edm.String` | searchable/filterable |
| `section_title` | `Edm.String` | searchable/filterable |
| `source_type` | `Edm.String` | filterable |
| `content` | `Edm.String` | searchable |
| `content_vector` | vector collection | searchable vector field, same dimension as the selected embedding model |
| `created_at` | `Edm.DateTimeOffset` or `Edm.String` | retrievable |
| `file_hash` | `Edm.String` | filterable |

Deletion uses `doc_id eq '<document_id>'`, so `doc_id` must be filterable. RAG retrieval reads `id`, `filepath`, and `content`; uploaded chunks include those fields and can be retrieved by the existing chat flow after indexing.

### JSON parsing

JSON uploads are parsed with Python's standard `json` module. The parser supports JSON objects and arrays, splits content by top-level keys, array elements, or nested JSON paths, and stores each path as `section_title`.

Examples:

```text
$
$.alert.rules[0]
$.services[2].name
$.dashboards[0].panels[3]
```

JSON chunks are written with `source_type=json`. Invalid JSON fails ingestion and records the parsing error in both `documents.error_message` and `ingest_tasks.error_message`.

### Local test checklist

1. Start the backend and frontend.
2. Open the Documents view.
3. Select the target Azure AI Search index.
4. Upload `.md`, `.txt`, `.pdf`, `.docx`, and `.json` samples.
5. Confirm `backend/storage/rag.db` has records in `documents` and `ingest_tasks`.
6. Confirm Azure AI Search contains chunks with the uploaded `doc_id`.
7. Ask a question in Chat that should retrieve the uploaded content.
8. Upload the same file again and confirm the result is `already_exists`.
9. Delete the document and confirm the chat flow no longer retrieves that `doc_id`.
