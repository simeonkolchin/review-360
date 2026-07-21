"""Group-chat handlers: keeping the member list in sync.

The Bot API deliberately has no "list the members of this group" call, so the
roster is assembled from everything Telegram *does* tell us:

* the admin list, which `getChatAdministrators` returns in full;
* `chat_member` updates — anyone joining or leaving while the bot is present;
* the author of any message sent in the chat.

Nobody has to press anything. The one thing self-enrolment used to buy — the
right to DM someone — comes from the personal deep link in the round
announcement instead: pressing Start opens the dialogue and begins the review.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated, Message

from app.services import gateway
from app.services.photos import get_avatar_url

router = Router()
logger = logging.getLogger(__name__)

GROUPS = {"group", "supergroup"}


async def _remember(bot: Bot, chat, user, *, is_admin: bool = False, with_photo: bool = False):
    """Record one person as a member of one chat."""
    if user is None or user.is_bot:
        return None
    avatar = await get_avatar_url(bot, user.id) if with_photo else None
    return await gateway.enroll(
        chat.id,
        chat.title or "Группа",
        user,
        photo_url=avatar,
        is_admin=is_admin,
    )


async def _sync_admins(bot: Bot, chat) -> int:
    """Pull the full admin list — the only roster Telegram hands over."""
    try:
        admins = await bot.get_chat_administrators(chat.id)
    except Exception as exc:
        logger.warning("cannot read admins of %s: %s", chat.id, exc)
        return 0
    count = 0
    for member in admins:
        if await _remember(bot, chat, member.user, is_admin=True, with_photo=True):
            count += 1
    return count


@router.message(F.new_chat_members)
async def members_added(message: Message) -> None:
    """The bot was added — or someone else was."""
    me = await message.bot.get_me()
    added_bot = any(u.id == me.id for u in message.new_chat_members)

    if added_bot:
        await _remember(message.bot, message.chat, message.from_user, is_admin=True)
        known = await _sync_admins(message.bot, message.chat)
        await message.answer(
            "👋 Привет! Я собираю обратную связь по методу <b>«Оценка 360»</b>.\n\n"
            f"Участники подтягиваются автоматически — уже вижу <b>{known}</b>. "
            "Остальные появятся, как только напишут что-нибудь в чате.\n\n"
            "Дальше — соберите команду на сайте и запустите оценку: "
            "я отмечу всех здесь и пришлю каждому опрос в личку."
        )
        return

    for user in message.new_chat_members:
        await _remember(message.bot, message.chat, user, with_photo=True)


@router.chat_member()
async def membership_changed(update: ChatMemberUpdated) -> None:
    """Someone joined or left while we were watching."""
    if update.chat.type not in GROUPS:
        return
    status = update.new_chat_member.status
    user = update.new_chat_member.user
    if status in {"member", "administrator", "creator"}:
        await _remember(
            update.bot, update.chat, user,
            is_admin=status in {"administrator", "creator"}, with_photo=True,
        )
    elif status in {"left", "kicked"}:
        await gateway.forget(update.chat.id, user.id)


@router.message(Command("members"), F.chat.type.in_(GROUPS))
async def resync(message: Message) -> None:
    """Manual nudge: re-read the admin list and record whoever asked."""
    await _remember(message.bot, message.chat, message.from_user, with_photo=True)
    known = await _sync_admins(message.bot, message.chat)
    await message.answer(
        f"🔄 Список обновлён — вижу {known} администратор(ов) и всех, кто писал в чате.\n\n"
        "<i>Telegram не отдаёт ботам полный список участников группы, поэтому "
        "остальные добавятся, как только напишут сюда хоть что-то.</i>"
    )


@router.message(F.chat.type.in_(GROUPS))
async def any_group_message(message: Message) -> None:
    """Last resort, and in practice the most effective one: passive harvesting.

    Runs after every other group handler, so it never swallows a command.
    """
    await _remember(message.bot, message.chat, message.from_user)
