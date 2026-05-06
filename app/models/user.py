"""Модель пользователя. Привязка через telegram_id."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPK, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.goal import Goal
    from app.models.investment import Investment
    from app.models.referral import Referral
    from app.models.transaction import Transaction


class User(Base, IntPK, TimestampMixin, SoftDeleteMixin):
    """Пользователь финансового трекера.

    Создаётся автоматически при первом обращении бота через valid Telegram initData.
    """

    # Telegram-специфичные поля
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Настройки пользователя
    base_currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow", nullable=False)

    # Реферальная система
    referral_code: Mapped[str | None] = mapped_column(String(16), unique=True, nullable=True, index=True)
    referred_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)

    # Уведомления
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Связи
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    categories: Mapped[list["Category"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    goals: Mapped[list["Goal"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    investments: Mapped[list["Investment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    referrals_made: Mapped[list["Referral"]] = relationship(
        "Referral",
        foreign_keys="Referral.referrer_user_id",
        back_populates="referrer",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_users_telegram_id_active", "telegram_id", postgresql_where="deleted_at IS NULL"),
    )

    @property
    def display_name(self) -> str:
        """Человекочитаемое имя для UI."""
        if self.first_name:
            full = self.first_name
            if self.last_name:
                full += f" {self.last_name}"
            return full
        if self.username:
            return f"@{self.username}"
        return f"user_{self.telegram_id}"

    def __repr__(self) -> str:
        return f"<User id={self.id} tg={self.telegram_id} name={self.display_name!r}>"
