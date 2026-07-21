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
import time

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message

from app.keyboards.inline import enroll_keyboard
from app.services import gateway
from app.services.photos import get_avatar_url, get_chat_photo

router = Router()
logger = logging.getLogger(__name__)

GROUPS = {"group", "supergroup"}

# (chat_id, user_id) -> monotonic seconds. A chatty group would otherwise hit
# the gateway on every single message to re-learn what it already knows.
_SEEN: dict[tuple[int, int], float] = {}
SEEN_TTL_SEC = 600


def _recently_seen(chat_id: int, user_id: int) -> bool:
    now = time.monotonic()
    key = (chat_id, user_id)
    if now - _SEEN.get(key, 0) < SEEN_TTL_SEC:
        return True
    _SEEN[key] = now
    if len(_SEEN) > 10_000:  # cheap bound; the cache is pure optimisation
        for stale in [k for k, t in _SEEN.items() if now - t > SEEN_TTL_SEC]:
            _SEEN.pop(stale, None)
    return False


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
    """Pull the full admin list — the only roster Telegram hands over.

    Also refreshes the group's own photo, so the chat card on the site picks it
    up the moment the bot has a reason to look. Returns how many people the
    backend now knows in this chat, which is what the tally should show.
    """
    chat_photo = await get_chat_photo(bot, chat.id)
    try:
        admins = await bot.get_chat_administrators(chat.id)
    except Exception as exc:
        logger.warning("cannot read admins of %s: %s", chat.id, exc)
        return 0
    known = 0
    for member in admins:
        # The bot is an admin of its own group — it is not a participant.
        if member.user.is_bot:
            continue
        avatar = await get_avatar_url(bot, member.user.id)
        result = await gateway.enroll(
            chat.id, chat.title or "Группа", member.user,
            is_admin=True, photo_url=avatar, chat_photo_url=chat_photo,
        )
        if result:
            known = result.get("member_count", known)
    return known


@router.message(F.migrate_to_chat_id)
async def upgraded_away(message: Message) -> None:
    """Last message in the old group: it has become a supergroup."""
    await gateway.migrate_chat(
        message.chat.id, message.migrate_to_chat_id, message.chat.title
    )


@router.message(F.migrate_from_chat_id)
async def upgraded_here(message: Message) -> None:
    """First message in the new supergroup — same group, new id."""
    await gateway.migrate_chat(
        message.migrate_from_chat_id, message.chat.id, message.chat.title
    )
    await _sync_admins(message.bot, message.chat)


@router.message(F.new_chat_members)
async def members_added(message: Message) -> None:
    """The bot was added — or someone else was."""
    me = await message.bot.get_me()
    added_bot = any(u.id == me.id for u in message.new_chat_members)

    if added_bot:
        await _remember(message.bot, message.chat, message.from_user, is_admin=True)
        known = await _sync_admins(message.bot, message.chat)
        me_member = None
        try:
            me_member = await message.bot.get_chat_member(message.chat.id, me.id)
        except Exception as exc:
            logger.debug("cannot read own status in %s: %s", message.chat.id, exc)
        is_admin = bool(me_member and me_member.status in {"administrator", "creator"})

        hint = (
            "Тех, кто пишет в чате, я и так замечаю."
            if is_admin
            else "⚠️ Сделайте меня <b>администратором</b> — иначе я не вижу даже "
                 "сообщения остальных."
        )
        await message.answer(
            "👋 Привет! Я собираю обратную связь по методу <b>«Оценка 360»</b>.\n\n"
            "Нажмите «Участвую» — так я точно узнаю всех, кого можно включать в "
            "команды. Telegram не отдаёт ботам список участников, поэтому одна "
            "кнопка надёжнее любых догадок.\n\n"
            f"<i>{hint}</i>",
            reply_markup=enroll_keyboard(known),
        )
        return

    for user in message.new_chat_members:
        await _remember(message.bot, message.chat, user, with_photo=True)


@router.my_chat_member()
async def own_status_changed(update: ChatMemberUpdated) -> None:
    """Our own rights changed — most usefully, we were made an administrator.

    That is the moment privacy mode stops hiding other people's messages, so it
    is also the moment the roster can actually start filling up.
    """
    if update.chat.type not in GROUPS:
        return
    was_admin = update.old_chat_member.status in {"administrator", "creator"}
    is_admin = update.new_chat_member.status in {"administrator", "creator"}
    if is_admin and not was_admin:
        known = await _sync_admins(update.bot, update.chat)
        await update.bot.send_message(
            update.chat.id,
            "✅ Спасибо, теперь я администратор — вижу всех, кто пишет в чате, "
            f"и уже записал {known} человек(а).\n\n"
            "<i>Остальные добавятся, как только напишут сюда хоть что-нибудь.</i>",
        )


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


@router.message(Command("enroll"), F.chat.type.in_(GROUPS))
@router.message(Command("members"), F.chat.type.in_(GROUPS))
async def ask_to_enroll(message: Message) -> None:
    """Put the join button in the chat and record whoever asked for it."""
    result = await _remember(message.bot, message.chat, message.from_user, with_photo=True)
    count = (result or {}).get("member_count", 0)
    await message.answer(
        "🎯 <b>Оценка 360</b>\n\n"
        "Нажмите «Участвую», чтобы попасть в список — из него на сайте "
        "собираются команды.\n\n"
        "<i>Заодно это даёт мне право написать вам в личку, когда начнётся опрос.</i>",
        reply_markup=enroll_keyboard(count),
    )


@router.callback_query(F.data == "enroll")
async def enrolled(query: CallbackQuery) -> None:
    """Someone tapped the join button — record them and update the tally."""
    chat = query.message.chat
    result = await _remember(query.bot, chat, query.from_user, with_photo=True)
    if not result:
        await query.answer("Не получилось записать, попробуйте ещё раз", show_alert=True)
        return

    await query.answer(
        "Вы уже в списке ✅" if result.get("already") else "Записал, спасибо ✅"
    )
    try:
        await query.message.edit_reply_markup(
            reply_markup=enroll_keyboard(result.get("member_count", 0))
        )
    except Exception as exc:
        # "message is not modified" when the count did not change — harmless
        logger.debug("cannot refresh the tally: %s", exc)


@router.message(F.chat.type.in_(GROUPS))
async def any_group_message(message: Message) -> None:
    """Last resort, and in practice the most effective one: passive harvesting.

    Runs after every other group handler, so it never swallows a command.

    Note this only sees messages at all if the bot is an administrator or its
    privacy mode is off in BotFather — otherwise Telegram hands it commands and
    replies only, and the roster fills up more slowly.
    """
    if _recently_seen(message.chat.id, message.from_user.id):
        return
    await _remember(message.bot, message.chat, message.from_user)
