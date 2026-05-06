"""API транзакций."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import CurrentUser, DbSession
from app.models.transaction import TransactionKind
from app.schemas.transaction import (
    TransactionCreate,
    TransactionList,
    TransactionPublic,
    TransactionUpdate,
)
from app.services.transactions import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionList)
async def list_transactions(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    kind: TransactionKind | None = None,
    category_id: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    amount_min: Decimal | None = None,
    amount_max: Decimal | None = None,
    search: str | None = None,
) -> TransactionList:
    """Список транзакций с фильтрами и пагинацией."""
    svc = TransactionService(db)
    return await svc.list(
        user_id=user.id,
        page=page,
        page_size=page_size,
        kind=kind,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        amount_min=amount_min,
        amount_max=amount_max,
        search=search,
    )


@router.post("", response_model=TransactionPublic, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    user: CurrentUser,
    db: DbSession,
    data: TransactionCreate,
) -> TransactionPublic:
    """Создаёт новую транзакцию."""
    svc = TransactionService(db)
    try:
        tx = await svc.create(user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await db.commit()
    await db.refresh(tx, attribute_names=["category"])

    return TransactionPublic(
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


@router.get("/{tx_id}", response_model=TransactionPublic)
async def get_transaction(
    user: CurrentUser, db: DbSession, tx_id: int
) -> TransactionPublic:
    svc = TransactionService(db)
    tx = await svc.get(user.id, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="транзакция не найдена")
    return TransactionPublic(
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


@router.patch("/{tx_id}", response_model=TransactionPublic)
async def update_transaction(
    user: CurrentUser,
    db: DbSession,
    tx_id: int,
    data: TransactionUpdate,
) -> TransactionPublic:
    svc = TransactionService(db)
    try:
        tx = await svc.update(user.id, tx_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not tx:
        raise HTTPException(status_code=404, detail="транзакция не найдена")
    await db.commit()
    await db.refresh(tx, attribute_names=["category"])
    return TransactionPublic(
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


@router.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    user: CurrentUser, db: DbSession, tx_id: int
):
    svc = TransactionService(db)
    deleted = await svc.delete(user.id, tx_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="транзакция не найдена")
    await db.commit()
    return None
