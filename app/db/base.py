"""Базовый класс ORM-моделей с общими mixin'ами."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import BigInteger, DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

# Единое соглашение об именовании ключей/индексов — нужно для Alembic
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Корень всех моделей."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        # CamelCase → snake_case, плюс множественное число.
        # Например: TransactionItem → transaction_items
        import re

        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        if not name.endswith("s"):
            name += "s"
        return name


def utcnow() -> datetime:
    """Текущее время в UTC. Используется как default для timestamp колонок."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Добавляет created_at и updated_at. Всегда TIMESTAMPTZ."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=__import__("sqlalchemy").text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=__import__("sqlalchemy").text("CURRENT_TIMESTAMP"),
    )


class SoftDeleteMixin:
    """Soft delete: удаление = просто заполняем deleted_at."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class IntPK:
    """BigInteger primary key — на случай миллионов транзакций."""

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
