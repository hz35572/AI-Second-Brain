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
└─ docker-compose.yml  # Docker 编排（依赖服务 + 前后端 full stack profile）
```

---

## 环境要求

- Node.js 18+（建议 20+）+ npm
- Python 3.11+
- uv
- Docker Desktop（用于一键启动依赖，或前后端 + 依赖整体部署）

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

```shell
copy .env.example .env
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
- 后端（API）：`http://localhost:9000/api/v1`

### 3) 常用 `make` 命令

```powershell
make up       # 启动 Postgres / Redis / Qdrant / MinIO
make down     # 停止 Docker 依赖服务
make logs     # 查看依赖服务日志
make backend-run # 只启动后端服务
make frontend-run # 只启动前端服务
``` 

## Docker 一键部署（前后端 + 依赖）

如果希望前后端也都运行在 Docker 中，可直接使用：

```powershell
make docker-up
```

常用命令：

```powershell
make docker-build  # 构建前后端镜像
make docker-up     # 构建并启动完整栈
make docker-ps     # 查看完整栈状态
make docker-logs   # 查看前后端容器日志
make docker-down   # 停止完整栈
```

启动后访问：

- 前端：`http://localhost:3000`
- 后端：`http://localhost:8000/api/v1`

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
