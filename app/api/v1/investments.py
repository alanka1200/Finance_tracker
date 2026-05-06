"""API инвестиций."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DbSession
from app.schemas.finance import (
    InvestmentCreate,
    InvestmentPublic,
    InvestmentUpdate,
)
from app.services.investments import InvestmentService

router = APIRouter(prefix="/investments", tags=["investments"])


def _to_public(inv) -> InvestmentPublic:  # type: ignore[no-untyped-def]
    return InvestmentPublic(
        id=inv.id,
        type=inv.type,
        name=inv.name,
        ticker=inv.ticker,
        purchase_amount=inv.purchase_amount,
        quantity=inv.quantity,
        purchase_price=inv.purchase_price,
        purchase_date=inv.purchase_date,
        current_price=inv.current_price,
        current_value=inv.current_value,
        currency=inv.currency,
        notes=inv.notes,
        profit_loss=inv.profit_loss,
        profit_loss_percent=inv.profit_loss_percent,
        created_at=inv.created_at,
    )


@router.get("", response_model=list[InvestmentPublic])
async def list_investments(
    user: CurrentUser, db: DbSession
) -> list[InvestmentPublic]:
    svc = InvestmentService(db)
    items = await svc.list(user.id)
    return [_to_public(i) for i in items]


@router.post("", response_model=InvestmentPublic, status_code=status.HTTP_201_CREATED)
async def create_investment(
    user: CurrentUser, db: DbSession, data: InvestmentCreate
) -> InvestmentPublic:
    svc = InvestmentService(db)
    inv = await svc.create(user.id, data)
    await db.commit()
    return _to_public(inv)


@router.patch("/{inv_id}", response_model=InvestmentPublic)
async def update_investment(
    user: CurrentUser, db: DbSession, inv_id: int, data: InvestmentUpdate
) -> InvestmentPublic:
    svc = InvestmentService(db)
    inv = await svc.update(user.id, inv_id, data)
    if not inv:
        raise HTTPException(status_code=404, detail="инвестиция не найдена")
    await db.commit()
    return _to_public(inv)


@router.delete("/{inv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_investment(
    user: CurrentUser, db: DbSession, inv_id: int
) -> None:
    svc = InvestmentService(db)
    if not await svc.delete(user.id, inv_id):
        raise HTTPException(status_code=404, detail="инвестиция не найдена")
    await db.commit()
