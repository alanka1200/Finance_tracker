"""Конфигурация приложения. Читается из переменных окружения / .env файла."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Единая точка для всех конфигов. Все секреты — только сюда."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Telegram Bot ===
    bot_token: str = Field(..., description="Токен от @BotFather")
    webhook_secret: str = Field(..., min_length=16, description="Секрет webhook'а")
    public_url: str = Field(..., description="Публичный URL backend'а")
    frontend_url: str = Field(..., description="URL Mini App")

    # === База данных ===
    database_url: str = Field(..., description="Postgres async URL")

    # === Безопасность ===
    jwt_secret: str = Field(..., min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_access_token_ttl_minutes: int = 60
    jwt_refresh_token_ttl_days: int = 30
    telegram_initdata_ttl_seconds: int = 86400  # 24 часа

    admin_telegram_ids: str = ""

    # === LLM провайдеры (опциональные) ===
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    cerebras_api_key: str = ""
    cerebras_model: str = "llama-3.3-70b"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # === Market Data ===
    finnhub_api_key: str = ""
    twelve_data_api_key: str = ""
    coingecko_api_key: str = ""

    # === Прочее ===
    environment: Literal["development", "production", "test"] = "development"
    log_level: Literal["debug", "info", "warning", "error"] = "info"
    cors_origins: str = "http://localhost:3000,https://web.telegram.org,https://alanka1200.github.io,https://telegram.org"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Гарантируем, что используется async-драйвер asyncpg."""
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and "+asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def admin_ids_set(self) -> set[int]:
        """Парсит строку admin_telegram_ids в множество int'ов."""
        if not self.admin_telegram_ids:
            return set()
        return {
            int(x.strip())
            for x in self.admin_telegram_ids.split(",")
            if x.strip().isdigit()
        }

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def webhook_path(self) -> str:
        """Путь webhook'а — содержит часть секрета для двойной защиты."""
        # Берём первые 16 символов секрета как часть URL — это защищает от
        # сканеров, не знающих токен бота.
        return f"/telegram/webhook/{self.webhook_secret[:16]}"

    @property
    def webhook_url(self) -> str:
        return f"{self.public_url.rstrip('/')}{self.webhook_path}"


@lru_cache
def get_settings() -> Settings:
    """Кешированный синглтон настроек."""
    return Settings()  # type: ignore[call-arg]


# Удобный alias для импортов
settings = get_settings()
