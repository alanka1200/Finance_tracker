"""Pydantic-схемы для API."""
from app.schemas.analytics import (
    AdviceResponse,
    CategoryBreakdown,
    DailyPoint,
    DashboardData,
    PeriodSummary,
    TrendData,
)
from app.schemas.finance import (
    CategoryCreate,
    CategoryPublic,
    CategoryUpdate,
    GoalContribution,
    GoalCreate,
    GoalPublic,
    GoalUpdate,
    InvestmentCreate,
    InvestmentPublic,
    InvestmentUpdate,
)
from app.schemas.transaction import (
    TransactionCreate,
    TransactionList,
    TransactionPublic,
    TransactionUpdate,
)
from app.schemas.user import (
    AuthResponse,
    RefreshRequest,
    RefreshResponse,
    UserPublic,
    UserUpdate,
)

__all__ = [
    "AdviceResponse",
    "AuthResponse",
    "CategoryBreakdown",
    "CategoryCreate",
    "CategoryPublic",
    "CategoryUpdate",
    "DailyPoint",
    "DashboardData",
    "GoalContribution",
    "GoalCreate",
    "GoalPublic",
    "GoalUpdate",
    "InvestmentCreate",
    "InvestmentPublic",
    "InvestmentUpdate",
    "PeriodSummary",
    "RefreshRequest",
    "RefreshResponse",
    "TransactionCreate",
    "TransactionList",
    "TransactionPublic",
    "TransactionUpdate",
    "TrendData",
    "UserPublic",
    "UserUpdate",
]
