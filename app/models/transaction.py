"""Модель транзакции — основная единица учёта."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPK, SoftDeleteMixin, TimestampMixin, utcnow

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.user import User


class TransactionKind(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class Transaction(Base, IntPK, TimestampMixin, SoftDeleteMixin):
    """Доход или расход."""

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    kind: Mapped[TransactionKind] = mapped_column(
        SAEnum(TransactionKind, name="transaction_kind"),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="RUB", nullable=False)

    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(256), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )

    # СВЯЗИ — с явным указанием foreign_keys, чтобы SQLAlchemy не путался
    user: Mapped["User"] = relationship(
        back_populates="transactions",
        foreign_keys=[user_id],
    )
    category: Mapped["Category | None"] = relationship(
        back_populates="transactions",
        foreign_keys=[category_id],
    )

    __table_args__ = (
        Index(
            "ix_transactions_user_date",
            "user_id",
            "occurred_at",
            postgresql_using="btree",
            postgresql_ops={"occurred_at": "DESC"},
            postgresql_where="deleted_at IS NULL",
        ),
        Index(
            "ix_transactions_user_category",
            "user_id",
            "category_id",
            "occurred_at",
            postgresql_ops={"occurred_at": "DESC"},
            postgresql_where="deleted_at IS NULL",
        ),
        Index(
            "ix_transactions_user_kind",
            "user_id",
            "kind",
            "occurred_at",
            postgresql_ops={"occurred_at": "DESC"},
            postgresql_where="deleted_at IS NULL",
        ),
    )

    def __repr__(self) -> str:
        sign = "+" if self.kind == TransactionKind.INCOME else "-"
        return f"<Tx {sign}{self.amount} {self.currency} cat={self.category_id}>"
