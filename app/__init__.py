"""Финансовый трекер — backend приложение.

Архитектура:
- app/main.py        — FastAPI app, lifespan, монтаж роутеров
- app/config.py      — Settings из .env
- app/db/            — асинхронная SQLAlchemy сессия
- app/models/        — ORM модели
- app/schemas/       — Pydantic схемы для API
- app/api/           — HTTP роутеры (REST API + telegram webhook)
- app/services/      — бизнес-логика, не зависящая от HTTP
- app/bot/           — обработчики команд Telegram бота
- app/core/          — security (JWT), logging
"""
__version__ = "1.0.0"
