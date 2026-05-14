# AI Second Brain

基于 RAG（Retrieval-Augmented Generation，检索增强生成）的个人知识库问答系统。你可以上传本地资料（TXT/PDF/Word 等），用自然语言进行对话式检索与问答；系统要求回答内容**严格可溯源**：每个事实句/要点都必须绑定引用，点击引用角标可在右侧抽屉预览原文并定位/高亮。

---

## 核心功能（MVP / V1.0）

- **文件/文件夹管理**：文件夹树 + 文件 CRUD
- **上传与解析**：支持小文件直传与大文件分片上传（含进度）
- **RAG 问答 + SSE 流式输出**：首条 `chunk` 快速返回（TTFB 指标）
- **严格引用溯源（硬约束）**
  - 输出中每个事实句/要点必须带引用标记 `[n]`
  - 点击引用角标可跳转到原文对应位置并高亮（MVP 先保证页码正确 + 高亮近似可见）
- **范围问答（Scope）**：global / folder / file 级别过滤检索范围

---

## 技术栈

**前端**

- Next.js（App Router）+ TypeScript
- Tailwind CSS
- 状态管理：Zustand
- 数据请求：@tanstack/react-query
- 文档渲染：react-markdown / remark-gfm
- PDF 预览：react-pdf

**后端**

- FastAPI（Python 3.11+）
- SSE（流式输出）
- SQLAlchemy（Async）+ Alembic
- PostgreSQL（MVP 元数据统一使用 Postgres）
- Redis（缓存 / 会话 / 进度 / 限流等）
- 文档解析：pypdf、python-docx

**向量检索 / 存储**

- Qdrant（向量库，默认）
- 对象存储：本地文件系统（开发）/ MinIO（部署示例，兼容 S3）

---

## 目录结构

```text
.
├─ backend/    # FastAPI 服务（/api/v1）
├─ frontend/   # Next.js Web UI
├─ docs/       # PRD / TDD / API / Database 等文档（单一事实来源）
├─ infra/      # 部署/基础设施相关（如有）
└─ docker-compose.yml  # Postgres / Redis / Qdrant / MinIO
```

---

## 环境要求

- Node.js 18+（建议 20+）+ npm
- Python 3.11+
- uv
- Docker Desktop（用于一键启动依赖：Postgres/Redis/Qdrant/MinIO）

端口默认占用：

- Frontend：`3000`
- Backend：`8000`
- Postgres：`5433`
- Redis：`6379`
- Qdrant：`6333`（HTTP）、`6334`（gRPC）
- MinIO：`9000`（S3 API）、`9001`（Console）

---

## 安装与启动（本地开发）

### 1) 配置环境变量

根目录复制一份环境变量文件：

```powershell
Copy-Item .env.example .env
```

按需修改 `.env`（后端配置变量统一使用 `AISB_` 前缀）。最小可用配置见：

- `AISB_DATABASE_URL`（Postgres）
- `AISB_REDIS_URL`（Redis）
- `AISB_JWT_SECRET`（JWT 密钥）
- `AISB_STORAGE_DIR`（本地对象存储目录）

### 2) 使用 `make` 一键准备并启动

项目根目录提供了统一的 `Makefile`，推荐直接使用下面的命令完成本地开发启动：

```powershell
make setup
make dev
```

含义说明：

- `make setup`：启动依赖服务，并安装后端/前端依赖，最后执行后端数据库迁移
- `make dev`：同时启动后端 FastAPI 和前端 Next.js 开发服务

打开：

- 前端：`http://localhost:3000`
- 后端（API）：`http://localhost:8000/api/v1`

### 3) 常用 `make` 命令

```powershell
make up       # 启动 Postgres / Redis / Qdrant / MinIO
make down     # 停止 Docker 依赖服务
make logs     # 查看依赖服务日志
make backend-run # 只启动后端服务
make frontend-run # 只启动前端服务
``` 

---

## 使用指南（基础操作）

> API 结构与字段以 `docs/API.md` 为准。

1) **注册 / 登录**

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`

登录成功后使用 `Authorization: Bearer <token>` 调用后续接口。

2) **上传文件**

- 小文件直传：`POST /api/v1/files/upload`（`multipart/form-data`）
- 大文件分片：
  - `POST /api/v1/files/upload/init`
  - `PUT /api/v1/files/upload/{upload_id}/chunks/{chunk_index}`
  - `POST /api/v1/files/upload/{upload_id}/complete`

3) **查看任务进度**

- `GET /api/v1/tasks/{task_id}/progress`

4) **发起对话（SSE 流式）**

后端按 `chunk* -> citation? -> done` 的事件顺序返回（详见 `docs/TECH_DESIGN.md` 与 `docs/API.md`）。

5) **引用溯源与预览**

回答中的引用角标对应 `Citation` 结构（包含 `file_id`、`page`、`locator`、`highlight_positions` 等），前端点击后打开右侧抽屉进行定位/高亮预览。

---

## 常用开发命令

**后端**

```powershell
cd backend
uv sync --extra test
uv run pytest
```

**前端**

```powershell
cd frontend
npm run lint
npm run build
```

---


---

## Roadmap（概览）

- V1.0（MVP）：上传解析 + RAG 问答 + SSE + 引用溯源 + 基础文件/文件夹 CRUD
- V1.5：自动标签/摘要、范围问答 UI、对话历史
- V2.0：多模态、本地化、第三方同步、分享与权限细化

---
