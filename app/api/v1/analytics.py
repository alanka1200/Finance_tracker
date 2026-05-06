"""API аналитики и AI-советов."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Query

from app.deps import CurrentUser, DbSession
from app.schemas.analytics import AdviceResponse, DashboardData, PeriodSummary, TrendData
from app.services.advice_llm import generate_advice
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard(user: CurrentUser, db: DbSession) -> DashboardData:
    """Главный экран Mini App."""
    svc = AnalyticsService(db)
    return await svc.dashboard(user.id)


@router.get("/period", response_model=PeriodSummary)
async def get_period(
    user: CurrentUser,
    db: DbSession,
    start: date = Query(..., description="дата начала (включительно)"),
    end: date = Query(..., description="дата конца (включительно)"),
) -> PeriodSummary:
    """Сводка за произвольный период."""
    svc = AnalyticsService(db)
    return await svc.period_summary(user.id, start, end)


@router.get("/trend", response_model=TrendData)
async def get_trend(
    user: CurrentUser, db: DbSession, days: int = Query(30, ge=1, le=365)
) -> TrendData:
    """Тренд по дням за последние N дней."""
    svc = AnalyticsService(db)
    points = await svc.daily_trend(user.id, days=days)
    return TrendData(days=points)


@router.get("/advice", response_model=AdviceResponse)
async def get_advice(user: CurrentUser, db: DbSession) -> AdviceResponse:
    """AI/правило-ориентированный совет."""
    svc = AnalyticsService(db)
    dashboard = await svc.dashboard(user.id)
    return await generate_advice(dashboard)
