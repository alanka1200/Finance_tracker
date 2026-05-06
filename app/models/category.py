"""Модель категории доходов/расходов."""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SAEnum

from app.db.base import Base, IntPK, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.user import User


class CategoryKind(str, Enum):
    """Тип категории."""

    INCOME = "income"
    EXPENSE = "expense"


class Category(Base, IntPK, TimestampMixin, SoftDeleteMixin):
    """Категория транзакции. Бывает кастомная или системная (предзаданная)."""

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[CategoryKind] = mapped_column(
        SAEnum(CategoryKind, name="category_kind"),
        nullable=False,
        index=True,
    )

    # Эмодзи или иконка для UI
    icon: Mapped[str] = mapped_column(String(8), default="💰", nullable=False)
    # Hex цвет: #RRGGBB
    color: Mapped[str] = mapped_column(String(7), default="#40a7e3", nullable=False)

    # Системная категория не редактируется пользователем
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)

    # Связи
    user: Mapped["User"] = relationship(back_populates="categories")
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="category",
        foreign_keys="Transaction.category_id",
    )

    __table_args__ = (
        Index(
            "ix_categories_user_kind_active",
            "user_id",
            "kind",
            postgresql_where="deleted_at IS NULL",
        ),
    )

    def __repr__(self) -> str:
        return f"<Category {self.icon} {self.name} ({self.kind.value})>"


# Дефолтные категории — создаются автоматически при регистрации пользователя.
DEFAULT_CATEGORIES: list[dict[str, str | CategoryKind]] = [
    # Доходы
    {"name": "Зарплата", "kind": CategoryKind.INCOME, "icon": "💼", "color": "#4CAF50"},
    {"name": "Фриланс", "kind": CategoryKind.INCOME, "icon": "💻", "color": "#8BC34A"},
    {"name": "Подарки", "kind": CategoryKind.INCOME, "icon": "🎁", "color": "#CDDC39"},
    {"name": "Инвестиции", "kind": CategoryKind.INCOME, "icon": "📈", "color": "#009688"},
    {"name": "Прочее", "kind": CategoryKind.INCOME, "icon": "💵", "color": "#4DB6AC"},
    # Расходы
    {"name": "Продукты", "kind": CategoryKind.EXPENSE, "icon": "🛒", "color": "#F44336"},
    {"name": "Кафе", "kind": CategoryKind.EXPENSE, "icon": "🍔", "color": "#FF5722"},
    {"name": "Транспорт", "kind": CategoryKind.EXPENSE, "icon": "🚗", "color": "#FF9800"},
    {"name": "Жильё", "kind": CategoryKind.EXPENSE, "icon": "🏠", "color": "#FFC107"},
    {"name": "Здоровье", "kind": CategoryKind.EXPENSE, "icon": "💊", "color": "#E91E63"},
    {"name": "Развлечения", "kind": CategoryKind.EXPENSE, "icon": "🎮", "color": "#9C27B0"},
    {"name": "Одежда", "kind": CategoryKind.EXPENSE, "icon": "👕", "color": "#673AB7"},
    {"name": "Связь", "kind": CategoryKind.EXPENSE, "icon": "📱", "color": "#3F51B5"},
    {"name": "Образование", "kind": CategoryKind.EXPENSE, "icon": "📚", "color": "#2196F3"},
    {"name": "Прочее", "kind": CategoryKind.EXPENSE, "icon": "💸", "color": "#607D8B"},
]
