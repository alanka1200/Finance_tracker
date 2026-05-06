"""Модель финансовой цели."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPK, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class GoalStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class GoalPriority(int, Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class Goal(Base, IntPK, TimestampMixin, SoftDeleteMixin):
    """Финансовая цель — копим на машину, путешествие, инвестиции и т.д."""

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)

    target_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(
        Numeric(19, 4), default=Decimal("0"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(8), default="RUB", nullable=False)

    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    category_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    icon: Mapped[str] = mapped_column(String(8), default="🎯", nullable=False)

    priority: Mapped[GoalPriority] = mapped_column(
        SAEnum(GoalPriority, name="goal_priority"),
        default=GoalPriority.MEDIUM,
        nullable=False,
    )
    status: Mapped[GoalStatus] = mapped_column(
        SAEnum(GoalStatus, name="goal_status"),
        default=GoalStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # Связи
    user: Mapped["User"] = relationship(back_populates="goals")

    __table_args__ = (
        Index(
            "ix_goals_user_status_active",
            "user_id",
            "status",
            postgresql_where="deleted_at IS NULL",
        ),
    )

    @property
    def progress_percent(self) -> float:
        """Процент выполнения (0–100)."""
        if self.target_amount <= 0:
            return 0.0
        pct = float(self.current_amount / self.target_amount * 100)
        return max(0.0, min(100.0, pct))

    @property
    def remaining(self) -> Decimal:
        return max(Decimal("0"), self.target_amount - self.current_amount)

    def __repr__(self) -> str:
        return f"<Goal {self.title!r} {self.progress_percent:.0f}%>"
