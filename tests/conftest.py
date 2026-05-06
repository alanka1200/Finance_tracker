"""Pytest конфигурация. Загружает фикстуры и устанавливает env-переменные для тестов."""
import os
import sys

# Путь к корню проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Минимально необходимые env-переменные для тестов (config.py их требует)
os.environ.setdefault("BOT_TOKEN", "1234567890:TESTAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
os.environ.setdefault("WEBHOOK_SECRET", "test_webhook_secret_at_least_16_chars_long")
os.environ.setdefault("PUBLIC_URL", "https://example.com")
os.environ.setdefault("FRONTEND_URL", "https://example.com")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test_jwt_secret_at_least_16_chars_long_too")
os.environ.setdefault("ENVIRONMENT", "test")
