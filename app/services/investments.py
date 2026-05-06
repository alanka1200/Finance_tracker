"""Бизнес-логика инвестиций."""
from __future__ import annotations

from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Investment
from app.schemas.finance import InvestmentCreate, InvestmentUpdate


class InvestmentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, user_id: int, data: InvestmentCreate) -> Investment:
        inv = Investment(
            user_id=user_id,
            type=data.type,
            name=data.name,
            ticker=data.ticker.upper() if data.ticker else None,
            purchase_amount=data.purchase_amount,
            quantity=data.quantity,
            purchase_price=data.purchase_price,
            purchase_date=data.purchase_date,
            currency=data.currency,
            notes=data.notes,
            current_value=data.purchase_amount,  # стартуем с цены покупки
        )
        self.db.add(inv)
        await self.db.flush()
        logger.info("Инвестиция создана: user={} {}", user_id, inv)
        return inv

    async def get(self, user_id: int, inv_id: int) -> Investment | None:
        stmt = select(Investment).where(
            Investment.id == inv_id,
            Investment.user_id == user_id,
            Investment.deleted_at.is_(None),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list(self, user_id: int) -> list[Investment]:
        stmt = (
            select(Investment)
            .where(Investment.user_id == user_id, Investment.deleted_at.is_(None))
            .order_by(Investment.purchase_date.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def update(
        self, user_id: int, inv_id: int, data: InvestmentUpdate
    ) -> Investment | None:
        inv = await self.get(user_id, inv_id)
        if not inv:
            return None

        update_dict = data.model_dump(exclude_none=True)
        if "ticker" in update_dict and update_dict["ticker"]:
            update_dict["ticker"] = str(update_dict["ticker"]).upper()

        for k, v in update_dict.items():
            setattr(inv, k, v)

        # Если обновили current_price, пересчитываем current_value
        if "current_price" in update_dict and inv.current_price:
            inv.current_value = inv.current_price * inv.quantity

        await self.db.flush()
        return inv

    async def delete(self, user_id: int, inv_id: int) -> bool:
        inv = await self.get(user_id, inv_id)
        if not inv:
            return False
        inv.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True
