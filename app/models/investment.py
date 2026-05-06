"""Модель инвестиции — портфельная позиция."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPK, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class InvestmentType(str, Enum):
    STOCK = "stock"
    BOND = "bond"
    CRYPTO = "crypto"
    DEPOSIT = "deposit"
    REAL_ESTATE = "real_estate"
    OTHER = "other"


class Investment(Base, IntPK, TimestampMixin, SoftDeleteMixin):
    """Инвестиция/актив в портфеле пользователя."""

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type: Mapped[InvestmentType] = mapped_column(
        SAEnum(InvestmentType, name="investment_type"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    # Покупка
    purchase_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(19, 8), default=Decimal("1"), nullable=False)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(19, 8), nullable=True)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Текущая стоимость (обновляется фоновой задачей по market data API)
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(19, 8), nullable=True)
    current_value: Mapped[Decimal | None] = mapped_column(Numeric(19, 4), nullable=True)

    currency: Mapped[str] = mapped_column(String(8), default="RUB", nullable=False)
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Связи
    user: Mapped["User"] = relationship(back_populates="investments")

    __table_args__ = (
        Index(
            "ix_investments_user_active",
            "user_id",
            postgresql_where="deleted_at IS NULL",
        ),
    )

    @property
    def profit_loss(self) -> Decimal:
        """Прибыль/убыток в абсолютном значении."""
        if self.current_value is None:
            return Decimal("0")
        return self.current_value - self.purchase_amount

    @property
    def profit_loss_percent(self) -> float:
        if self.purchase_amount <= 0 or self.current_value is None:
            return 0.0
        return float((self.current_value - self.purchase_amount) / self.purchase_amount * 100)

    def __repr__(self) -> str:
        return f"<Investment {self.type.value} {self.name!r} {self.purchase_amount}>"
