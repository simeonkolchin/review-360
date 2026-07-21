from fastapi import APIRouter, Depends, HTTPException, Response, status

from app import (
    AUTH_COOKIE_NAME,
    COOKIE_SECURE,
    DEV_LOGIN_ENABLED,
    JWT_TTL_HOURS,
    TELEGRAM_BOT_USERNAME,
)
from app.schemas.requests import DevLoginRequest, TelegramAuthRequest
from app.schemas.responses import UserResponse
from app.services import data_client
from app.services.security import (
    create_access_token,
    get_current_user_id,
    verify_telegram_auth,
)

router = APIRouter(prefix="/auth")


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=JWT_TTL_HOURS * 3600,
    )


@router.get("/config", summary="Public auth configuration for the frontend")
async def auth_config():
    return {"bot_username": TELEGRAM_BOT_USERNAME, "dev_login_enabled": DEV_LOGIN_ENABLED}


@router.post("/telegram", response_model=UserResponse, summary="Login via Telegram Login Widget")
async def telegram_login(payload: TelegramAuthRequest, response: Response):
    if not verify_telegram_auth(payload.model_dump(exclude_none=True)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Telegram signature")

    user = await data_client.post(
        "/users/upsert",
        json={
            "telegram_id": payload.id,
            "username": payload.username,
            "first_name": payload.first_name,
            "last_name": payload.last_name,
            "photo_url": payload.photo_url,
        },
    )
    _set_cookie(response, create_access_token(payload.id))
    await data_client.record_event("login", payload.id, method="telegram")
    return user


@router.post("/dev-login", response_model=UserResponse, summary="Local development login")
async def dev_login(payload: DevLoginRequest, response: Response):
    """Bypasses signature verification.

    The Telegram Login Widget requires a domain registered with BotFather and
    does not work on localhost, so local runs use this. Disabled unless
    DEV_LOGIN_ENABLED is on.
    """
    if not DEV_LOGIN_ENABLED:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Dev login is disabled")

    user = await data_client.post(
        "/users/upsert",
        json={
            "telegram_id": payload.telegram_id,
            "username": payload.username,
            "first_name": payload.first_name or "Dev",
            "last_name": payload.last_name,
        },
    )
    _set_cookie(response, create_access_token(payload.telegram_id))
    await data_client.record_event("login", payload.telegram_id, method="dev")
    return user


@router.post("/logout", summary="Clear the session cookie")
async def logout(response: Response):
    response.delete_cookie(AUTH_COOKIE_NAME, samesite="lax", secure=COOKIE_SECURE)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse, summary="Current user")
async def me(telegram_id: int = Depends(get_current_user_id)):
    return await data_client.post("/users/upsert", json={"telegram_id": telegram_id})


# --------------------------------------------------------------------- login via bot


@router.post("/login-link", summary="Start login through the Telegram bot")
async def login_link():
    """Mint a one-time token and hand back the deep link to open the bot.

    This replaces the Telegram Login Widget, which needs a public domain
    registered with BotFather and therefore cannot work on localhost.
    """
    data = await data_client.post("/login-tokens")
    token = data["token"]
    link = (
        f"https://t.me/{TELEGRAM_BOT_USERNAME}?start=login_{token}"
        if TELEGRAM_BOT_USERNAME
        else None
    )
    return {"token": token, "link": link, "bot_username": TELEGRAM_BOT_USERNAME}


@router.get("/login-status", response_model=UserResponse | None, summary="Poll login status")
async def login_status(token: str, response: Response):
    """Polled by the login page; sets the session cookie once confirmed."""
    data = await data_client.post("/login-tokens/consume", json={"token": token})
    if not data.get("confirmed"):
        return None

    user = data["user"]
    _set_cookie(response, create_access_token(user["telegram_id"]))
    await data_client.record_event("login", user["telegram_id"], method="bot")
    return user
