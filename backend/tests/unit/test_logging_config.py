import json
import logging
from pathlib import Path
from datetime import datetime

from app.core.config import Settings
from app.core.logging_config import (
    ColoredFormatter,
    DailyDateFileHandler,
    SensitiveDataFilter,
    configure_logging,
    stop_logging_listener,
)


def _settings(tmp_path: Path, **overrides) -> Settings:
    values = {
        "LOG_DIR": tmp_path,
        "LOG_FILE_NAME": "test.log",
        "LOG_QUEUE_ENABLED": False,
        "LOG_CONSOLE_ENABLED": False,
        "LOG_FILE_ENABLED": True,
        "LOG_ROTATION": "daily",
        "LOG_FILE_MAX_BYTES": 256,
        "LOG_FILE_BACKUP_COUNT": 1,
    }
    values.update(overrides)
    return Settings(**values)


def test_configure_logging_writes_file_with_expected_fields(tmp_path: Path) -> None:
    configure_logging(_settings(tmp_path))
    try:
        logger = logging.getLogger("app.tests.logging")
        logger.info("hello from logging test")

        log_content = (tmp_path / f"{datetime.now().date().isoformat()}.log").read_text(encoding="utf-8")

        assert "INFO" in log_content
        assert "app.tests.logging" in log_content
        assert "pid=" in log_content
        assert "tid=" in log_content
        assert "hello from logging test" in log_content
    finally:
        stop_logging_listener()
        logging.getLogger().handlers.clear()


def test_daily_file_handler_switches_to_new_date_file(tmp_path: Path) -> None:
    current = datetime(2026, 5, 18, 8, 0, 0)

    def now(_timezone) -> datetime:  # noqa: ANN001
        return current

    handler = DailyDateFileHandler(
        tmp_path,
        "%Y-%m-%d.log",
        timezone=datetime.now().astimezone().tzinfo,
        backup_count=5,
        now=now,
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("app.tests.daily")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        logger.info("first day")
        current = datetime(2026, 5, 18, 23, 59, 0)
        logger.info("same day")
        current = datetime(2026, 5, 19, 0, 0, 1)
        logger.info("second day")

        assert (tmp_path / "2026-05-18.log").read_text(encoding="utf-8") == "first day\nsame day\n"
        assert (tmp_path / "2026-05-19.log").read_text(encoding="utf-8") == "second day\n"
    finally:
        handler.close()
        logger.handlers.clear()


def test_sensitive_data_filter_redacts_common_secrets() -> None:
    record = logging.LogRecord(
        name="app.tests.logging",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="password=plain token:abc api_key=xyz",
        args=(),
        exc_info=None,
    )

    assert SensitiveDataFilter().filter(record)
    assert record.getMessage() == "password=[REDACTED] token:[REDACTED] api_key=[REDACTED]"


def test_colored_formatter_can_be_disabled() -> None:
    record = logging.LogRecord(
        name="app.tests.logging",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="plain warning",
        args=(),
        exc_info=None,
    )

    output = ColoredFormatter("%(levelname)s %(message)s", enabled=False).format(record)

    assert output == "WARNING plain warning"


def test_logging_can_be_loaded_from_json_config_file(tmp_path: Path) -> None:
    log_path = tmp_path / "json-config.log"
    config_path = tmp_path / "logging.json"
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "standard": {
                        "format": "%(levelname)s:%(name)s:%(message)s",
                    }
                },
                "handlers": {
                    "file": {
                        "class": "logging.FileHandler",
                        "filename": str(log_path),
                        "formatter": "standard",
                        "encoding": "utf-8",
                    }
                },
                "root": {"level": "INFO", "handlers": ["file"]},
            }
        ),
        encoding="utf-8",
    )

    configure_logging(_settings(tmp_path, LOG_CONFIG_FILE=config_path))
    try:
        logging.getLogger("app.tests.json").info("configured by file")

        assert log_path.read_text(encoding="utf-8") == "INFO:app.tests.json:configured by file\n"
    finally:
        logging.getLogger().handlers.clear()
