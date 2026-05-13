# AI Second Brain 技术设计文档（TDD）
**文档版本**：V1.1  
**最后更新**：2026-05-12  
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
AISB_DATABASE_URL=postgresql+asyncpg://aisb:aisb@localhost:5433/aisb
AISB_DATABASE_URL_SYNC=postgresql+psycopg://aisb:aisb@localhost:5433/aisb
AISB_SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
AISB_REDIS_URL=redis://localhost:6379/0
AISB_STORAGE_DIR=.data/storage
AISB_UPLOAD_TMP_DIR=.data/uploads
```

邮箱验证码注册额外配置：

```env
AISB_SMTP_HOST=smtp.example.com
AISB_SMTP_PORT=587
AISB_SMTP_USERNAME=apikey
AISB_SMTP_PASSWORD=change-me
AISB_SMTP_FROM_EMAIL=no-reply@example.com
AISB_SMTP_USE_TLS=true
AISB_EMAIL_DEV_MODE=false
AISB_EMAIL_CODE_EXPIRE_MINUTES=10
AISB_EMAIL_CODE_RESEND_INTERVAL_SECONDS=60
AISB_EMAIL_CODE_DAILY_LIMIT=10
AISB_EMAIL_CODE_MAX_ATTEMPTS=5
```

本地开发可设置 `AISB_EMAIL_DEV_MODE=true`，邮件服务不连接 SMTP，只在开发日志输出验证码。生产环境禁止记录验证码明文。

## 5. 数据模型

数据库表结构以 `docs/database.md` 为准，Alembic 初始迁移为 `backend/alembic/versions/0001_init.py`，新增表结构通过后续 Alembic migration 演进。

关键要求：

- `email_verification_codes` 仅保存验证码哈希，不保存明文验证码，用于邮箱验证码注册、频率限制、过期校验和消费状态记录
- `files.sha256` 用于去重和上传完整性校验
- `file_chunks.page_number`、`start_pos`、`end_pos` 和 `locator` 用于引用预览与高亮
- `conversations.scope_type` 和 `scope_ids` 用于支持 global/folder/file 范围问答
- 文件删除必须级联清理数据库中的 chunks/tags/tasks，同时清除向量库记录和存储的原文件

## 6. 邮箱验证码注册

注册采用“先发码，再注册”的两步流程：

1. 前端调用 `POST /auth/email-verification-code`，提交 `email` 与 `purpose=register`
2. 后端校验邮箱格式、邮箱未注册、同邮箱发送间隔与每日发送上限
3. 后端生成 6 位数字验证码，只持久化验证码哈希，明文仅用于当次邮件发送
4. 邮件发送成功后记录发送状态、过期时间与尝试次数
5. 用户提交邮箱、密码、昵称和验证码调用 `POST /auth/register`
6. 后端校验验证码用途、哈希、过期时间、消费状态与尝试次数
7. 验证通过后创建用户、消费验证码、返回 JWT 与用户信息

后端职责划分：

- `api/routers/v1/auth.py` 负责注册与发码接口的协议适配
- `schemas/auth.py` 定义发码请求、注册请求和登录同形态响应
- `services/auth_service.py` 编排用户创建、验证码校验、token 创建和事务提交
- 新增验证码 repository/service 管理验证码生成、哈希、频控、消费和失败尝试计数
- 邮件发送通过 SMTP 抽象服务完成；SMTP 发送失败返回统一邮件发送错误，不创建可用于注册的验证码

安全策略：

- 验证码默认 10 分钟过期
- 同一邮箱默认 60 秒内只能发送一次注册验证码
- 同一邮箱默认每日最多发送 10 次注册验证码
- 单个验证码默认最多校验 5 次，超过后作废
- 注册验证码校验成功后必须立即标记为已消费
- 生产日志不得记录验证码明文、密码或邮件正文
- 注册成功响应与登录接口保持一致：`token`、`expires_in`、`user`

错误处理：

- 已注册邮箱发送验证码时返回 `ERR_EMAIL_EXISTS`
- 发送过于频繁返回 `ERR_VERIFICATION_CODE_RATE_LIMITED`
- 超过每日上限返回 `ERR_VERIFICATION_CODE_DAILY_LIMIT`
- 验证码错误、过期、已消费或尝试次数超限返回对应验证码错误码，不创建用户
- SMTP 配置缺失或发送失败返回 `ERR_EMAIL_SEND_FAILED`

## 7. RAG 流水线

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

## 8. API 与 SSE 协议

`docs/API.md` 是接口与载荷的单一事实来源。  
`docs/backend/add-api-endpoint.md` 说明了如何新增 API endpoint。

SSE 事件顺序：

```text
chunk* -> citation? -> done
```

每个 `citation` 载荷都必须包含足够的 locator 数据，以便前端右侧抽屉能够打开原始文件，并高亮近似的来源位置。

## 9. 性能与验收口径

- Chat TTFB：从请求接收到首个 SSE `chunk` 发出，目标 < 2s
- 10MB 建库时间：从 upload init / 直接上传到文件 `ready`，目标 < 15s
- 100MB 文件可以异步运行更久，但必须提供稳定进度并避免进程崩溃

## 10. 安全与隐私

- 云端部署必须使用 TLS
- 密码使用 bcrypt 哈希
- 邮箱验证码只保存哈希，生产环境不得记录验证码明文
- 邮箱验证码接口必须有同邮箱发送间隔、每日上限和校验尝试次数限制
- JWT 校验集中在 `api/deps.py`
- 日志默认不得记录用户原始文档内容
- 生产环境必须覆盖默认密钥配置

## 11. 测试策略

后端最小覆盖：

- Auth 注册/登录的成功与错误分支
- 邮箱验证码发送成功、已注册邮箱拒绝、频率限制、每日上限、验证码错误/过期/已消费/尝试次数超限
- 验证码正确时注册成功并返回与登录一致的响应结构
- 直接上传与 multipart 上传任务创建
- 任务进度响应契约
- Chat SSE 事件顺序
- CitationValidator 的逐句引用校验与降级行为

验收标准：

- `import app.main` 成功
- API 契约与 `docs/API.md` 一致
- 核心集成流程可在 PostgreSQL 上通过
