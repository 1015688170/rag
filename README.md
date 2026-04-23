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
```

`RERANKER_MODEL_PATH` 必须指向本地模型目录，目录里应包含 `config.json`、tokenizer 文件和模型权重文件。

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
