"""Расчёты статистики: дашборд, тренды, разбивки по категориям."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Goal, Investment, Referral, Transaction, TransactionKind
from app.schemas.analytics import (
    CategoryBreakdown,
    DailyPoint,
    DashboardData,
    PeriodSummary,
)


class AnalyticsService:
    """Сервис аналитики. Все методы принимают user_id."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_balance(self, user_id: int) -> Decimal:
        """Расчётный баланс = сумма доходов − сумма расходов (по основной валюте).

        Замечание: пока считаем по всем валютам как если они одна.
        Полноценная мультивалютная конвертация — TODO следующего релиза.
        """
        income = await self._sum(user_id, TransactionKind.INCOME)
        expense = await self._sum(user_id, TransactionKind.EXPENSE)
        return income - expense

    async def _sum(
        self,
        user_id: int,
        kind: TransactionKind,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Decimal:
        conditions = [
            Transaction.user_id == user_id,
            Transaction.kind == kind,
            Transaction.deleted_at.is_(None),
        ]
        if start:
            conditions.append(Transaction.occurred_at >= start)
        if end:
            conditions.append(Transaction.occurred_at < end)

        stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(and_(*conditions))
        result = await self.db.execute(stmt)
        return Decimal(str(result.scalar() or 0))

    async def period_summary(
        self,
        user_id: int,
        start: date,
        end: date,
    ) -> PeriodSummary:
        """Сводка за период [start, end]."""
        start_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

        income = await self._sum(user_id, TransactionKind.INCOME, start_dt, end_dt)
        expense = await self._sum(user_id, TransactionKind.EXPENSE, start_dt, end_dt)

        # Разбивка по категориям
        expense_breakdown = await self._category_breakdown(
            user_id, TransactionKind.EXPENSE, start_dt, end_dt, expense
        )
        income_breakdown = await self._category_breakdown(
            user_id, TransactionKind.INCOME, start_dt, end_dt, income
        )

        # Количество транзакций
        count_stmt = select(func.count()).select_from(Transaction).where(
            and_(
                Transaction.user_id == user_id,
                Transaction.deleted_at.is_(None),
                Transaction.occurred_at >= start_dt,
                Transaction.occurred_at < end_dt,
            )
        )
        count_result = await self.db.execute(count_stmt)
        tx_count = int(count_result.scalar() or 0)

        return PeriodSummary(
            period_start=start,
            period_end=end,
            income_total=income,
            expense_total=expense,
            balance=income - expense,
            transaction_count=tx_count,
            by_category_expense=expense_breakdown,
            by_category_income=income_breakdown,
        )

    async def _category_breakdown(
        self,
        user_id: int,
        kind: TransactionKind,
        start: datetime,
        end: datetime,
        total: Decimal,
    ) -> list[CategoryBreakdown]:
        """Группировка сумм по категориям."""
        stmt = (
            select(
                Transaction.category_id,
                Category.name,
                Category.icon,
                Category.color,
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
                func.count().label("cnt"),
            )
            .join(Category, Category.id == Transaction.category_id, isouter=True)
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.kind == kind,
                    Transaction.deleted_at.is_(None),
                    Transaction.occurred_at >= start,
                    Transaction.occurred_at < end,
                )
            )
            .group_by(Transaction.category_id, Category.name, Category.icon, Category.color)
            .order_by(func.sum(Transaction.amount).desc())
        )
        rows = (await self.db.execute(stmt)).all()
        result = []
        for row in rows:
            cat_total = Decimal(str(row.total))
            percent = float(cat_total / total * 100) if total > 0 else 0.0
            result.append(
                CategoryBreakdown(
                    category_id=row.category_id,
                    category_name=row.name or "Без категории",
                    category_icon=row.icon or "❓",
                    category_color=row.color or "#888888",
                    total=cat_total,
                    count=int(row.cnt),
                    percent=round(percent, 2),
                )
            )
        return result

    async def daily_trend(self, user_id: int, days: int = 30) -> list[DailyPoint]:
        """Доход/расход по дням за последние N дней."""
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=days)

        # Группируем по дате (UTC)
        stmt = (
            select(
                func.date(Transaction.occurred_at).label("day"),
                Transaction.kind,
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            )
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.deleted_at.is_(None),
                    Transaction.occurred_at >= start_dt,
                )
            )
            .group_by(func.date(Transaction.occurred_at), Transaction.kind)
            .order_by(func.date(Transaction.occurred_at))
        )
        rows = (await self.db.execute(stmt)).all()

        # Заполняем все дни (даже пустые)
        by_day: dict[date, dict[str, Decimal]] = {}
        for i in range(days + 1):
            d = (start_dt + timedelta(days=i)).date()
            by_day[d] = {"income": Decimal("0"), "expense": Decimal("0")}

        for row in rows:
            d = row.day if isinstance(row.day, date) else date.fromisoformat(str(row.day))
            if d in by_day:
                by_day[d][row.kind.value] = Decimal(str(row.total))

        return [
            DailyPoint(day=d, income=v["income"], expense=v["expense"])
            for d, v in sorted(by_day.items())
        ]

    async def dashboard(self, user_id: int) -> DashboardData:
        """Полные данные для главного экрана Mini App."""
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        # Параллельно считать всё в одном запросе на каждый kind было бы быстрее,
        # но для ясности оставим так — нагрузка минимальна.
        balance = await self.get_balance(user_id)
        income_month = await self._sum(user_id, TransactionKind.INCOME, month_start)
        expense_month = await self._sum(user_id, TransactionKind.EXPENSE, month_start)

        tx_count_stmt = select(func.count()).select_from(Transaction).where(
            and_(Transaction.user_id == user_id, Transaction.deleted_at.is_(None))
        )
        tx_count = int((await self.db.execute(tx_count_stmt)).scalar() or 0)

        goals_stmt = select(func.count()).select_from(Goal).where(
            and_(
                Goal.user_id == user_id,
                Goal.deleted_at.is_(None),
                Goal.status == "active",
            )
        )
        active_goals = int((await self.db.execute(goals_stmt)).scalar() or 0)

        inv_stmt = select(func.coalesce(func.sum(
            func.coalesce(Investment.current_value, Investment.purchase_amount)
        ), 0)).where(
            and_(Investment.user_id == user_id, Investment.deleted_at.is_(None))
        )
        investments_value = Decimal(str((await self.db.execute(inv_stmt)).scalar() or 0))

        ref_stmt = select(func.count()).select_from(Referral).where(
            Referral.referrer_user_id == user_id
        )
        ref_count = int((await self.db.execute(ref_stmt)).scalar() or 0)

        trend = await self.daily_trend(user_id, days=30)
        top_expenses = await self._category_breakdown(
            user_id, TransactionKind.EXPENSE, month_start, now + timedelta(days=1), expense_month
        )

        return DashboardData(
            balance=balance,
            income_this_month=income_month,
            expense_this_month=expense_month,
            transactions_count=tx_count,
            active_goals_count=active_goals,
            investments_total_value=investments_value,
            referrals_count=ref_count,
            last_30_days_trend=trend,
            top_expense_categories=top_expenses[:5],
        )
