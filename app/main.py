"""Главный модуль приложения. Запуск:

    uvicorn app.main:app --host 0.0.0.0 --port 8080

Lifespan:
1. Запуск FastAPI → инициализация PTB Application.
2. setWebhook через Telegram API (с secret_token).
3. Старт PTB Application.
4. На shutdown — graceful: остановка PTB, закрытие БД.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from telegram import Update

from app import __version__
from app.api.telegram import router as telegram_router
from app.api.v1 import api_v1_router
from app.bot import build_application
from app.config import settings
from app.core.logging import setup_logging
from app.db.session import close_db


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: C901
    """Жизненный цикл приложения. Инициализация и graceful shutdown."""
    setup_logging()
    logger.info("🚀 Запуск финансового трекера v{}", __version__)
    logger.info("Environment: {}", settings.environment)

    # === Инициализация Telegram бота ===
    ptb_app = build_application()
    app.state.ptb_app = ptb_app

    await ptb_app.initialize()

    # Регистрируем webhook
    try:
        await ptb_app.bot.set_webhook(
            url=settings.webhook_url,
            secret_token=settings.webhook_secret,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=False,
        )
        webhook_info = await ptb_app.bot.get_webhook_info()
        logger.info(
            "✅ Webhook установлен: url={} pending={} max_connections={}",
            webhook_info.url,
            webhook_info.pending_update_count,
            webhook_info.max_connections,
        )
    except Exception as e:
        # Не валим приложение — может быть локальная разработка без публичного URL
        logger.warning(
            "⚠️ Не удалось установить webhook (это нормально для локальной разработки): {}", e
        )

    await ptb_app.start()
    logger.info("✅ PTB Application запущен")

    # === Приложение работает ===
    yield

    # === Graceful shutdown ===
    logger.info("🛑 Останавливаю приложение...")
    try:
        await ptb_app.stop()
        await ptb_app.shutdown()
        logger.info("✅ PTB Application остановлен")
    except Exception as e:
        logger.exception("Ошибка при остановке бота: {}", e)

    await close_db()
    logger.info("✅ Соединения с БД закрыты. До встречи!")


app = FastAPI(
    title="Финансовый Трекер API",
    description=(
        "REST API для Telegram Mini App финансового трекера.\n\n"
        "Авторизация: Telegram WebApp initData → JWT (Bearer)."
    ),
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)

# CORS — для запросов с GitHub Pages / web.telegram.org
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Роутеры ===
app.include_router(telegram_router)
app.include_router(api_v1_router)


# === Health checks ===
@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "service": "finance-tracker",
        "version": __version__,
        "status": "ok",
    }


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Healthcheck для платформы хостинга."""
    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):  # type: ignore[no-untyped-def]
    """Глобальный обработчик ошибок — чтоб не текли стектрейсы наружу."""
    logger.exception("Необработанное исключение: {}", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"},
    )
