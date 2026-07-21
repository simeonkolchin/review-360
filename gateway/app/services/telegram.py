"""Thin Telegram Bot API client used by the gateway to post into groups."""

import logging

import httpx

from app import TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_USERNAME

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
        async with httpx.AsyncClient(timeout=10.0) as client:
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
