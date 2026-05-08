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
ADMIN_USERNAME=admin
ADMIN_PASSWORD=
SESSION_SECRET=
SESSION_EXPIRE_HOURS=12
SESSION_COOKIE_SECURE=false
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

## Site login protection

The workbench is protected by a simple admin login before any business API can be used. This is a site-level guard only; it does not replace document-level permission fields such as `user_id`, `department`, `roles`, `visibility`, `owner_id`, `allowed_departments`, or `allowed_roles`.

Required backend environment variables:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<set-a-strong-password>
SESSION_SECRET=<set-a-random-secret>
SESSION_EXPIRE_HOURS=12
SESSION_COOKIE_SECURE=false
```

Generate a session secret:

```bash
openssl rand -hex 32
```

Set `SESSION_COOKIE_SECURE=true` when serving the site over HTTPS in production. The backend refuses to start when `ADMIN_PASSWORD` or `SESSION_SECRET` is empty.

Auth APIs:

- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

All other `/api/*` routes require the `rag_session` HttpOnly cookie. `/health`, auth routes, and `OPTIONS` requests are allowed without login.

Auth smoke tests:

```bash
curl -i http://127.0.0.1:8000/api/indexes

curl -i -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"wrong"}'

curl -i -c cookies.txt -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"你的密码"}'

curl -i -b cookies.txt http://127.0.0.1:8000/api/indexes
curl -i -b cookies.txt http://127.0.0.1:8000/api/auth/me

curl -i -b cookies.txt -c cookies.txt -X POST http://127.0.0.1:8000/api/auth/logout
curl -i -b cookies.txt http://127.0.0.1:8000/api/indexes
```

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

### Chunking strategy

Document ingestion uses a two-stage strategy:

1. Parse each file into `DocumentSection` records based on the file type.
2. Split only oversized sections into `DocumentChunk` records.

Defaults:

- `chunk_size=1000` chars.
- `chunk_overlap=150` chars.
- The current version chunks by character count, not tokens.
- Overlap is used only when a section is longer than `chunk_size`.
- Short sections are not forced to overlap.
- Empty chunks are skipped.

File-type parsing:

- Markdown: split sections by headings from `#` through `######`; `section_path` keeps the heading hierarchy joined by `/`.
- TXT: split text into paragraphs, then merge short paragraphs until the section approaches `chunk_size`.
- DOCX: use `python-docx`; Heading styles become section titles, otherwise paragraphs are merged like TXT.
- PDF: use `pypdf`; extract page text, group page paragraphs into sections, and preserve `page_start` / `page_end`. Scanned PDFs require OCR and are not supported in this version.
- JSON: parse with Python `json`; split by JSON path, keeping small fields grouped under parent sections where possible.

This can be upgraded later to tokenizer-based chunking without changing the upload API.

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

The application upload limit is 20MB per file. If the frontend shows HTTP 413 / `Request Entity Too Large`, the request was rejected before ingestion, usually by Nginx or another reverse proxy. Set Nginx above the app limit, for example:

```nginx
client_max_body_size 25m;
```

Document ingestion is synchronous in the current version. Larger files can spend time in parsing, embedding, and Azure AI Search indexing. If the frontend shows HTTP 504 / `Gateway Time-out` but the document list later shows `success`, the gateway timed out while the backend continued processing. Increase proxy timeouts, for example:

```nginx
proxy_connect_timeout 300s;
proxy_send_timeout 300s;
proxy_read_timeout 300s;
```

New backend dependencies are in `backend/requirements.txt`: `SQLAlchemy`, `python-multipart`, `pypdf`, and `python-docx`. Install them before starting the backend:

```bash
cd backend
pip install -r requirements.txt
```

### Ingest APIs

- `POST /api/search-index/create`: create or initialize the Azure AI Search RAG chunk index.
- `POST /api/documents/upload`: upload and synchronously ingest one document.
- `GET /api/documents`: list document metadata by `created_at` descending.
- `GET /api/ingest-tasks/{task_id}`: inspect an ingest task.
- `DELETE /api/documents/{document_id}?index_name=<index>&embedding_model=ada-002`: delete all Azure AI Search chunks for a document and soft-delete the SQLite record.

The existing `/api/chat` and `/api/rerank/status` endpoints remain available.

### Document permission control

This is the first version of document-level permission control, not a full authentication system. The frontend sends `user_id`, `department`, and `roles` only as test-time identity fields; production deployments should inject trusted identity from SSO, JWT validation, or an API gateway.

Permission metadata is stored on `documents` in SQLite and on every Azure AI Search chunk:

- `visibility`: `public`, `private`, `department`, or `role`.
- `owner_id`: user id for owner checks.
- `allowed_departments`: JSON array string in SQLite, string collection in Azure AI Search.
- `allowed_roles`: JSON array string in SQLite, string collection in Azure AI Search.

Chat retrieval uses an Azure AI Search `filter` so permission filtering happens during recall, not after chunks are returned to Python. Requests without identity fields can only retrieve `public` documents. Document listing uses the same visibility rules in SQLite for this first version; document deletion is allowed only for the owner or a caller with the `admin` role.

Existing SQLite databases are migrated at startup after `Base.metadata.create_all(bind=engine)`: missing permission columns are added with `ALTER TABLE`. Alembic is not required for this version.

Existing Azure AI Search indexes that do not include the permission fields should be recreated with the new schema and re-ingested. Azure AI Search does not always allow all schema changes to be safely added in place for old indexes.

### Create search index

The UI provides a `Create index` button next to the Search Index selector. Use it to initialize the selected Azure AI Search index before uploading documents, instead of creating the schema manually in the Azure portal.

API:

```http
POST /api/search-index/create
Content-Type: application/json

{
  "index_name": "swp-embedding-002-k8s-index",
  "embedding_model": "ada-002"
}
```

`index_name` is optional. When omitted, the backend uses the default index for the selected embedding model: `INDEX_ADA` for `ada-002`, `INDEX_005` for `google-005`.

Responses:

- Created: `{"status":"created","message":"index created successfully",...}`
- Already exists: `{"status":"already_exists","message":"index already exists",...}`
- Failed: HTTP 500 with the Azure SDK error in `detail`.

Vector dimensions are read from backend configuration:

```env
ADA002_VECTOR_DIMENSIONS=1536
GOOGLE_005_VECTOR_DIMENSIONS=768
```

If you change embedding providers or models, update these values before creating a new index. The `content_vector` dimension must match the embedding vector returned by `EmbeddingService`.

### Azure AI Search index fields

The create-index endpoint creates these fields, and the upload pipeline writes to the same schema. If an index is created elsewhere, it must contain these fields; otherwise indexing will fail and the document/task status will be set to `failed`.

| Field | Type | Required index behavior |
| --- | --- | --- |
| `id` | `Edm.String` | key |
| `doc_id` | `Edm.String` | filterable |
| `chunk_id` | `Edm.String` | filterable |
| `chunk_index` | `Edm.Int32` | filterable/sortable |
| `filename` | `Edm.String` | searchable/filterable |
| `filepath` | `Edm.String` | searchable/filterable |
| `section_title` | `Edm.String` | searchable/filterable |
| `section_path` | `Edm.String` | searchable/filterable |
| `source_type` | `Edm.String` | filterable |
| `content` | `Edm.String` | searchable |
| `content_vector` | vector collection | searchable vector field, same dimension as the selected embedding model |
| `page_start` | `Edm.Int32` | filterable/sortable |
| `page_end` | `Edm.Int32` | filterable/sortable |
| `created_at` | `Edm.DateTimeOffset` or `Edm.String` | retrievable |
| `file_hash` | `Edm.String` | filterable |
| `visibility` | `Edm.String` | filterable |
| `owner_id` | `Edm.String` | filterable |
| `allowed_departments` | `Collection(Edm.String)` | filterable |
| `allowed_roles` | `Collection(Edm.String)` | filterable |

Deletion uses `doc_id eq '<document_id>'`, so `doc_id` must be filterable. RAG retrieval reads `id`, `filepath`, and `content`; uploaded chunks include those fields and can be retrieved by the existing chat flow after indexing.

### JSON parsing

JSON uploads are parsed with Python's standard `json` module. The parser supports JSON objects and arrays, splits content by JSON path, and stores each path as both `section_title` and `section_path`.

Examples:

```text
$
$.alert.rules[0]
$.services[2].name
$.dashboards[0].panels[3]
```

JSON chunks are written with `source_type=json`. Invalid JSON fails ingestion and records the parsing error in both `documents.error_message` and `ingest_tasks.error_message`.

PDF chunks keep `page_start` and `page_end` so answers can later cite page ranges. If no text can be extracted, ingestion fails with a message indicating that scanned PDFs/OCR are not supported in this version.

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
