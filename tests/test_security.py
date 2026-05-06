"""Тесты JWT — проверка выпуска и валидации токенов."""
import time

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_access_token_roundtrip():
    """Выпустили → распаковали → данные совпадают."""
    token = create_access_token(user_id=42, telegram_id=12345)
    payload = decode_token(token, expected_type="access")
    assert payload is not None
    assert payload.sub == "42"
    assert payload.telegram_id == 12345
    assert payload.type == "access"


def test_refresh_token_separate_from_access():
    """Refresh токен НЕ должен валидироваться как access."""
    refresh = create_refresh_token(user_id=42, telegram_id=12345)
    # Декодим как access — должно не пройти
    assert decode_token(refresh, expected_type="access") is None
    # Декодим как refresh — должно пройти
    payload = decode_token(refresh, expected_type="refresh")
    assert payload is not None
    assert payload.type == "refresh"


def test_invalid_signature_rejected():
    """Поломанный токен → None."""
    token = create_access_token(user_id=42, telegram_id=12345)
    # Меняем последний символ
    broken = token[:-1] + ("A" if token[-1] != "A" else "B")
    assert decode_token(broken) is None


def test_garbage_token_rejected():
    assert decode_token("not-a-token") is None
    assert decode_token("") is None
