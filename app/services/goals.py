"""Бизнес-логика финансовых целей."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Goal, GoalStatus
from app.schemas.finance import GoalCreate, GoalUpdate


class GoalService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, user_id: int, data: GoalCreate) -> Goal:
        goal = Goal(
            user_id=user_id,
            title=data.title,
            description=data.description,
            target_amount=data.target_amount,
            current_amount=data.current_amount,
            currency=data.currency,
            deadline=data.deadline,
            category_label=data.category_label,
            icon=data.icon,
            priority=data.priority,
        )
        self.db.add(goal)
        await self.db.flush()
        logger.info("Цель создана: user={} {}", user_id, goal)
        return goal

    async def get(self, user_id: int, goal_id: int) -> Goal | None:
        stmt = select(Goal).where(
            Goal.id == goal_id,
            Goal.user_id == user_id,
            Goal.deleted_at.is_(None),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list(
        self, user_id: int, status: GoalStatus | None = None
    ) -> list[Goal]:
        conditions = [Goal.user_id == user_id, Goal.deleted_at.is_(None)]
        if status:
            conditions.append(Goal.status == status)
        stmt = select(Goal).where(*conditions).order_by(
            Goal.priority.asc(), Goal.created_at.desc()
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def update(
        self, user_id: int, goal_id: int, data: GoalUpdate
    ) -> Goal | None:
        goal = await self.get(user_id, goal_id)
        if not goal:
            return None
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(goal, k, v)

        # Автоматическое завершение, если current >= target
        if goal.current_amount >= goal.target_amount and goal.status == GoalStatus.ACTIVE:
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = datetime.now(timezone.utc)
            logger.info("Цель {} достигнута! 🎉", goal.id)

        await self.db.flush()
        return goal

    async def delete(self, user_id: int, goal_id: int) -> bool:
        goal = await self.get(user_id, goal_id)
        if not goal:
            return False
        goal.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    async def contribute(
        self, user_id: int, goal_id: int, amount: Decimal
    ) -> Goal | None:
        """Пополняет цель."""
        goal = await self.get(user_id, goal_id)
        if not goal:
            return None
        goal.current_amount += amount
        if goal.current_amount >= goal.target_amount and goal.status == GoalStatus.ACTIVE:
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = datetime.now(timezone.utc)
            logger.info("Цель {} достигнута пополнением! 🎉", goal.id)
        await self.db.flush()
        return goal
