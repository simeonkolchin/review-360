"""Thin Telegram Bot API client used by the gateway to post into groups."""

import logging

import httpx

from app import TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_USERNAME, TELEGRAM_PROXY

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"


def deep_link(token: str) -> str | None:
    """t.me link that opens the bot and immediately starts the review."""
    if not TELEGRAM_BOT_USERNAME:
        return None
    return f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={token}"


def mention(display_name: str, telegram_id: int) -> str:
    """HTML mention that works even for users without a username."""
    safe = (display_name or "участник").replace("<", "").replace(">", "")
    return f'<a href="tg://user?id={telegram_id}">{safe}</a>'


async def fetch_file(file_path: str) -> tuple[bytes, str] | None:
    """Download a file from Telegram by its `getFile` path.

    The download URL carries the bot token, so this always happens server-side;
    callers get raw bytes to hand to the browser.
    """
    if not TELEGRAM_BOT_TOKEN:
        return None
    url = f"{API_BASE}/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    try:
        async with httpx.AsyncClient(timeout=15.0, proxy=TELEGRAM_PROXY or None) as client:
            response = await client.get(url)
        if response.status_code != 200:
            logger.warning("file download failed: %s", response.status_code)
            return None
        return response.content, response.headers.get("content-type", "image/jpeg")
    except Exception as exc:
        logger.warning("file download error: %s", exc)
        return None


async def _call(method: str, payload: dict | None = None):
    if not TELEGRAM_BOT_TOKEN:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0, proxy=TELEGRAM_PROXY or None) as client:
            response = await client.post(
                f"{API_BASE}/bot{TELEGRAM_BOT_TOKEN}/{method}", json=payload or {}
            )
        data = response.json()
        return data.get("result") if data.get("ok") else None
    except Exception as exc:
        logger.warning("%s error: %s", method, exc)
        return None


async def chat_status(chat_id: int) -> dict:
    """What Telegram will tell us about a group.

    The Bot API refuses to list members, but it does say how many there are and
    whether we are an administrator — which together explain why the roster on
    the site may be shorter than the group really is.
    """
    status: dict = {"member_count": None, "bot_is_admin": None, "photo_url": None}

    total = await _call("getChatMemberCount", {"chat_id": chat_id})
    if isinstance(total, int):
        status["member_count"] = total

    me = await _call("getMe")
    if me:
        membership = await _call(
            "getChatMember", {"chat_id": chat_id, "user_id": me["id"]}
        )
        if membership:
            status["bot_is_admin"] = membership.get("status") in {"administrator", "creator"}

    # Groups often get their photo after the bot joins — pick it up on the way past.
    chat = await _call("getChat", {"chat_id": chat_id})
    photo = (chat or {}).get("photo", {}).get("small_file_id")
    if photo:
        file = await _call("getFile", {"file_id": photo})
        if file and file.get("file_path"):
            status["photo_url"] = f"tg:{file['file_path']}"

    return status


async def leave_chat(chat_id: int) -> bool:
    """Make the bot leave a group — called when the chat is deleted from the site."""
    if not TELEGRAM_BOT_TOKEN:
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0, proxy=TELEGRAM_PROXY or None) as client:
            response = await client.post(
                f"{API_BASE}/bot{TELEGRAM_BOT_TOKEN}/leaveChat", json={"chat_id": chat_id}
            )
        return response.status_code < 400
    except Exception as exc:
        logger.warning("leaveChat error: %s", exc)
        return False


async def send_message(chat_id: int, text: str, reply_markup: dict | None = None) -> bool:
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — skipping sendMessage to %s", chat_id)
        return False

    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient(timeout=10.0, proxy=TELEGRAM_PROXY or None) as client:
            response = await client.post(
                f"{API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json=payload
            )
        if response.status_code >= 400:
            logger.error("sendMessage failed: %s %s", response.status_code, response.text[:300])
            return False
        return True
    except Exception as exc:
        logger.error("sendMessage error: %s", exc)
        return False
