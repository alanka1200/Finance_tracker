"""API экспорта данных в CSV / JSON."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.deps import CurrentUser, DbSession
from app.models import Goal, Investment, Transaction

router = APIRouter(prefix="/export", tags=["export"])


def _serialize_value(v):  # type: ignore[no-untyped-def]
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if hasattr(v, "value"):  # Enum
        return v.value
    return v


@router.get("/transactions.csv")
async def export_transactions_csv(
    user: CurrentUser, db: DbSession
) -> StreamingResponse:
    """Все транзакции пользователя в CSV. UTF-8 with BOM (для Excel)."""
    stmt = (
        select(Transaction)
        .where(Transaction.user_id == user.id, Transaction.deleted_at.is_(None))
        .options(selectinload(Transaction.category))
        .order_by(Transaction.occurred_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()

    output = io.StringIO()
    output.write("\ufeff")  # BOM для Excel
    writer = csv.writer(output, delimiter=";")  # ; — стандарт для русского Excel
    writer.writerow(
        ["ID", "Дата", "Тип", "Категория", "Сумма", "Валюта", "Описание", "Теги"]
    )
    for tx in rows:
        writer.writerow(
            [
                tx.id,
                tx.occurred_at.isoformat(),
                "Доход" if tx.kind.value == "income" else "Расход",
                tx.category.name if tx.category else "",
                str(tx.amount),
                tx.currency,
                tx.description or "",
                tx.tags or "",
            ]
        )
    output.seek(0)

    fname = f"transactions_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/full.json")
async def export_full_json(user: CurrentUser, db: DbSession) -> StreamingResponse:
    """Полный дамп пользовательских данных в JSON."""
    tx_stmt = (
        select(Transaction)
        .where(Transaction.user_id == user.id, Transaction.deleted_at.is_(None))
        .options(selectinload(Transaction.category))
        .order_by(Transaction.occurred_at.desc())
    )
    txs = (await db.execute(tx_stmt)).scalars().all()

    goals_stmt = select(Goal).where(Goal.user_id == user.id, Goal.deleted_at.is_(None))
    goals = (await db.execute(goals_stmt)).scalars().all()

    inv_stmt = select(Investment).where(
        Investment.user_id == user.id, Investment.deleted_at.is_(None)
    )
    invs = (await db.execute(inv_stmt)).scalars().all()

    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "base_currency": user.base_currency,
            "referral_code": user.referral_code,
        },
        "transactions": [
            {
                "id": t.id,
                "kind": t.kind.value,
                "amount": str(t.amount),
                "currency": t.currency,
                "category": t.category.name if t.category else None,
                "description": t.description,
                "tags": t.tags,
                "occurred_at": t.occurred_at.isoformat(),
            }
            for t in txs
        ],
        "goals": [
            {
                "id": g.id,
                "title": g.title,
                "target_amount": str(g.target_amount),
                "current_amount": str(g.current_amount),
                "currency": g.currency,
                "deadline": g.deadline.isoformat() if g.deadline else None,
                "status": g.status.value,
            }
            for g in goals
        ],
        "investments": [
            {
                "id": i.id,
                "type": i.type.value,
                "name": i.name,
                "ticker": i.ticker,
                "purchase_amount": str(i.purchase_amount),
                "quantity": str(i.quantity),
                "purchase_date": i.purchase_date.isoformat(),
                "current_value": str(i.current_value) if i.current_value else None,
                "currency": i.currency,
            }
            for i in invs
        ],
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    fname = f"finance_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    return StreamingResponse(
        iter([body]),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
