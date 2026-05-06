"""Реферальная система."""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPK, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class ReferralStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"


class Referral(Base, IntPK, TimestampMixin):
    """Связь "пригласил-пригласили". Уникальность по referred_user_id
    предотвращает повторное начисление бонуса."""

    referrer_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referred_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[ReferralStatus] = mapped_column(
        SAEnum(ReferralStatus, name="referral_status"),
        default=ReferralStatus.PENDING,
        nullable=False,
    )

    # Один пользователь может быть приглашён только один раз.
    __table_args__ = (
        UniqueConstraint("referred_user_id", name="uq_referrals_referred_user_id"),
        Index("ix_referrals_referrer_status", "referrer_user_id", "status"),
    )

    # Связи
    referrer: Mapped["User"] = relationship(
        foreign_keys=[referrer_user_id], back_populates="referrals_made"
    )

    def __repr__(self) -> str:
        return f"<Referral {self.referrer_user_id} → {self.referred_user_id} ({self.status.value})>"
