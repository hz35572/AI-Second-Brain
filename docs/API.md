# AI Second Brain API 文档（MVP - Postgres）

本文档与 `docs/TECH_DESIGN.md` 保持一致，整理 API 规范，供前后端联调、测试与后续实现对齐使用。

数据库表结构参考：`docs/database.md`。

## 1. 通用规范

- Base URL：`/api/v1`
- 协议：HTTPS（云端）/ HTTP（本地离线）
- 数据格式：JSON（除 SSE/文件分片上传外）
- 鉴权：JWT Bearer Token

### 1.1 统一响应体

成功响应：

```json
{
  "code": 0,
  "data": {}
}
```

错误响应（建议实现形态）：

```json
{
  "code": "ERR_INVALID_ARGUMENT",
  "message": "参数错误",
  "details": {}
}
```

### 1.2 认证头

```http
Authorization: Bearer <jwt_token>
```

### 1.3 核心数据结构

Citation（引用项，支持 PDF/分页与 Excel/非分页定位）：

```json
{
  "index": 1,
  "chunk_id": "uuid",
  "file_id": "uuid",
  "file_name": "document.pdf",
  "page": 3,
  "locator": {
    "type": "excel",
    "sheet": "Sheet1",
    "row_start": 1,
    "row_end": 50,
    "col_start": 1,
    "col_end": 10
  },
  "text": "原文对应段落/块内容预览...",
  "highlight_positions": {
    "start": 0,
    "end": 120
  }
}
```

说明：

- PDF/分页文档优先使用 `page + highlight_positions(start/end)` 做跳转与高亮。
- Excel 之类非分页文档使用 `locator` 定位；`highlight_positions` 可为空或忽略。

## 2. 认证模块

### 2.1 发送邮箱验证码

`POST /auth/email-verification-code`

用于注册前发送邮箱验证码。验证码仅用于 `purpose=register` 的注册场景，默认 10 分钟有效。

Request:

```json
{
  "email": "user@example.com",
  "purpose": "register"
}
```

Response 200:

```json
{
  "code": 0,
  "data": {
    "email": "user@example.com",
    "purpose": "register",
    "expires_in": 600,
    "resend_after": 60
  }
}
```

错误码：

| code | HTTP | 含义 |
| --- | --- | --- |
| `ERR_EMAIL_EXISTS` | 400 | 邮箱已注册 |
| `ERR_VERIFICATION_CODE_RATE_LIMITED` | 429 | 同一邮箱发送过于频繁 |
| `ERR_VERIFICATION_CODE_DAILY_LIMIT` | 429 | 同一邮箱当日发送次数超限 |
| `ERR_EMAIL_SEND_FAILED` | 503 | SMTP 配置缺失或邮件发送失败 |

### 2.2 用户注册

`POST /auth/register`

Request:

```json
{
  "email": "user@example.com",
  "password": "min_8_chars",
  "name": "用户名",
  "verification_code": "123456"
}
```

Response 201:

```json
{
  "code": 0,
  "data": {
    "token": "jwt_token",
    "expires_in": 86400,
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "name": "用户名"
    }
  }
}
```

错误码：

| code | HTTP | 含义 |
| --- | --- | --- |
| `ERR_EMAIL_EXISTS` | 400 | 邮箱已注册 |
| `ERR_INVALID_VERIFICATION_CODE` | 400 | 验证码错误 |
| `ERR_VERIFICATION_CODE_EXPIRED` | 400 | 验证码已过期 |
| `ERR_VERIFICATION_CODE_USED` | 400 | 验证码已被消费 |
| `ERR_VERIFICATION_CODE_ATTEMPTS_EXCEEDED` | 429 | 验证码尝试次数超限 |
| `ERR_INVALID_ARGUMENT` | 422 | 邮箱、密码或验证码格式错误 |

说明：

- 注册成功响应与登录接口保持一致，前端统一从 `data.token` 与 `data.user` 读取认证状态。
- 服务端必须在创建用户前完成验证码校验；验证码校验成功后必须标记为已消费。
- 密码仍使用 bcrypt 哈希，密码 UTF-8 字节长度不得超过 bcrypt 限制。

### 2.3 用户登录

`POST /auth/login`

Request:

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

Response 200:

```json
{
  "code": 0,
  "data": {
    "token": "jwt_token",
    "expires_in": 86400,
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "name": "用户名"
    }
  }
}
```

## 3. 文件管理模块

### 3.1 直接上传文件（小文件）

`POST /files/upload`

Content-Type: `multipart/form-data`

Parameters:

- `file`: File
- `folder_id`: UUID（可选）

Response 202:

```json
{
  "code": 0,
  "data": {
    "file_id": "uuid",
    "task_id": "uuid",
    "status": "pending"
  }
}
```

### 3.2 分片上传初始化（大文件/断点续传）

`POST /files/upload/init`

Request:

```json
{
  "file_name": "large_file.pdf",
  "file_size": 104857600,
  "mime_type": "application/pdf",
  "folder_id": "uuid"
}
```

Response 200:

```json
{
  "code": 0,
  "data": {
    "upload_id": "uuid",
    "chunk_size": 5242880,
    "total_chunks": 20
  }
}
```

### 3.3 上传分片

`PUT /files/upload/{upload_id}/chunks/{chunk_index}`

Content-Type: `application/octet-stream`

Response 200:

```json
{
  "code": 0,
  "data": {
    "chunk_index": 0,
    "uploaded": true
  }
}
```

### 3.4 完成分片上传

`POST /files/upload/{upload_id}/complete`

Response 202:

```json
{
  "code": 0,
  "data": {
    "file_id": "uuid",
    "task_id": "uuid",
    "status": "parsing"
  }
}
```

### 3.5 获取文件列表

`GET /files?folder_id={uuid}&page=1&page_size=20&status=ready&tag=标签名`

Response 200:

```json
{
  "code": 0,
  "data": {
    "total": 100,
    "items": [
      {
        "id": "uuid",
        "name": "document.pdf",
        "file_size": 1048576,
        "mime_type": "application/pdf",
        "page_count": 50,
        "summary": "本文档主要介绍了...",
        "tags": ["AI", "技术文档"],
        "status": "ready",
        "created_at": "2026-04-23T10:00:00Z"
      }
    ]
  }
}
```

### 3.6 获取上传/处理进度

`GET /tasks/{task_id}/progress`

Response 200:

```json
{
  "code": 0,
  "data": {
    "task_id": "uuid",
    "task_type": "embedding",
    "status": "running",
    "progress": 85,
    "message": "正在向量化：85%"
  }
}
```

## 4. 文件夹管理模块

### 4.1 创建文件夹

`POST /folders`

Request:

```json
{
  "name": "工作文档",
  "parent_id": "uuid"
}
```

Response 201:

```json
{
  "code": 0,
  "data": {
    "id": "uuid",
    "name": "工作文档",
    "parent_id": null,
    "path": "/工作文档"
  }
}
```

### 4.2 获取文件夹树

`GET /folders/tree`

Response 200:

```json
{
  "code": 0,
  "data": [
    {
      "id": "uuid",
      "name": "根目录",
      "children": [
        {
          "id": "uuid",
          "name": "工作文档",
          "children": [],
          "file_count": 10
        }
      ]
    }
  ]
}
```

## 5. 对话问答模块（核心）

### 5.1 创建对话

`POST /chat/conversations`

Request:

```json
{
  "title": "关于AI的讨论",
  "scope_type": "global",
  "scope_ids": []
}
```

Response 201:

```json
{
  "code": 0,
  "data": {
    "id": "uuid",
    "title": "关于AI的讨论",
    "scope_type": "global",
    "created_at": "2026-04-23T10:00:00Z"
  }
}
```

### 5.2 发送消息（SSE 流式响应）

`POST /chat/conversations/{conversation_id}/messages`

Request:

```json
{
  "content": "这篇文章的主要观点是什么？",
  "stream": true
}
```

Response 200：`text/event-stream`

事件流示例：

```text
data: {"type":"chunk","content":"这篇"}
data: {"type":"chunk","content":"文章"}
data: {"type":"chunk","content":"主要"}
data: {"type":"citation","citations":[{"chunk_id":"uuid","file_id":"uuid","file_name":"doc.pdf","page":3,"text":"原文段落内容..."}]}
data: {"type":"done","metadata":{"token_usage":1024,"latency_ms":1500}}
```

SSE 事件类型定义：

| type | 含义 | payload 关键字段 |
|---|---|---|
| `chunk` | 增量文本 token/片段 | `content` |
| `citation` | 引用信息（用于角标跳转/高亮） | `citations: Citation[]` |
| `done` | 本次回答结束 | `metadata.token_usage`、`metadata.latency_ms` |

引用完整性约束（MVP）：

- Answer 文本中的事实句必须包含引用标记（如 `[1]`）；服务端需做校验与必要降级。

### 5.3 获取对话历史

`GET /chat/conversations/{conversation_id}/messages?page=1&page_size=20`

Response 200:

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "uuid",
        "role": "user",
        "content": "这篇文章的主要观点是什么？",
        "created_at": "2026-04-23T10:00:00Z"
      },
      {
        "id": "uuid",
        "role": "assistant",
        "content": "这篇文章的主要观点包括...[1]",
        "citations": [],
        "created_at": "2026-04-23T10:00:02Z"
      }
    ]
  }
}
```

### 5.4 获取对话列表

`GET /chat/conversations?page=1&page_size=20`

Response 200:

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "uuid",
        "title": "关于AI的讨论",
        "message_count": 10,
        "updated_at": "2026-04-23T10:00:00Z"
      }
    ]
  }
}
```

## 6. 标签与摘要模块（V1.5）

### 6.1 获取文件标签

`GET /files/{file_id}/tags`

Response 200:

```json
{
  "code": 0,
  "data": [
    {
      "id": "uuid",
      "name": "人工智能",
      "confidence": 0.95,
      "source": "ai"
    }
  ]
}
```

### 6.2 更新文件标签

`PUT /files/{file_id}/tags`

Request:

```json
{
  "tags": ["新增标签1", "新增标签2"]
}
```

Response 200:

```json
{
  "code": 0,
  "data": { "updated": true }
}
```

## 7. WebSocket 实时推送（任务进度）

`WS /ws/tasks`

用于实时推送任务进度：

```json
{
  "event": "task_progress",
  "task_id": "uuid",
  "progress": 85,
  "message": "正在向量化：85%"
}
```

完成事件：

```json
{
  "event": "task_completed",
  "task_id": "uuid",
  "status": "completed"
}
```
