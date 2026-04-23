# Linux 服务器部署命令

下面命令按 Ubuntu/Debian 系统编写，默认项目目录为 `/opt/swp-rag-workbench`，模型目录为 `/opt/swp-models`。

## 1. 安装系统依赖

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl git nginx
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
python3 --version
node --version
npm --version
```

## 2. 创建目录

```bash
sudo mkdir -p /opt/swp-rag-workbench/current
sudo mkdir -p /opt/swp-rag-workbench/env
sudo mkdir -p /opt/swp-models
sudo chown -R $USER:$USER /opt/swp-rag-workbench /opt/swp-models
```

## 3. 拉取代码

把 `<你的 GitHub 仓库地址>` 替换成自己的仓库地址。

```bash
git clone <你的 GitHub 仓库地址> /opt/swp-rag-workbench/current
```

如果目录里已经有代码，后续更新用：

```bash
cd /opt/swp-rag-workbench/current
git pull
```

## 4. 创建后端虚拟环境

虚拟环境放在代码目录外，后续同步代码不会影响它。

```bash
python3 -m venv /opt/swp-rag-workbench/venv
source /opt/swp-rag-workbench/venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
pip install -r /opt/swp-rag-workbench/current/backend/requirements.txt
```

`backend/requirements.txt` 已固定 Rerank 兼容版本，避免 `FlagEmbedding` 与 `transformers` 新版本不兼容导致重排失效。

## 5. 下载 Rerank 模型

```bash
source /opt/swp-rag-workbench/venv/bin/activate
pip install -U huggingface_hub
huggingface-cli download BAAI/bge-reranker-v2-m3 --local-dir /opt/swp-models/bge-reranker-v2-m3
ls -la /opt/swp-models/bge-reranker-v2-m3
```

如果服务器不能访问 Hugging Face，可以在其他机器下载后上传整个 `/opt/swp-models/bge-reranker-v2-m3` 目录。

## 6. 创建后端环境变量

```bash
cp /opt/swp-rag-workbench/current/backend/.env.example /opt/swp-rag-workbench/env/backend.env
nano /opt/swp-rag-workbench/env/backend.env
```

至少确认下面几项已经填写：

```env
NEXUS_API_KEY=
AWS_BEARER_TOKEN_BEDROCK=
ADA002_API_URL=
GOOGLE_005_BASE_URL=
GPT4O_API_URL=
CLAUDE_ENDPOINT=
SEARCH_ENDPOINT=
SEARCH_KEY=
RERANKER_MODEL_PATH=/opt/swp-models/bge-reranker-v2-m3
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

## 7. 创建前端环境变量

```bash
cp /opt/swp-rag-workbench/current/frontend/.env.example /opt/swp-rag-workbench/current/frontend/.env
sed -i 's#^VITE_API_BASE_URL=.*#VITE_API_BASE_URL=/api#' /opt/swp-rag-workbench/current/frontend/.env
```

## 8. 手动验证后端

```bash
cd /opt/swp-rag-workbench/current/backend
source /opt/swp-rag-workbench/venv/bin/activate
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

浏览器访问：

```text
http://服务器IP:8000/docs
```

验证成功后按 `Ctrl+C` 停止手动进程。

## 9. 创建 systemd 服务

把 `User=$USER` 中的 `$USER` 替换成实际运行用户，例如 `ubuntu` 或你的登录用户名。

```bash
sudo tee /etc/systemd/system/swp-rag-backend.service > /dev/null <<'EOF'
[Unit]
Description=SWP RAG Workbench FastAPI Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/swp-rag-workbench/current/backend
EnvironmentFile=/opt/swp-rag-workbench/env/backend.env
ExecStart=/opt/swp-rag-workbench/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

如果你的用户名不是 `ubuntu`，执行：

```bash
sudo sed -i "s/^User=.*/User=$USER/" /etc/systemd/system/swp-rag-backend.service
```

启动后端：

```bash
sudo systemctl daemon-reload
sudo systemctl enable swp-rag-backend
sudo systemctl start swp-rag-backend
sudo systemctl status swp-rag-backend
```

查看日志：

```bash
journalctl -u swp-rag-backend -f
```

## 10. 构建前端

```bash
cd /opt/swp-rag-workbench/current/frontend
npm ci || npm install
npm run build
```

## 11. 配置 Nginx

```bash
sudo tee /etc/nginx/sites-available/swp-rag-workbench > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;

    root /opt/swp-rag-workbench/current/frontend/dist;
    index index.html;

    location / {
        try_files $uri /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
EOF
```

启用 Nginx 配置：

```bash
sudo ln -sf /etc/nginx/sites-available/swp-rag-workbench /etc/nginx/sites-enabled/swp-rag-workbench
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

## 12. 开放防火墙

如果启用了 `ufw`：

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw status
```

## 13. 日常更新代码

```bash
cd /opt/swp-rag-workbench/current
git pull
source /opt/swp-rag-workbench/venv/bin/activate
pip install -r backend/requirements.txt
cd frontend
npm ci || npm install
npm run build
sudo systemctl restart swp-rag-backend
sudo systemctl reload nginx
```

## 14. 排查 Rerank

如果前端显示“重排不可用”，先检查后端诊断接口：

```bash
curl http://127.0.0.1:8000/api/rerank/status
```

再查看日志：

```bash
journalctl -u swp-rag-backend -f
```

如果是依赖版本漂移，重新安装固定版本：

```bash
source /opt/swp-rag-workbench/venv/bin/activate
pip uninstall -y FlagEmbedding transformers tokenizers
pip install --no-cache-dir -r /opt/swp-rag-workbench/current/backend/requirements.txt
sudo systemctl restart swp-rag-backend
```
