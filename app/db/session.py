"""Async подключение к Postgres через SQLAlchemy 2.0."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# Создаём движок один раз на всё приложение.
# pool_pre_ping=True проверяет соединение перед использованием (важно
# для serverless Postgres вроде Neon, где соединение может уснуть).
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,  # SQL логи через стандартный logging → loguru
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,  # 30 минут — переоткрываем соединение
)

# Фабрика сессий. expire_on_commit=False удобно для async — объекты
# остаются доступными после коммита.
SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — выдаёт сессию на запрос, гарантирует закрытие."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        # commit в endpoint'ах явный — это безопаснее, чем автокоммит


async def close_db() -> None:
    """Закрытие движка при shutdown."""
    await engine.dispose()
