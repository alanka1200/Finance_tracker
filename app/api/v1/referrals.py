"""API реферальной системы."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.config import settings
from app.deps import CurrentUser, DbSession
from app.models import Referral


class ReferralStats(BaseModel):
    referral_code: str | None
    referral_url: str
    total_referred: int
    confirmed_referred: int


router = APIRouter(prefix="/referrals", tags=["referrals"])


@router.get("/me", response_model=ReferralStats)
async def my_referral_stats(user: CurrentUser, db: DbSession) -> ReferralStats:
    """Личная статистика по рефералам."""
    total_stmt = select(func.count()).select_from(Referral).where(
        Referral.referrer_user_id == user.id
    )
    total = int((await db.execute(total_stmt)).scalar() or 0)

    confirmed_stmt = select(func.count()).select_from(Referral).where(
        Referral.referrer_user_id == user.id,
        Referral.status == "confirmed",
    )
    confirmed = int((await db.execute(confirmed_stmt)).scalar() or 0)

    # Реферальный URL: t.me/<bot_username>?start=<code>
    # Обрабатываем без хардкода bot_username — можно сделать параметром в config.
    bot_username = settings.bot_token.split(":")[0]  # резервный fallback
    if user.referral_code:
        url = f"https://t.me/share/url?url=https://t.me/{bot_username}?start={user.referral_code}"
    else:
        url = ""

    return ReferralStats(
        referral_code=user.referral_code,
        referral_url=url,
        total_referred=total,
        confirmed_referred=confirmed,
    )
