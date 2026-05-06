# AI Second Brain 技术设计文档（TDD）
**文档版本**：V1.1  
**最后更新**：2026-05-02  
**关联文档**：`docs/PRD.md`、`docs/API.md`、`docs/database.md`

## 1. 项目目标与范围

AI Second Brain 是一个基于 RAG 的个人知识库问答系统。MVP 聚焦于：
- TXT/PDF/Word 上传、解析、分块与建库
- Chat-first 三栏体验：左侧导航、中间对话、右侧引用预览抽屉
- SSE 流式问答，首条 `chunk` TTFB < 2s
- 严格引用溯源：每个事实句/要点必须包含引用标记，引用可点击并定位到原文
- 文件、文件夹、任务进度、对话基础管理

MVP 元数据存储统一使用 PostgreSQL，不接受临时改回 SQLite 的实现。

## 2. 技术栈与关键决策

- Backend：FastAPI、SQLAlchemy 2.x async、Alembic、Pydantic Settings
- Metadata DB：PostgreSQL 16
- Cache / progress / future queue：Redis
- Vector DB：Qdrant
- Storage：本地文件系统（开发默认），后续兼容 MinIO/S3
- Frontend：Next.js App Router、TypeScript、Tailwind CSS、Zustand
- Streaming：SSE，事件顺序为 `chunk* -> citation? -> done`

## 3. 后端目录结构

```text
backend/
  app/
    main.py                 # FastAPI app factory, lifespan, CORS, v1 router
    agents/                 # Agent implementation
    api/
      routers/              # auth/files/folders/chat/tasks routes
        v1/                 # v1 version router
      deps.py               # shared dependencies: auth, db session
      router.py             # versioned router aggregator
    core/
      config.py             # Settings, AISB_ env prefix, compatibility aliases
      database.py           # compatibility exports; new code imports app.db.session
      security.py           # password hashing and JWT helpers
    db/
      base.py               # SQLAlchemy DeclarativeBase + naming convention
      session.py            # async engine/session/context managers
      models/               # SQLAlchemy ORM models
    schemas/                # Pydantic request/response schemas
    repositories/           # database access layer
    services/               # business orchestration
    tasks/                  # background task helpers
  alembic/
    env.py
    versions/
  tests/
  pyproject.toml
```

分层规则：

- `api/routers/v1` 只负责协议适配、依赖注入、参数校验和序列化
- 数据库访问放在 `repositories`
- 业务编排放在 `services`
- 新的数据库代码必须从 `app.db.session` 导入 session；`app.core.database` 仅作为旧模块的临时兼容层
- 新的 SQLAlchemy 模型必须继承自 `app.db.base.Base`

## 4. 配置策略

后端配置位于 `app/core/config.py`。

- 环境变量统一使用 `AISB_` 前缀，避免与全局环境变量冲突
- `.env` 会从当前目录或其父目录加载
- 新代码应使用大写配置字段，例如 `settings.DATABASE_URL` 和 `settings.STORAGE_DIR`
- 小写别名，例如 `settings.database_url` 和 `settings.storage_dir`，仅保留用于迁移兼容
- PostgreSQL 可通过 `AISB_DATABASE_URL` 配置，也可通过 `AISB_POSTGRES_HOST`、`AISB_POSTGRES_PORT`、`AISB_POSTGRES_USER`、`AISB_POSTGRES_PASSWORD`、`AISB_POSTGRES_DB` 配置
- Alembic 使用 `settings.DATABASE_URL_SYNC`；应用运行时使用 `settings.DATABASE_URL`

最小本地配置：

```env
AISB_DATABASE_URL=postgresql+asyncpg://aisb:aisb@localhost:5432/aisb
AISB_DATABASE_URL_SYNC=postgresql+psycopg://aisb:aisb@localhost:5432/aisb
AISB_SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
AISB_REDIS_URL=redis://localhost:6379/0
AISB_STORAGE_DIR=.data/storage
AISB_UPLOAD_TMP_DIR=.data/uploads
```

## 5. 数据模型

数据库表结构以 `docs/database.md` 为准，Alembic 初始迁移为 `backend/alembic/versions/0001_init.py`。

关键要求：

- `files.sha256` 用于去重和上传完整性校验
- `file_chunks.page_number`、`start_pos`、`end_pos` 和 `locator` 用于引用预览与高亮
- `conversations.scope_type` 和 `scope_ids` 用于支持 global/folder/file 范围问答
- 文件删除必须级联清理数据库中的 chunks/tags/tasks，同时清除向量库记录和存储的原文件

## 6. RAG 流水线

导入流程：

1. 上传单文件或 multipart 分片
2. 校验大小/哈希并持久化原始文件
3. 在 PostgreSQL 中创建文件/任务元数据
4. 解析 TXT/PDF/Word
5. 在保留 locator 字段的前提下清洗并分块文本
6. 持久化 chunks 和后续向量负载
7. 将文件标记为 `ready`，任务标记为 `completed`

问答流程：

1. 解析用户范围：`global`、`folder` 或 `file`
2. 按用户和范围过滤，从向量库检索 top-k chunks
3. 用编号上下文块构建 prompt
4. 通过 SSE 流式输出 LLM 结果
5. 按句校验引用
6. 如果引用校验失败，重试一次引用修复；如果仍然无效，则返回有依据的降级回答，而不是输出未经支持的结论

## 7. API 与 SSE 协议

`docs/API.md` 是接口与载荷的单一事实来源。  
`docs/backend/add-api-endpoint.md` 说明了如何新增 API endpoint。

SSE 事件顺序：

```text
chunk* -> citation? -> done
```

每个 `citation` 载荷都必须包含足够的 locator 数据，以便前端右侧抽屉能够打开原始文件，并高亮近似的来源位置。

## 8. 性能与验收口径

- Chat TTFB：从请求接收到首个 SSE `chunk` 发出，目标 < 2s
- 10MB 建库时间：从 upload init / 直接上传到文件 `ready`，目标 < 15s
- 100MB 文件可以异步运行更久，但必须提供稳定进度并避免进程崩溃

## 9. 安全与隐私

- 云端部署必须使用 TLS
- 密码使用 bcrypt 哈希
- JWT 校验集中在 `api/deps.py`
- 日志默认不得记录用户原始文档内容
- 生产环境必须覆盖默认密钥配置

## 10. 测试策略

后端最小覆盖：

- Auth 注册/登录的成功与错误分支
- 直接上传与 multipart 上传任务创建
- 任务进度响应契约
- Chat SSE 事件顺序
- CitationValidator 的逐句引用校验与降级行为

验收标准：

- `import app.main` 成功
- API 契约与 `docs/API.md` 一致
- 核心集成流程可在 PostgreSQL 上通过
