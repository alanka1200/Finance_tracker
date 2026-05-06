"""Аутентификация: Telegram initData → JWT."""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, status
from loguru import logger

from app.core.security import create_access_token, create_refresh_token, decode_token
from app.deps import DbSession
from app.schemas.user import AuthResponse, RefreshRequest, RefreshResponse, UserPublic
from app.services.telegram_auth import InvalidInitDataError, validate_init_data
from app.services.users import get_or_create_user, get_user_by_id

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram", response_model=AuthResponse)
async def auth_telegram(
    db: DbSession,
    init_data: str = Body(..., embed=True, description="window.Telegram.WebApp.initData"),
) -> AuthResponse:
    """Обмен Telegram initData на JWT токены.

    Mini App при старте получает initData → POST /auth/telegram → access + refresh.
    Все последующие запросы — с Authorization: Bearer <access>.
    """
    try:
        parsed = validate_init_data(init_data)
    except InvalidInitDataError as e:
        logger.warning("Невалидная initData: {}", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"невалидная initData: {e}",
        ) from e

    user, created = await get_or_create_user(
        db, parsed.user, referral_start_param=parsed.start_param
    )
    await db.commit()
    await db.refresh(user)

    if created:
        logger.info("Зарегистрирован новый пользователь через Mini App: {}", user)

    access = create_access_token(user.id, user.telegram_id)
    refresh = create_refresh_token(user.id, user.telegram_id)

    return AuthResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserPublic.model_validate(user),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    db: DbSession,
    body: RefreshRequest,
) -> RefreshResponse:
    """Обмен refresh токена на новый access токен."""
    payload = decode_token(body.refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="невалидный refresh токен",
        )

    user = await get_user_by_id(db, int(payload.sub))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="пользователь не найден",
        )

    return RefreshResponse(access_token=create_access_token(user.id, user.telegram_id))
