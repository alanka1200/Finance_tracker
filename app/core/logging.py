"""Настройка логирования через loguru."""
from __future__ import annotations

import logging
import sys

from loguru import logger

from app.config import settings


class InterceptHandler(logging.Handler):
    """Перехватывает логи стандартного logging и направляет в loguru.

    Это нужно, чтобы логи uvicorn/sqlalchemy/telegram попадали в общий поток.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6  # noqa: SLF001
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """Конфигурирует loguru и перехватывает стандартные логи."""
    logger.remove()  # убираем дефолтный обработчик
    logger.add(
        sys.stdout,
        level=settings.log_level.upper(),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=not settings.is_production,
        backtrace=True,
        diagnose=not settings.is_production,
    )

    # Перехватываем стандартный logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for logger_name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "sqlalchemy.engine",
        "httpx",
        "telegram",
    ):
        logging.getLogger(logger_name).handlers = [InterceptHandler()]
        logging.getLogger(logger_name).propagate = False

    logger.info(
        "Логирование настроено. environment={}, log_level={}",
        settings.environment,
        settings.log_level,
    )
