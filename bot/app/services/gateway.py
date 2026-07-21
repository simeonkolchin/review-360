"""Client for the gateway. The bot never touches the database directly."""

import logging

import httpx

from app import BOT_API_TOKEN, GATEWAY_URL, REQUEST_TIMEOUT_SEC

logger = logging.getLogger(__name__)

HEADERS = {"X-Bot-Token": BOT_API_TOKEN}


async def _request(method: str, path: str, **kwargs):
    try:
        async with httpx.AsyncClient(timeout=float(REQUEST_TIMEOUT_SEC)) as client:
            response = await client.request(
                method, f"{GATEWAY_URL}{path}", headers=HEADERS, **kwargs
            )
    except Exception as exc:
        logger.error("gateway unreachable: %s", exc)
        return None

    if response.status_code >= 400:
        logger.warning("gateway %s %s -> %s %s", method, path, response.status_code,
                       response.text[:200])
        return None
    return response.json() if response.content else None


async def enroll(chat_id: int, chat_title: str, user, can_dm: bool = False,
                 is_admin: bool = False, photo_url: str | None = None):
    return await _request(
        "POST",
        "/bot/enroll",
        json={
            "telegram_chat_id": chat_id,
            "chat_title": chat_title,
            "telegram_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "photo_url": photo_url,
            "can_dm": can_dm,
            "is_admin": is_admin,
        },
    )


async def forget(chat_id: int, telegram_id: int):
    """Someone left the group — drop them from its roster."""
    return await _request(
        "POST",
        "/bot/leave",
        json={"telegram_chat_id": chat_id, "telegram_id": telegram_id},
    )


async def mark_reachable(user):
    """Record that this person has opened the bot, so we may DM them."""
    return await _request(
        "POST",
        "/bot/reachable",
        json={
            "telegram_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
    )


async def get_tasks(token: str, telegram_id: int):
    return await _request("GET", "/bot/tasks", params={"token": token, "telegram_id": telegram_id})


async def submit(assignment_id: int, responses: list[dict], telegram_id: int,
                 comment_only: bool = False):
    return await _request(
        "POST",
        "/bot/responses",
        params={"telegram_id": telegram_id},
        json={
            "assignment_id": assignment_id,
            "responses": responses,
            "comment_only": comment_only,
        },
    )


async def get_results(telegram_id: int):
    return await _request("GET", "/bot/results", params={"telegram_id": telegram_id})


async def confirm_login(token: str, telegram_id: int, username, first_name, last_name,
                        photo_url: str | None = None):
    return await _request(
        "POST",
        "/bot/confirm-login",
        json={
            "token": token,
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "photo_url": photo_url,
        },
    )
