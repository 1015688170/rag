# 前端

这是 RAG 测试台的 React + Vite + Tailwind 前端。

## 环境变量

从模板生成本地 `.env`：

```bash
cp .env.example .env
```

如果通过 Nginx 反向代理后端：

```env
VITE_API_BASE_URL=/api
```

## 启动

```bash
npm install
npm run dev
```

## 打包

```bash
npm run build
```
