# =============================================================
# Multi-stage Dockerfile для FastAPI + python-telegram-bot
# Лёгкий образ (~150 MB) с pinned Python и non-root user.
# =============================================================

# --- Stage 1: builder ---
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Системные пакеты для сборки asyncpg, cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# --- Stage 2: runtime ---
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/app/.local/bin:$PATH"

# Минимум зависимостей для рантайма
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root пользователь — критично для безопасности
RUN useradd --create-home --shell /bin/bash --uid 1000 app

WORKDIR /app
COPY --from=builder --chown=app:app /root/.local /home/app/.local
COPY --chown=app:app . /app

USER app

EXPOSE 8080

# Healthcheck для платформ хостинга
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Запуск: миграции при старте → uvicorn
# В production миграции лучше запускать отдельным шагом deploy pipeline'а,
# но для простоты на free-tier хостингах оставляем здесь.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
