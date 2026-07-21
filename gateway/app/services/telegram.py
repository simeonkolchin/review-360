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


async def _api(method: str, payload: dict | None = None) -> dict | None:
    """Raw Bot API call — the whole envelope, errors included."""
    if not TELEGRAM_BOT_TOKEN:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0, proxy=TELEGRAM_PROXY or None) as client:
            response = await client.post(
                f"{API_BASE}/bot{TELEGRAM_BOT_TOKEN}/{method}", json=payload or {}
            )
        return response.json()
    except Exception as exc:
        logger.warning("%s error: %s", method, exc)
        return None


async def _call(method: str, payload: dict | None = None):
    data = await _api(method, payload)
    return data.get("result") if data and data.get("ok") else None


def migration_target(data: dict | None) -> int | None:
    """The new chat id Telegram hands back when a group became a supergroup.

    Upgrading a group changes its id, and every call with the old one fails
    with this pointer — following it is the only way not to lose the chat.
    """
    if not data or data.get("ok"):
        return None
    return (data.get("parameters") or {}).get("migrate_to_chat_id")


async def chat_status(chat_id: int) -> dict:
    """What Telegram will tell us about a group.

    The Bot API refuses to list members, but it does say how many there are and
    whether we are an administrator — which together explain why the roster on
    the site may be shorter than the group really is.
    """
    status: dict = {
        "member_count": None, "bot_is_admin": None, "photo_url": None, "migrate_to": None,
    }

    probe = await _api("getChat", {"chat_id": chat_id})
    moved = migration_target(probe)
    if moved:
        status["migrate_to"] = moved
        return status

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
    chat = (probe or {}).get("result") or {}
    photo = (chat.get("photo") or {}).get("small_file_id")
    if photo:
        file = await _call("getFile", {"file_id": photo})
        if file and file.get("file_path"):
            status["photo_url"] = f"tg:{file['file_path']}"

    return status


MEMBER_STATUSES = {"creator", "administrator", "member", "restricted"}


async def sync_members(chat_id: int, chat_title: str, candidate_ids: list[int]) -> int:
    """Record everyone Telegram confirms is in this chat.

    Two sources, both of which the Bot API does allow: the admin list in full,
    and a membership check for each person we already know from anywhere else.
    Returns how many people were written.
    """
    from app.services import data_client  # local import keeps the module import-light

    async def remember(user: dict, is_admin: bool) -> bool:
        if user.get("is_bot"):
            return False
        photo = None
        photos = await _call(
            "getUserProfilePhotos", {"user_id": user["id"], "limit": 1}
        )
        sizes = (photos or {}).get("photos") or []
        if sizes:
            file = await _call("getFile", {"file_id": sizes[0][-1]["file_id"]})
            if file and file.get("file_path"):
                photo = f"tg:{file['file_path']}"
        await data_client.post("/enroll", json={
            "telegram_chat_id": chat_id,
            "chat_title": chat_title,
            "telegram_id": user["id"],
            "username": user.get("username"),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "photo_url": photo,
            "is_admin": is_admin,
        })
        return True

    seen: set[int] = set()
    written = 0

    for admin in await _call("getChatAdministrators", {"chat_id": chat_id}) or []:
        user = admin.get("user", {})
        seen.add(user.get("id"))
        if await remember(user, is_admin=True):
            written += 1

    for candidate in candidate_ids:
        if candidate in seen:
            continue
        membership = await _call(
            "getChatMember", {"chat_id": chat_id, "user_id": candidate}
        )
        if not membership or membership.get("status") not in MEMBER_STATUSES:
            continue
        if await remember(membership.get("user", {}), is_admin=False):
            written += 1

    return written


async def leave_chat(chat_id: int) -> bool:
    """Make the bot leave a group — called when the chat is deleted from the site.

    Follows a supergroup migration: a stored id can be the retired one, and
    leaving the dead chat would silently leave the bot sitting in the live one.
    """
    data = await _api("leaveChat", {"chat_id": chat_id})
    moved = migration_target(data)
    if moved:
        data = await _api("leaveChat", {"chat_id": moved})
    return bool(data and data.get("ok"))


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

    data = await _api("sendMessage", payload)
    moved = migration_target(data)
    if moved:
        payload["chat_id"] = moved
        data = await _api("sendMessage", payload)
    if not (data and data.get("ok")):
        logger.error("sendMessage failed: %s", (data or {}).get("description"))
        return False
    return True
