"""Resolve a Telegram user's avatar into a direct file URL.

Telegram does not hand out avatar URLs directly: you ask for the user's profile
photos, take the largest size of the newest one, then turn its file_id into a
path with getFile. The resulting link embeds the bot token, so it is only ever
stored server-side and rendered by our own frontend.
"""

import logging

from aiogram import Bot

from app import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)


async def get_avatar_url(bot: Bot, telegram_id: int) -> str | None:
    try:
        photos = await bot.get_user_profile_photos(user_id=telegram_id, limit=1)
        if not photos.total_count or not photos.photos:
            return None
        # photos.photos[0] is one photo in several sizes — take the largest
        largest = photos.photos[0][-1]
        file = await bot.get_file(largest.file_id)
        return f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file.file_path}"
    except Exception as exc:
        logger.debug("no avatar for %s: %s", telegram_id, exc)
        return None
