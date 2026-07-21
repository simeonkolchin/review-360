"""Resolve a Telegram user's avatar into a reference our own API can serve.

Telegram does not hand out avatar URLs directly: you ask for the user's profile
photos, take the largest size of the newest one, then turn its file_id into a
path with getFile. The download URL for that path embeds the **bot token**, so
it must never reach a browser — we store just the path behind a `tg:` marker and
let the gateway stream the bytes (see `GET /api/avatar/...`). That also keeps
avatars working for clients who cannot reach api.telegram.org themselves.
"""

import logging

from aiogram import Bot

logger = logging.getLogger(__name__)


async def get_avatar_file_id(bot: Bot, telegram_id: int) -> str | None:
    """`file_id` of the person's newest profile photo.

    Sending a photo by file_id is what Telegram wants anyway — no download, no
    upload, and it works even where the file URL would not be reachable.
    """
    try:
        photos = await bot.get_user_profile_photos(user_id=telegram_id, limit=1)
        if not photos.total_count or not photos.photos:
            return None
        return photos.photos[0][-1].file_id
    except Exception as exc:
        logger.debug("no avatar file_id for %s: %s", telegram_id, exc)
        return None


async def get_avatar_url(bot: Bot, telegram_id: int) -> str | None:
    try:
        photos = await bot.get_user_profile_photos(user_id=telegram_id, limit=1)
        if not photos.total_count or not photos.photos:
            return None
        # photos.photos[0] is one photo in several sizes — take the largest
        largest = photos.photos[0][-1]
        file = await bot.get_file(largest.file_id)
        return f"tg:{file.file_path}" if file.file_path else None
    except Exception as exc:
        logger.debug("no avatar for %s: %s", telegram_id, exc)
        return None
