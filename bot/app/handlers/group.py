"""Group-chat handlers: enrolment.

Telegram's Bot API cannot list the members of a group, so people opt in by
tapping a button. That also gives the bot permission to DM them later, which it
otherwise would not have.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.keyboards.inline import enroll_keyboard
from app.services import gateway
from app.services.photos import get_avatar_url

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("enroll"), F.chat.type.in_({"group", "supergroup"}))
async def start_enrollment(message: Message) -> None:
    await gateway.enroll(message.chat.id, message.chat.title or "Группа", message.from_user,
                         is_admin=True)
    await message.answer(
        "🎯 <b>Оценка 360</b>\n\n"
        "Нажмите «Участвую», чтобы попасть в список участников — "
        "после этого вас можно будет добавить в команду на сайте.\n\n"
        "<i>Это же даёт боту право написать вам в личку, когда начнётся опрос.</i>",
        reply_markup=enroll_keyboard(),
    )


@router.callback_query(F.data == "enroll")
async def enroll_callback(query: CallbackQuery) -> None:
    avatar = await get_avatar_url(query.bot, query.from_user.id)
    result = await gateway.enroll(
        query.message.chat.id,
        query.message.chat.title or "Группа",
        query.from_user,
        photo_url=avatar,
    )
    if result:
        await query.answer("Вы в списке участников ✅", show_alert=False)
    else:
        await query.answer("Не удалось записать, попробуйте позже", show_alert=True)


@router.message(F.new_chat_members)
async def bot_added(message: Message) -> None:
    """Greet the group as soon as the bot is added."""
    me = await message.bot.get_me()
    if not any(u.id == me.id for u in message.new_chat_members):
        return
    await gateway.enroll(message.chat.id, message.chat.title or "Группа", message.from_user,
                         is_admin=True)
    await message.answer(
        "👋 Привет! Я собираю обратную связь по методу <b>«Оценка 360»</b>.\n\n"
        "Нажмите «Участвую» — и вы попадёте в список, из которого на сайте "
        "собираются команды.",
        reply_markup=enroll_keyboard(),
    )
