"""Обработчики команд и сообщений бота."""
from __future__ import annotations

from loguru import logger
from sqlalchemy import func, select
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.config import settings
from app.db.session import SessionLocal
from app.models import Goal, Transaction, User
from app.services.users import get_or_create_user
from app.services.telegram_auth import TelegramUser


def _make_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура с кнопкой запуска Mini App."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📱 Открыть приложение",
                    web_app=WebAppInfo(url=settings.frontend_url),
                )
            ],
            [
                InlineKeyboardButton("📊 Статистика", callback_data="stats"),
                InlineKeyboardButton("ℹ️ О боте", callback_data="about"),
            ],
        ]
    )


WELCOME_TEXT = (
    "👋 *Привет\\! Я — твой персональный финансовый трекер\\.*\n\n"
    "🎯 С моей помощью ты сможешь:\n"
    "• Учитывать доходы и расходы\n"
    "• Ставить финансовые цели\n"
    "• Анализировать привычки трат\n"
    "• Управлять инвестиционным портфелем\n"
    "• Получать персональные советы\n\n"
    "👇 *Нажми кнопку ниже, чтобы начать\\:*"
)

HELP_TEXT = (
    "🤖 *Доступные команды:*\n\n"
    "/start — открыть приложение\n"
    "/stats — твоя краткая статистика\n"
    "/help — это сообщение\n"
    "/about — о боте\n\n"
    "💡 *Совет:* основная работа происходит в Mini App\\. "
    "Просто нажми кнопку «📱 Открыть приложение»\\!"
)

ABOUT_TEXT = (
    "💼 *Финансовый Трекер*\n\n"
    "Бесплатное приложение для управления личными финансами\\.\n\n"
    "🔒 Твои данные защищены\n"
    "📊 Красивая аналитика\n"
    "🎯 Достижение целей\n"
    "📈 Инвестиционный портфель\n"
    "🤖 AI\\-советы\n\n"
    "Сделано с ❤️ для тех, кто хочет финансовую свободу\\."
)


async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start. Регистрирует пользователя при первом обращении."""
    if not update.effective_user or not update.message:
        return

    tg_user = TelegramUser(
        id=update.effective_user.id,
        first_name=update.effective_user.first_name,
        last_name=update.effective_user.last_name,
        username=update.effective_user.username,
        language_code=update.effective_user.language_code,
        is_premium=getattr(update.effective_user, "is_premium", False) or False,
    )

    # Проверяем start parameter (для рефералки): /start ABC123XY
    referral_param = None
    if context.args:
        referral_param = context.args[0]
        logger.info("Старт через рефералку: {} → {}", referral_param, tg_user.id)

    async with SessionLocal() as db:
        try:
            user, created = await get_or_create_user(db, tg_user, referral_param)
            await db.commit()
        except Exception as e:
            logger.exception("Не удалось создать пользователя: {}", e)
            await update.message.reply_text(
                "Извини, что-то пошло не так. Попробуй ещё раз через минуту."
            )
            return

    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=_make_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    if created:
        logger.info("Новый пользователь через бота: {}", user)


async def on_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN_V2)


async def on_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        ABOUT_TEXT,
        reply_markup=_make_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def on_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Краткая статистика без Mini App."""
    if not update.effective_user or not update.message:
        return

    tg_id = update.effective_user.id
    async with SessionLocal() as db:
        user_stmt = select(User).where(User.telegram_id == tg_id, User.deleted_at.is_(None))
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        if not user:
            await update.message.reply_text(
                "Сначала запусти приложение командой /start 😊"
            )
            return

        tx_count_stmt = select(func.count()).select_from(Transaction).where(
            Transaction.user_id == user.id, Transaction.deleted_at.is_(None)
        )
        tx_count = int((await db.execute(tx_count_stmt)).scalar() or 0)

        goals_count_stmt = select(func.count()).select_from(Goal).where(
            Goal.user_id == user.id,
            Goal.deleted_at.is_(None),
            Goal.status == "active",
        )
        goals_count = int((await db.execute(goals_count_stmt)).scalar() or 0)

    text = (
        f"📊 *Твоя статистика:*\n\n"
        f"💰 Транзакций: *{tx_count}*\n"
        f"🎯 Активных целей: *{goals_count}*\n\n"
        f"_Подробности — в приложении\\!_"
    )
    await update.message.reply_text(
        text,
        reply_markup=_make_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Любое текстовое сообщение → дружелюбное напоминание про Mini App."""
    if not update.message:
        return
    await update.message.reply_text(
        "💡 Все действия удобнее выполнять в приложении 👇",
        reply_markup=_make_main_keyboard(),
    )
