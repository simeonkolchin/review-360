"""One message that keeps being edited instead of a growing wall of messages.

The review is a single "card" in the private chat: the reviewee's photo with
the question in the caption and the score buttons underneath. Every answer edits
that same message, so the dialogue stays one screen tall no matter how many
people and questions there are.

Telegram cannot turn a text message into a photo message (or back) with an
edit, so the card remembers what it currently is and resends only when the type
has to change.
"""

import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InputMediaPhoto

logger = logging.getLogger(__name__)


async def render(
    bot: Bot,
    chat_id: int,
    card: dict | None,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
    photo: str | None = None,
) -> dict:
    """Draw the card, editing in place whenever Telegram allows it.

    `card` is the state returned by the previous call: message id, whether it is
    a photo message, and which photo is on it. Returns the new state.
    """
    if card:
        try:
            same_kind = bool(card.get("photo")) == bool(photo)
            if same_kind and photo and card.get("photo") != photo:
                await bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=card["message_id"],
                    media=InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"),
                    reply_markup=keyboard,
                )
                return {"message_id": card["message_id"], "photo": photo}
            if same_kind and photo:
                await bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=card["message_id"],
                    caption=text,
                    reply_markup=keyboard,
                )
                return card
            if same_kind:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=card["message_id"],
                    text=text,
                    reply_markup=keyboard,
                    disable_web_page_preview=True,
                )
                return card
            # text <-> photo: the only case Telegram makes us start over
            await bot.delete_message(chat_id=chat_id, message_id=card["message_id"])
        except Exception as exc:
            # "message is not modified" and friends are not worth failing over
            logger.debug("card edit failed, sending a new one: %s", exc)
            if "not modified" in str(exc):
                return card

    if photo:
        message = await bot.send_photo(
            chat_id=chat_id, photo=photo, caption=text, reply_markup=keyboard
        )
        return {"message_id": message.message_id, "photo": photo}

    message = await bot.send_message(
        chat_id=chat_id, text=text, reply_markup=keyboard, disable_web_page_preview=True
    )
    return {"message_id": message.message_id, "photo": None}


async def close(bot: Bot, chat_id: int, card: dict | None, text: str) -> None:
    """Leave the card as a final, button-less message."""
    if not card:
        await bot.send_message(chat_id=chat_id, text=text)
        return
    try:
        if card.get("photo"):
            await bot.edit_message_caption(
                chat_id=chat_id, message_id=card["message_id"], caption=text, reply_markup=None
            )
        else:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=card["message_id"], text=text, reply_markup=None
            )
    except Exception:
        await bot.send_message(chat_id=chat_id, text=text)
