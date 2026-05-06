"""Создание и конфигурация PTB Application."""
from __future__ import annotations

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.bot.handlers import (
    handle_message,
    on_about,
    on_help,
    on_start,
    on_stats,
)
from app.config import settings


def build_application() -> Application:
    """Создаёт и настраивает Application бота."""
    # updater(None) — отключаем поллинг, мы будем работать через webhook.
    app: Application = (
        ApplicationBuilder()
        .token(settings.bot_token)
        .updater(None)
        .build()
    )

    # Команды
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(CommandHandler("help", on_help))
    app.add_handler(CommandHandler("about", on_about))
    app.add_handler(CommandHandler("stats", on_stats))

    # Текстовые сообщения (не команды)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app


__all__ = ["build_application"]
