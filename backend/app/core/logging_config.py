"""Central logging configuration for the backend application."""

from __future__ import annotations

import atexit
import json
import logging
import logging.config
import logging.handlers
import os
import queue
import re
import sys
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime, tzinfo
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import Settings

DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] [pid=%(process)d tid=%(thread)d] %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
DEFAULT_ACCESS_LOG_FORMAT = (
    "%(asctime)s %(levelname)s [%(name)s] [pid=%(process)d tid=%(thread)d] "
    '%(client_addr)s - "%(request_line)s" %(status_code)s'
)
SENSITIVE_VALUE_RE = re.compile(
    r"(?i)\b(password|secret|token|api[_-]?key|authorization|cookie)\b(\s*[=:]\s*)([^\s,;]+)"
)

_QUEUE_LISTENER: logging.handlers.QueueListener | None = None


class SensitiveDataFilter(logging.Filter):
    """Redact common credential values from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._redact(record.msg)
        if isinstance(record.args, Mapping):
            record.args = {key: self._redact(value) for key, value in record.args.items()}
        elif isinstance(record.args, tuple):
            record.args = tuple(self._redact(value) for value in record.args)
        return True

    @staticmethod
    def _redact(value: object) -> object:
        if not isinstance(value, str):
            return value
        return SENSITIVE_VALUE_RE.sub(r"\1\2[REDACTED]", value)


class ColoredFormatter(logging.Formatter):
    """Formatter that adds ANSI colors for local console logs."""

    COLORS = {
        logging.DEBUG: "\033[36m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[35m",
    }
    RESET = "\033[0m"

    def __init__(self, fmt: str, datefmt: str | None = None, *, enabled: bool = True) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.enabled = enabled

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        if not self.enabled:
            return message
        color = self.COLORS.get(record.levelno)
        if not color:
            return message
        return f"{color}{message}{self.RESET}"


class DailyDateFileHandler(logging.FileHandler):
    """File handler that writes to a new date-named file each day."""

    def __init__(
        self,
        log_dir: Path,
        filename_format: str,
        *,
        timezone: tzinfo,
        backup_count: int,
        now: Callable[[tzinfo], datetime] | None = None,
        encoding: str = "utf-8",
    ) -> None:
        self.log_dir = log_dir
        self.filename_format = filename_format
        self.timezone = timezone
        self.backup_count = backup_count
        self.now = now or datetime.now
        self.current_date = self._today()
        super().__init__(self._filename_for(self.current_date), encoding=encoding)

    def emit(self, record: logging.LogRecord) -> None:
        self._switch_file_if_needed()
        super().emit(record)

    def _switch_file_if_needed(self) -> None:
        today = self._today()
        if today == self.current_date:
            return
        self.acquire()
        try:
            today = self._today()
            if today == self.current_date:
                return
            if self.stream:
                self.stream.flush()
                self.stream.close()
                self.stream = None
            self.baseFilename = str(self._filename_for(today))
            self.current_date = today
            self.stream = self._open()
            self._cleanup_old_logs()
        finally:
            self.release()

    def _today(self) -> date:
        return self.now(self.timezone).date()

    def _filename_for(self, value: date) -> Path:
        return self.log_dir / value.strftime(self.filename_format)

    def _cleanup_old_logs(self) -> None:
        if self.backup_count <= 0:
            return
        date_logs = sorted(
            path
            for path in self.log_dir.glob("*.log")
            if path.is_file() and _looks_like_date_named_log(path.name)
        )
        for old_log in date_logs[: -self.backup_count]:
            old_log.unlink(missing_ok=True)


def configure_logging(
    settings: Settings,
    *,
    handlers: Iterable[logging.Handler] | None = None,
    filters: Iterable[logging.Filter] | None = None,
) -> None:
    """Configure application logging from a config file or Settings values.

    Args:
        settings: Application settings containing AISB_LOG_* values.
        handlers: Optional custom handlers appended to the root logger.
        filters: Optional custom filters applied to all configured handlers.
    """
    global _QUEUE_LISTENER

    stop_logging_listener()

    if settings.LOG_CONFIG_FILE:
        config_path = Path(settings.LOG_CONFIG_FILE)
        with config_path.open("r", encoding="utf-8") as config_file:
            logging.config.dictConfig(json.load(config_file))
        return

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(_parse_log_level(settings.LOG_LEVEL))

    configured_filters: list[logging.Filter] = [SensitiveDataFilter()]
    if filters:
        configured_filters.extend(filters)

    target_handlers = _build_handlers(settings)
    if handlers:
        target_handlers.extend(handlers)

    for handler in target_handlers:
        for log_filter in configured_filters:
            handler.addFilter(log_filter)

    if settings.LOG_QUEUE_ENABLED and target_handlers:
        log_queue: queue.Queue[logging.LogRecord] = queue.Queue(-1)
        queue_handler = logging.handlers.QueueHandler(log_queue)
        root_logger.addHandler(queue_handler)
        _QUEUE_LISTENER = logging.handlers.QueueListener(log_queue, *target_handlers, respect_handler_level=True)
        _QUEUE_LISTENER.start()
        atexit.register(stop_logging_listener)
    else:
        for handler in target_handlers:
            root_logger.addHandler(handler)

    _configure_library_loggers(settings)


def stop_logging_listener() -> None:
    """Stop the async logging listener if queue logging is enabled."""
    global _QUEUE_LISTENER
    if _QUEUE_LISTENER is not None:
        _QUEUE_LISTENER.stop()
        _QUEUE_LISTENER = None


def get_logger(name: str) -> logging.Logger:
    """Return a named logger for application modules."""
    return logging.getLogger(name)


def _build_handlers(settings: Settings) -> list[logging.Handler]:
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
    handlers: list[logging.Handler] = []

    if settings.LOG_CONSOLE_ENABLED:
        use_color = settings.LOG_CONSOLE_COLOR and _stream_supports_color(sys.stderr)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(_parse_log_level(settings.LOG_CONSOLE_LEVEL or settings.LOG_LEVEL))
        console_handler.setFormatter(ColoredFormatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT, enabled=use_color))
        handlers.append(console_handler)

    if settings.LOG_FILE_ENABLED:
        settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_path = settings.LOG_DIR / settings.LOG_FILE_NAME
        file_handler: logging.Handler
        if settings.LOG_ROTATION == "daily":
            file_handler = DailyDateFileHandler(
                settings.LOG_DIR,
                settings.LOG_DAILY_FILE_NAME_FORMAT,
                timezone=_get_timezone(settings.TIMEZONE),
                backup_count=settings.LOG_FILE_BACKUP_COUNT,
                encoding="utf-8",
            )
        elif settings.LOG_ROTATION == "time":
            file_handler = logging.handlers.TimedRotatingFileHandler(
                file_path,
                when=settings.LOG_ROTATION_WHEN,
                interval=settings.LOG_ROTATION_INTERVAL,
                backupCount=settings.LOG_FILE_BACKUP_COUNT,
                encoding="utf-8",
                utc=True,
            )
        else:
            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=settings.LOG_FILE_MAX_BYTES,
                backupCount=settings.LOG_FILE_BACKUP_COUNT,
                encoding="utf-8",
            )
        file_handler.setLevel(_parse_log_level(settings.LOG_FILE_LEVEL or settings.LOG_LEVEL))
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    return handlers


def _configure_library_loggers(settings: Settings) -> None:
    logging.getLogger("uvicorn").handlers.clear()
    logging.getLogger("uvicorn").propagate = True
    logging.getLogger("uvicorn.error").handlers.clear()
    logging.getLogger("uvicorn.error").propagate = True
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = True
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.LOG_SQLALCHEMY_ENABLED else logging.WARNING
    )


def _parse_log_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    normalized = level.upper()
    value = logging.getLevelName(normalized)
    if isinstance(value, int):
        return value
    raise ValueError(f"Unsupported log level: {level}")


def _stream_supports_color(stream: Any) -> bool:
    return hasattr(stream, "isatty") and stream.isatty() and os.getenv("NO_COLOR") is None


def _get_timezone(name: str) -> tzinfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return UTC


def _looks_like_date_named_log(filename: str) -> bool:
    try:
        datetime.strptime(filename, "%Y-%m-%d.log")
    except ValueError:
        return False
    return True
