"""Бизнес-логика управления пользователями."""
from __future__ import annotations

import secrets
import string

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DEFAULT_CATEGORIES, Category, Referral, ReferralStatus, User
from app.services.telegram_auth import TelegramUser


def _generate_referral_code(length: int = 8) -> str:
    """Случайный реферальный код. Алфанумерик в верхнем регистре."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def get_or_create_user(
    db: AsyncSession,
    tg_user: TelegramUser,
    referral_start_param: str | None = None,
) -> tuple[User, bool]:
    """Возвращает (user, created). Если новый — создаёт + сидит дефолтные категории + регистрирует реферала.

    Параметры:
        db: async-сессия (коммит делает caller)
        tg_user: распарсенный Telegram-пользователь из initData
        referral_start_param: содержимое start_param (если запуск через ссылку с рефералкой)
    """
    # 1. Ищем существующего по telegram_id
    stmt = select(User).where(User.telegram_id == tg_user.id, User.deleted_at.is_(None))
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing:
        # Обновляем "живые" поля (имя могло измениться)
        existing.username = tg_user.username
        existing.first_name = tg_user.first_name
        existing.last_name = tg_user.last_name
        existing.language_code = tg_user.language_code
        existing.is_premium = tg_user.is_premium
        await db.flush()
        return existing, False

    # 2. Новый пользователь — создаём
    user = User(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
        language_code=tg_user.language_code,
        is_premium=tg_user.is_premium,
        referral_code=await _unique_referral_code(db),
    )
    db.add(user)
    await db.flush()  # получим user.id

    # 3. Сидим дефолтные категории
    for idx, c in enumerate(DEFAULT_CATEGORIES):
        cat = Category(
            user_id=user.id,
            name=str(c["name"]),
            kind=c["kind"],  # type: ignore[arg-type]
            icon=str(c["icon"]),
            color=str(c["color"]),
            is_system=True,
            sort_order=idx,
        )
        db.add(cat)

    # 4. Реферал (если запуск через ссылку tg.me/bot?start=ABCD1234)
    if referral_start_param:
        referrer = await _find_referrer(db, referral_start_param)
        if referrer and referrer.id != user.id:
            user.referred_by_user_id = referrer.id
            ref = Referral(
                referrer_user_id=referrer.id,
                referred_user_id=user.id,
                status=ReferralStatus.CONFIRMED,
            )
            db.add(ref)
            logger.info(
                "Реферал зарегистрирован: {} → {}", referrer.id, user.id
            )

    await db.flush()
    logger.info("Новый пользователь: id={} tg={} ref_code={}", user.id, user.telegram_id, user.referral_code)
    return user, True


async def _unique_referral_code(db: AsyncSession, max_attempts: int = 10) -> str:
    """Генерит код, проверяя уникальность."""
    for _ in range(max_attempts):
        code = _generate_referral_code()
        stmt = select(User).where(User.referral_code == code)
        if not (await db.execute(stmt)).scalar_one_or_none():
            return code
    # На крайний случай — увеличим длину
    return _generate_referral_code(length=12)


async def _find_referrer(db: AsyncSession, code: str) -> User | None:
    """Найти реферера по коду."""
    code = code.strip().upper()[:16]
    stmt = select(User).where(User.referral_code == code, User.deleted_at.is_(None))
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    return (await db.execute(stmt)).scalar_one_or_none()
