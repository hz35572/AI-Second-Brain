# AI Second Brain 数据库设计

**最后更新**：2026-05-02  
**数据库**：PostgreSQL 16  
**单一事实来源**：本文件 + `backend/alembic/versions/0001_init.py`

## 1. 设计原则

- MVP 元数据统一存储在 PostgreSQL。
- 主键统一使用 UUID。
- 删除文件时必须级联清理其 chunk、tag、task 关联以及向量库/对象存储中的派生数据。
- 引用溯源相关字段必须保留，不允许为了简化实现而删除。

## 2. 表清单

### `users`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `uuid` | 主键，`gen_random_uuid()` |
| `email` | `varchar(255)` | 唯一邮箱 |
| `password_hash` | `varchar(255)` | 密码哈希 |
| `name` | `varchar(100)` | 用户名，可空 |
| `avatar_url` | `varchar(500)` | 头像地址，可空 |
| `deployment_mode` | `varchar(20)` | `cloud` / `local` 等 |
| `created_at` | `timestamptz` | 创建时间 |
| `updated_at` | `timestamptz` | 更新时间 |

索引与约束：

- `uq_users_email`
- `idx_users_email`

### `folders`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `uuid` | 主键 |
| `user_id` | `uuid` | 所属用户 |
| `parent_id` | `uuid` | 父文件夹，可空 |
| `name` | `varchar(255)` | 文件夹名称 |
| `path` | `varchar(1000)` | 规范化路径 |
| `sort_order` | `integer` | 排序值 |
| `created_at` | `timestamptz` | 创建时间 |
| `updated_at` | `timestamptz` | 更新时间 |

索引：

- `idx_folders_user`
- `idx_folders_parent`
- `idx_folders_path`

### `files`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `uuid` | 主键 |
| `user_id` | `uuid` | 所属用户 |
| `folder_id` | `uuid` | 所属文件夹，可空 |
| `name` | `varchar(255)` | 当前名称 |
| `original_name` | `varchar(255)` | 上传原始名称 |
| `file_path` | `varchar(1000)` | 对象存储或本地相对路径 |
| `file_size` | `bigint` | 文件字节数 |
| `mime_type` | `varchar(100)` | MIME 类型，可空 |
| `sha256` | `varchar(64)` | 文件完整性校验 |
| `page_count` | `integer` | 页数 |
| `word_count` | `integer` | 词数 |
| `summary` | `text` | 摘要，可空 |
| `status` | `varchar(20)` | `pending/parsing/ready/failed` |
| `error_message` | `text` | 失败原因，可空 |
| `upload_progress` | `integer` | 上传/处理进度 |
| `created_at` | `timestamptz` | 创建时间 |
| `updated_at` | `timestamptz` | 更新时间 |

索引：

- `idx_files_user`
- `idx_files_folder`
- `idx_files_status`
- `idx_files_sha256`

### `file_chunks`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `uuid` | 主键 |
| `user_id` | `uuid` | 所属用户 |
| `file_id` | `uuid` | 所属文件 |
| `chunk_index` | `integer` | 文件内顺序 |
| `content` | `text` | chunk 文本 |
| `page_number` | `integer` | PDF/分页文档页码，可空 |
| `start_pos` | `integer` | chunk 起始偏移，可空 |
| `end_pos` | `integer` | chunk 结束偏移，可空 |
| `locator` | `jsonb` | 非分页文档定位信息，可空 |
| `token_count` | `integer` | token 数，可空 |
| `vector_id` | `varchar(100)` | 向量库记录 ID，可空 |
| `created_at` | `timestamptz` | 创建时间 |

索引与约束：

- `idx_chunks_file`
- `idx_chunks_user`
- `idx_chunks_file_chunk_index`（唯一约束，`file_id + chunk_index`）

引用溯源依赖：

- `page_number`
- `start_pos`
- `end_pos`
- `locator`

### `tags`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `uuid` | 主键 |
| `user_id` | `uuid` | 所属用户 |
| `file_id` | `uuid` | 所属文件 |
| `name` | `varchar(100)` | 标签名 |
| `confidence` | `numeric(3,2)` | AI 置信度，可空 |
| `source` | `varchar(20)` | `ai` / `manual` |
| `created_at` | `timestamptz` | 创建时间 |

索引与约束：

- `idx_tags_name`
- `idx_tags_user_file_name`

### `conversations`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `uuid` | 主键 |
| `user_id` | `uuid` | 所属用户 |
| `title` | `varchar(255)` | 标题，可空 |
| `scope_type` | `varchar(20)` | `global/folder/file` |
| `scope_ids` | `uuid[]` | 范围 ID 数组，可空 |
| `model_provider` | `varchar(50)` | 模型提供商，可空 |
| `model_name` | `varchar(100)` | 模型名，可空 |
| `created_at` | `timestamptz` | 创建时间 |
| `updated_at` | `timestamptz` | 更新时间 |

索引：

- `idx_conversations_user`
- `idx_conversations_scope_ids`（GIN）

### `messages`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `uuid` | 主键 |
| `conversation_id` | `uuid` | 所属会话 |
| `role` | `varchar(20)` | `user/assistant/system` |
| `content` | `text` | 消息内容 |
| `citations` | `jsonb` | 引用数组，可空 |
| `metadata` | `jsonb` | 扩展字段，可空 |
| `created_at` | `timestamptz` | 创建时间 |

索引：

- `idx_messages_conv`
- `idx_messages_created`

### `tasks`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `uuid` | 主键 |
| `user_id` | `uuid` | 所属用户 |
| `task_type` | `varchar(50)` | 如 `embedding` |
| `related_file_id` | `uuid` | 关联文件，可空 |
| `status` | `varchar(20)` | `pending/running/completed/failed` |
| `progress` | `integer` | 进度百分比 |
| `result` | `jsonb` | 任务结果，可空 |
| `error_message` | `text` | 失败原因，可空 |
| `created_at` | `timestamptz` | 创建时间 |
| `updated_at` | `timestamptz` | 更新时间 |

索引：

- `idx_tasks_user`
- `idx_tasks_status`
- `idx_tasks_file`

## 3. 级联与一致性要求

- `users` 删除时级联删除其 `folders/files/file_chunks/tags/conversations/tasks`。
- `folders.parent_id` 级联删除子目录。
- `files` 删除时数据库侧级联删除 `file_chunks`，并要求应用层同步清理：
  - Qdrant 中对应向量记录
  - 对象存储原文件
  - 相关缓存
- `messages` 随 `conversations` 级联删除。

## 4. 与引用溯源相关的约束

- 每个可用于回答的 `file_chunks` 记录必须能映射到原文定位信息。
- PDF MVP 至少保证 `page_number` 正确，`start_pos/end_pos` 或近似高亮可用。
- 对非分页文档，使用 `locator` 保存 sheet、行列、段落等定位信息。
