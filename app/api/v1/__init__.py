"""Роутер API v1 — собирает все эндпойнты в один pre-fixed роутер."""
from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    auth,
    categories,
    export,
    goals,
    investments,
    referrals,
    transactions,
    users,
)

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(transactions.router)
api_v1_router.include_router(categories.router)
api_v1_router.include_router(goals.router)
api_v1_router.include_router(investments.router)
api_v1_router.include_router(analytics.router)
api_v1_router.include_router(export.router)
api_v1_router.include_router(referrals.router)
