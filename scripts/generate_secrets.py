#!/usr/bin/env python
"""Генератор криптографически стойких секретов для .env

Использование:
    python scripts/generate_secrets.py
"""
import secrets


def main() -> None:
    print("\n🔐 Сгенерированные секреты для .env (скопируй):\n")
    print(f"WEBHOOK_SECRET={secrets.token_urlsafe(32)}")
    print(f"JWT_SECRET={secrets.token_urlsafe(32)}")
    print()
    print("⚠️  ВАЖНО: эти значения нужно вставить в .env (или в переменные окружения")
    print("    хостинга — Render/Koyeb), но НЕ КОММИТИТЬ в git.\n")


if __name__ == "__main__":
    main()
