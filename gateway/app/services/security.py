"""Telegram Login Widget verification, JWT sessions and bot authentication."""

import hashlib
import hmac
import secrets
import time
from datetime import UTC, datetime, timedelta

from fastapi import Cookie, Header, HTTPException, status
from jose import JWTError, jwt

from app import (
    AUTH_COOKIE_NAME,
    BOT_API_TOKEN,
    JWT_ALGORITHM,
    JWT_SECRET,
    JWT_TTL_HOURS,
    TELEGRAM_AUTH_MAX_AGE_SEC,
    TELEGRAM_BOT_TOKEN,
)


def verify_telegram_auth(payload: dict) -> bool:
    """Validate a Telegram Login Widget payload.

    Telegram's scheme: join every field except `hash` as sorted "key=value"
    lines, then compare HMAC-SHA256 (keyed with SHA256 of the bot token)
    against the supplied hash.
    """
    if not TELEGRAM_BOT_TOKEN:
        return False

    received_hash = payload.get("hash")
    if not received_hash:
        return False

    try:
        auth_date = int(payload.get("auth_date", 0))
    except (TypeError, ValueError):
        return False
    if time.time() - auth_date > TELEGRAM_AUTH_MAX_AGE_SEC:
        return False

    data_check_string = "\n".join(
        f"{key}={payload[key]}"
        for key in sorted(payload)
        if key != "hash" and payload[key] is not None
    )
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    expected = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received_hash)


def create_access_token(telegram_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(hours=JWT_TTL_HOURS)
    return jwt.encode({"sub": str(telegram_id), "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user_id(
    token: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME),
) -> int:
    """Every public endpoint depends on this — no cookie, no access."""
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc


async def require_bot_token(x_bot_token: str = Header(default="")) -> None:
    """Guards the /bot endpoints the Telegram bot calls."""
    if not secrets.compare_digest(x_bot_token, BOT_API_TOKEN):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid bot token")
