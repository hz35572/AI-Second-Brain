# 后端日志方案使用指南

本文档说明 AI Second Brain 后端基于 Python 标准库 `logging` 的日志方案。实现入口为 `backend/app/core/logging_config.py`，应用启动时由 `backend/app/main.py` 调用 `configure_logging(settings)`。

## 1. 配置入口

默认通过 `.env` 或环境变量配置，统一使用 `AISB_` 前缀：

```env
AISB_LOG_LEVEL=INFO
AISB_LOG_CONSOLE_ENABLED=true
AISB_LOG_CONSOLE_COLOR=true
AISB_LOG_FILE_ENABLED=true
AISB_LOG_DIR=.data/logs
AISB_LOG_ROTATION=daily
AISB_LOG_DAILY_FILE_NAME_FORMAT=%Y-%m-%d.log
AISB_LOG_FILE_MAX_BYTES=10485760
AISB_LOG_FILE_BACKUP_COUNT=5
AISB_LOG_QUEUE_ENABLED=true
AISB_LOG_SQLALCHEMY_ENABLED=false
```

如需完全接管日志，可设置：

```env
AISB_LOG_CONFIG_FILE=config/logging.json
```

该文件必须是 `logging.config.dictConfig` 兼容 JSON。设置后，项目内置的 console/file/queue 配置不再自动生成。

## 2. 环境建议

开发环境：

- `AISB_LOG_LEVEL=DEBUG`
- `AISB_LOG_CONSOLE_ENABLED=true`
- `AISB_LOG_CONSOLE_COLOR=true`
- `AISB_LOG_FILE_ENABLED=true`
- `AISB_LOG_QUEUE_ENABLED=false`

测试环境：

- `AISB_LOG_LEVEL=WARNING`
- `AISB_LOG_CONSOLE_ENABLED=false`
- `AISB_LOG_FILE_ENABLED=false`

生产环境：

- `AISB_LOG_LEVEL=INFO`
- `AISB_LOG_CONSOLE_ENABLED=true`
- `AISB_LOG_FILE_ENABLED=true`
- `AISB_LOG_QUEUE_ENABLED=true`
- `AISB_LOG_ROTATION=daily`

容器化部署时可同时保留控制台日志给平台采集，并启用文件日志作为本地排障缓冲。

## 3. 日志级别

- `DEBUG`：局部调试信息，只用于开发或临时排障。
- `INFO`：应用启动、任务状态、上传完成、文件 ready、SSE 生命周期等关键业务状态。
- `WARNING`：可恢复异常、降级策略、重试、外部依赖短暂不可用。
- `ERROR`：请求失败、任务失败、外部服务调用失败、数据处理失败。
- `CRITICAL`：进程级不可恢复故障，例如关键配置缺失导致服务无法继续运行。

生产环境默认不输出 `DEBUG`，避免泄露上下文并降低性能开销。

## 4. 输出格式

默认格式：

```text
2026-05-18T10:20:30+0000 INFO [app.services.file_service] [pid=1234 tid=5678] file ready: file_id=...
```

字段包括：

- 时间戳
- 日志级别
- 模块名
- 进程 ID
- 线程 ID
- 日志消息

## 5. 文件轮转

默认按天创建日期文件：

```env
AISB_LOG_ROTATION=daily
AISB_LOG_DAILY_FILE_NAME_FORMAT=%Y-%m-%d.log
AISB_LOG_FILE_BACKUP_COUNT=14
```

该模式会将当天日志写入 `.data/logs/YYYY-MM-DD.log`，跨天后自动切换到新的日期文件。日期基于 `AISB_TIMEZONE`，默认 `UTC`。

也可以改为按大小轮转：

```env
AISB_LOG_ROTATION=size
AISB_LOG_FILE_NAME=backend.log
AISB_LOG_FILE_MAX_BYTES=10485760
AISB_LOG_FILE_BACKUP_COUNT=5
```

按时间轮转：

```env
AISB_LOG_ROTATION=time
AISB_LOG_FILE_NAME=backend.log
AISB_LOG_ROTATION_WHEN=midnight
AISB_LOG_ROTATION_INTERVAL=1
AISB_LOG_FILE_BACKUP_COUNT=14
```

时间轮转使用 UTC，便于跨机器聚合分析。

## 6. 代码使用方式

推荐在模块顶部创建 logger：

```python
import logging

logger = logging.getLogger(__name__)
```

也可以使用项目封装：

```python
from app.core.logging_config import get_logger

logger = get_logger(__name__)
```

参数化日志示例：

```python
logger.info("file ready: file_id=%s task_id=%s elapsed_ms=%s", file_id, task_id, elapsed_ms)
```

异常日志示例：

```python
try:
    send_message()
except EmailDeliveryError:
    logger.exception("email delivery failed: user_id=%s", user_id)
    raise
```

不要使用 f-string 拼接高频日志：

```python
# 避免
logger.debug(f"retrieved chunks: {chunks}")

# 推荐
logger.debug("retrieved chunk count: %s", len(chunks))
```

## 7. 安全与隐私

内置 `SensitiveDataFilter` 会脱敏常见凭据字段，例如 `password`、`secret`、`token`、`api_key`、`authorization`、`cookie`。

仍然禁止记录：

- 用户原始文档内容
- 用户问题全文
- 完整 RAG 检索上下文
- 密码、验证码、邮件正文
- JWT、API Key、Cookie 原文

需要排查质量问题时，只记录 ID、长度、耗时、命中数量、状态码和错误类型。若必须记录内容片段，需要先更新 `docs/TECH_DESIGN.md`，明确脱敏、采样、开关和保留周期。

## 8. 异常处理

FastAPI 全局异常处理器会记录未捕获异常堆栈，并向客户端返回统一错误：

```json
{"code": "ERR_INTERNAL_SERVER_ERROR", "message": "服务器内部错误", "details": {}}
```

业务层应优先抛出已有 HTTP/API 错误；未知异常才进入全局处理器。

## 9. 性能策略

生产环境启用 `AISB_LOG_QUEUE_ENABLED=true` 后，请求线程只把日志记录放入内存队列，实际格式化和 IO 由 `QueueListener` 完成，降低文件写入对主链路的影响。

高频路径建议：

- 使用参数化日志。
- 避免在 `DEBUG` 调用前构造大对象或序列化 JSON。
- 上传、解析、SSE 只记录阶段、耗时、计数和 ID。
- 大批量任务使用聚合日志，而不是每条 chunk 都输出 `INFO`。

## 10. 扩展方式

代码注入自定义 handler/filter：

```python
from app.core.config import settings
from app.core.logging_config import configure_logging

configure_logging(settings, handlers=[custom_handler], filters=[custom_filter])
```

复杂生产接入建议使用 `AISB_LOG_CONFIG_FILE` 指向 JSON dictConfig，例如接入集中式日志、JSON formatter 或云厂商 agent。

## 11. 验证

新增或调整日志配置后至少运行：

```bash
uv run pytest tests/unit/test_logging_config.py -q
uv run python -c "import app.main; print('ok')"
```
