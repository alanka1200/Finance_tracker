"""API целей."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DbSession
from app.models.goal import GoalStatus
from app.schemas.finance import (
    GoalContribution,
    GoalCreate,
    GoalPublic,
    GoalUpdate,
)
from app.services.goals import GoalService

router = APIRouter(prefix="/goals", tags=["goals"])


def _to_public(goal) -> GoalPublic:  # type: ignore[no-untyped-def]
    return GoalPublic(
        id=goal.id,
        title=goal.title,
        description=goal.description,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        currency=goal.currency,
        deadline=goal.deadline,
        completed_at=goal.completed_at,
        category_label=goal.category_label,
        icon=goal.icon,
        priority=goal.priority,
        status=goal.status,
        progress_percent=goal.progress_percent,
        remaining=goal.remaining,
        created_at=goal.created_at,
    )


@router.get("", response_model=list[GoalPublic])
async def list_goals(
    user: CurrentUser, db: DbSession, status_filter: GoalStatus | None = None
) -> list[GoalPublic]:
    svc = GoalService(db)
    goals = await svc.list(user.id, status=status_filter)
    return [_to_public(g) for g in goals]


@router.post("", response_model=GoalPublic, status_code=status.HTTP_201_CREATED)
async def create_goal(
    user: CurrentUser, db: DbSession, data: GoalCreate
) -> GoalPublic:
    svc = GoalService(db)
    goal = await svc.create(user.id, data)
    await db.commit()
    return _to_public(goal)


@router.get("/{goal_id}", response_model=GoalPublic)
async def get_goal(user: CurrentUser, db: DbSession, goal_id: int) -> GoalPublic:
    svc = GoalService(db)
    goal = await svc.get(user.id, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="цель не найдена")
    return _to_public(goal)


@router.patch("/{goal_id}", response_model=GoalPublic)
async def update_goal(
    user: CurrentUser, db: DbSession, goal_id: int, data: GoalUpdate
) -> GoalPublic:
    svc = GoalService(db)
    goal = await svc.update(user.id, goal_id, data)
    if not goal:
        raise HTTPException(status_code=404, detail="цель не найдена")
    await db.commit()
    return _to_public(goal)


@router.post("/{goal_id}/contribute", response_model=GoalPublic)
async def contribute_to_goal(
    user: CurrentUser,
    db: DbSession,
    goal_id: int,
    data: GoalContribution,
) -> GoalPublic:
    """Пополнение цели."""
    svc = GoalService(db)
    goal = await svc.contribute(user.id, goal_id, data.amount)
    if not goal:
        raise HTTPException(status_code=404, detail="цель не найдена")
    await db.commit()
    return _to_public(goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(user: CurrentUser, db: DbSession, goal_id: int) -> None:
    svc = GoalService(db)
    if not await svc.delete(user.id, goal_id):
        raise HTTPException(status_code=404, detail="цель не найдена")
    await db.commit()
