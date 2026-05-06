"""Бизнес-логика транзакций."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import utcnow
from app.models import Category, Transaction, TransactionKind
from app.schemas.transaction import (
    TransactionCreate,
    TransactionList,
    TransactionPublic,
    TransactionUpdate,
)


class TransactionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, user_id: int, data: TransactionCreate) -> Transaction:
        """Создаёт транзакцию. Проверяет, что category принадлежит пользователю."""
        if data.category_id is not None:
            cat_stmt = select(Category).where(
                Category.id == data.category_id,
                Category.user_id == user_id,
                Category.deleted_at.is_(None),
            )
            category = (await self.db.execute(cat_stmt)).scalar_one_or_none()
            if not category:
                raise ValueError("Категория не найдена")
            # Проверим, что тип категории матчится с типом транзакции
            if category.kind.value != data.kind.value:
                raise ValueError(
                    f"Тип категории ({category.kind.value}) не совпадает с типом транзакции ({data.kind.value})"
                )

        tx = Transaction(
            user_id=user_id,
            kind=data.kind,
            amount=data.amount,
            currency=data.currency,
            category_id=data.category_id,
            description=data.description,
            tags=data.tags,
            occurred_at=data.occurred_at or utcnow(),
        )
        self.db.add(tx)
        await self.db.flush()
        logger.info("Транзакция создана: user={} {}", user_id, tx)
        return tx

    async def get(self, user_id: int, tx_id: int) -> Transaction | None:
        stmt = (
            select(Transaction)
            .where(
                Transaction.id == tx_id,
                Transaction.user_id == user_id,
                Transaction.deleted_at.is_(None),
            )
            .options(selectinload(Transaction.category))
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def update(
        self, user_id: int, tx_id: int, data: TransactionUpdate
    ) -> Transaction | None:
        tx = await self.get(user_id, tx_id)
        if not tx:
            return None

        update_dict = data.model_dump(exclude_none=True)

        # Проверка категории
        if "category_id" in update_dict and update_dict["category_id"] is not None:
            cat_stmt = select(Category).where(
                Category.id == update_dict["category_id"],
                Category.user_id == user_id,
                Category.deleted_at.is_(None),
            )
            if not (await self.db.execute(cat_stmt)).scalar_one_or_none():
                raise ValueError("Категория не найдена")

        for k, v in update_dict.items():
            setattr(tx, k, v)
        await self.db.flush()
        return tx

    async def delete(self, user_id: int, tx_id: int) -> bool:
        """Soft-delete: ставим deleted_at."""
        tx = await self.get(user_id, tx_id)
        if not tx:
            return False
        tx.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    async def list(  # noqa: A003 - "list" имя метода ок
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        kind: TransactionKind | None = None,
        category_id: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        amount_min: Decimal | None = None,
        amount_max: Decimal | None = None,
        search: str | None = None,
    ) -> TransactionList:
        """Список с фильтрами и пагинацией."""
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        conditions = [
            Transaction.user_id == user_id,
            Transaction.deleted_at.is_(None),
        ]
        if kind:
            conditions.append(Transaction.kind == kind)
        if category_id:
            conditions.append(Transaction.category_id == category_id)
        if start_date:
            conditions.append(Transaction.occurred_at >= start_date)
        if end_date:
            conditions.append(Transaction.occurred_at <= end_date)
        if amount_min is not None:
            conditions.append(Transaction.amount >= amount_min)
        if amount_max is not None:
            conditions.append(Transaction.amount <= amount_max)
        if search:
            search_pattern = f"%{search.lower()}%"
            conditions.append(func.lower(Transaction.description).like(search_pattern))

        # Считаем total
        count_stmt = select(func.count()).select_from(Transaction).where(and_(*conditions))
        total = int((await self.db.execute(count_stmt)).scalar() or 0)

        # Получаем страницу
        offset = (page - 1) * page_size
        stmt = (
            select(Transaction)
            .where(and_(*conditions))
            .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
            .options(selectinload(Transaction.category))
            .offset(offset)
            .limit(page_size)
        )
        rows = (await self.db.execute(stmt)).scalars().all()

        items = [
            TransactionPublic(
                id=tx.id,
                user_id=tx.user_id,
                kind=tx.kind,
                amount=tx.amount,
                currency=tx.currency,
                category_id=tx.category_id,
                category_name=tx.category.name if tx.category else None,
                category_icon=tx.category.icon if tx.category else None,
                category_color=tx.category.color if tx.category else None,
                description=tx.description,
                tags=tx.tags,
                occurred_at=tx.occurred_at,
                created_at=tx.created_at,
            )
            for tx in rows
        ]

        return TransactionList(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=offset + len(items) < total,
        )
