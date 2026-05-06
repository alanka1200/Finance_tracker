"""Бизнес-логика категорий."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, CategoryKind
from app.schemas.finance import CategoryCreate, CategoryUpdate


class CategoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, user_id: int, kind: CategoryKind | None = None
    ) -> list[Category]:
        conditions = [Category.user_id == user_id, Category.deleted_at.is_(None)]
        if kind:
            conditions.append(Category.kind == kind)
        stmt = (
            select(Category)
            .where(*conditions)
            .order_by(Category.sort_order.asc(), Category.id.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create(self, user_id: int, data: CategoryCreate) -> Category:
        cat = Category(
            user_id=user_id,
            name=data.name,
            kind=data.kind,
            icon=data.icon,
            color=data.color,
            sort_order=data.sort_order,
            is_system=False,
        )
        self.db.add(cat)
        await self.db.flush()
        return cat

    async def get(self, user_id: int, cat_id: int) -> Category | None:
        stmt = select(Category).where(
            Category.id == cat_id,
            Category.user_id == user_id,
            Category.deleted_at.is_(None),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def update(
        self, user_id: int, cat_id: int, data: CategoryUpdate
    ) -> Category | None:
        cat = await self.get(user_id, cat_id)
        if not cat:
            return None
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(cat, k, v)
        await self.db.flush()
        return cat

    async def delete(self, user_id: int, cat_id: int) -> bool:
        """Soft delete. Системные категории удалять можно — это не сломает старые транзакции,
        потому что у транзакций category_id FK с ON DELETE SET NULL."""
        cat = await self.get(user_id, cat_id)
        if not cat:
            return False
        cat.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True
