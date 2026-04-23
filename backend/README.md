# 后端

这是 RAG 测试台的 FastAPI 后端。

## 环境变量

从模板生成本地 `.env`：

```bash
cp .env.example .env
```

`.env` 不能提交到 GitHub，根目录 `.gitignore` 已经忽略该文件。

## 启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```
