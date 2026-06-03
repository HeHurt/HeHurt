import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

_DEFAULT_LOGGER_NAME = "batterylifepredsys"
_DEFAULT_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"
_DEFAULT_FILE = str(Path(__file__).resolve().parent.parent.parent / "logs" / f"batterylifepredsys_{datetime.now().strftime('%Y%m%d')}.log")
_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5

_configured = False


def _to_level(level: str | int | None) -> int:
    if isinstance(level, int):
        return level
    if not level:
        return logging.INFO
    return getattr(logging, str(level).upper(), logging.INFO)


def configure_logging(
    level: str | int | None = None,
    log_file: str | None = None,
    logger_name: str = _DEFAULT_LOGGER_NAME,
    force: bool = False,
) -> logging.Logger:
    global _configured

    if _configured and not force:
        return logging.getLogger(logger_name)

    resolved_level = _to_level(level or os.getenv("BLP_LOG_LEVEL", "INFO"))
    resolved_file = log_file or os.getenv("BLP_LOG_FILE", _DEFAULT_FILE)

    logger = logging.getLogger(logger_name)
    logger.setLevel(resolved_level)
    logger.propagate = False

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(_DEFAULT_FORMAT, datefmt=_DEFAULT_DATEFMT)

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setLevel(resolved_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if resolved_file:
        log_path = Path(resolved_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=log_path,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(resolved_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _configured = True
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    configure_logging()
    if name:
        # 返回以默认 logger 名称为命名空间前缀的子 logger，
        # 这样子 logger 的消息会被已配置的处理器捕获并打印/写入文件。
        child_name = f"{_DEFAULT_LOGGER_NAME}.{name}"
        child_logger = logging.getLogger(child_name)
        if child_logger.level == logging.NOTSET:
            child_logger.setLevel(logging.getLogger(_DEFAULT_LOGGER_NAME).level)
        return child_logger
    return logging.getLogger(_DEFAULT_LOGGER_NAME)
