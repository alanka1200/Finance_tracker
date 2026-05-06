"""Endpoint для приёма webhook'ов от Telegram."""
from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException, Request, status
from loguru import logger
from telegram import Update

from app.config import settings

router = APIRouter(tags=["telegram"])


@router.post(settings.webhook_path)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> dict[str, str]:
    """Принимает Update от Telegram, валидирует секрет, передаёт в PTB.

    Защита: 
    1. Секретный путь webhook'а (часть webhook_secret).
    2. Заголовок X-Telegram-Bot-Api-Secret-Token, который Telegram добавляет к каждому
       запросу, если мы передали secret_token в setWebhook.
    """
    # Constant-time сравнение секрета
    if not x_telegram_bot_api_secret_token or not hmac.compare_digest(
        x_telegram_bot_api_secret_token, settings.webhook_secret
    ):
        logger.warning(
            "Невалидный или отсутствующий webhook secret. ip={}",
            request.client.host if request.client else "?",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    # PTB Application берётся из app.state — будет инициализирован в lifespan
    ptb_app = request.app.state.ptb_app
    try:
        body = await request.json()
        update = Update.de_json(body, ptb_app.bot)
        if update:
            await ptb_app.process_update(update)
    except Exception as e:
        # ВАЖНО: даже на ошибке возвращаем 200, иначе Telegram будет ретраить
        logger.exception("Ошибка обработки webhook: {}", e)

    return {"ok": "true"}
