"""Private-chat handlers: website login, the review itself, results."""

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, ChatShared, Message

from app import SCORE_MAX
from app.keyboards.inline import (
    chat_picker_keyboard,
    comment_keyboard,
    score_keyboard,
)
from app.services import gateway
from app.services.photos import get_avatar_file_id, get_avatar_url

router = Router()
logger = logging.getLogger(__name__)

# reviewer telegram_id -> where they are in their review.
# Losing this on restart only means re-asking; the server owns what is saved.
SESSIONS: dict[int, dict] = {}

KIND_LABEL = {"self": "самооценка", "leader": "как лидер", "peer": "коллега"}


def _progress_bar(done: int, total: int, width: int = 10) -> str:
    filled = round(width * done / total) if total else 0
    return "▰" * filled + "▱" * (width - filled)


async def _ask_current(message: Message, telegram_id: int) -> None:
    """Send the next question, or wrap up when everything is answered."""
    session = SESSIONS.get(telegram_id)
    if not session:
        return

    pending = [a for a in session["assignments"] if not a["completed"]]
    if not pending:
        SESSIONS.pop(telegram_id, None)
        await message.answer(
            "🎉 <b>Готово, спасибо!</b>\n\n"
            "Вы прошли оценку целиком. Результаты появятся, когда организатор "
            "закроет раунд — я пришлю уведомление.\n\n"
            "Посмотреть свои результаты: /results"
        )
        return

    assignment = pending[0]
    competencies = session["competencies"]
    index = session["competency_index"]
    competency = competencies[index]

    total = len(session["assignments"])
    done = total - len(pending)

    is_self = assignment["kind"] == "self"
    who = "себя" if is_self else assignment["reviewee"]["display_name"]

    header = (
        f"{'🪞' if is_self else '👤'} <b>{who}</b>"
        f"  <i>({KIND_LABEL.get(assignment['kind'], assignment['kind'])})</i>\n"
        f"<code>{_progress_bar(done, total)}</code>  {done}/{total} человек\n\n"
        f"<b>{competency['name']}</b>\n"
        f"<i>{competency.get('description') or ''}</i>\n\n"
        f"Вопрос {index + 1} из {len(competencies)} · оцените от 1 до {SCORE_MAX}"
    )

    keyboard = score_keyboard(assignment["id"], competency["id"])
    photo = assignment.get("_avatar")

    # Show the person's face on the first question about them — much easier to
    # answer honestly when you can see who you are rating.
    if photo and index == 0 and not is_self:
        try:
            await message.answer_photo(photo=photo, caption=header, reply_markup=keyboard)
            return
        except Exception as exc:
            logger.debug("photo send failed: %s", exc)

    await message.answer(header, reply_markup=keyboard)


async def _start_review(message: Message, token: str) -> None:
    telegram_id = message.from_user.id
    tasks = await gateway.get_tasks(token, telegram_id)
    if not tasks:
        await message.answer(
            "Не удалось найти активную оценку по этой ссылке.\n"
            "Возможно, раунд уже закрыт или вы не входите в эту команду."
        )
        return

    pending = [a for a in tasks["assignments"] if not a["completed"]]
    if not pending:
        await message.answer("Вы уже прошли эту оценку ✅\n\nПосмотреть результаты: /results")
        return

    # Preload avatars so questions can show a face
    for assignment in tasks["assignments"]:
        reviewee_id = assignment["reviewee"]["telegram_id"]
        assignment["_avatar"] = await get_avatar_file_id(message.bot, reviewee_id)

    SESSIONS[telegram_id] = {
        "token": token,
        "assignments": tasks["assignments"],
        "competencies": tasks["competencies"],
        "competency_index": 0,
        "buffer": {},
        "awaiting_comment_for": None,
    }

    await message.answer(
        f"🎯 <b>Оценка 360</b> — команда «{tasks['team_name']}»\n\n"
        f"Предстоит оценить <b>{len(pending)}</b> человек(а) "
        f"по <b>{len(tasks['competencies'])}</b> компетенциям — это пара минут.\n\n"
        f"🔒 Ответы <b>анонимны</b>: коллега увидит только средние по команде, "
        f"без привязки к автору.\n"
        f"💾 Прогресс сохраняется — можно прерваться и вернуться."
    )
    await _ask_current(message, telegram_id)


@router.message(CommandStart(deep_link=True), F.chat.type == "private")
async def start_with_payload(message: Message, command) -> None:
    payload = (command.args or "").strip()

    # website login: t.me/<bot>?start=login_<token>
    if payload.startswith("login_"):
        user = message.from_user
        avatar = await get_avatar_url(message.bot, user.id)
        result = await gateway.confirm_login(
            payload[len("login_"):], user.id, user.username,
            user.first_name, user.last_name, avatar,
        )
        if result:
            await message.answer(
                "✅ <b>Вход подтверждён</b>\n\nВернитесь на вкладку с сайтом — вы уже внутри.",
                reply_markup=chat_picker_keyboard(),
            )
        else:
            await message.answer(
                "Ссылка для входа недействительна или устарела.\n"
                "Обновите страницу входа и попробуйте снова."
            )
        return

    await _start_review(message, payload)


@router.message(CommandStart(), F.chat.type == "private")
async def start(message: Message) -> None:
    await message.answer(
        "👋 <b>Review 360</b> — честная обратная связь для команды.\n\n"
        "<b>Как начать</b>\n"
        "1. Добавьте меня в рабочий чат\n"
        "2. Отправьте там <code>/enroll</code> — коллеги нажмут «Участвую»\n"
        "3. Соберите команду на сайте и запустите оценку\n\n"
        "Опрос я пришлю каждому сюда, в личку. Кнопка ниже поможет выбрать чат.\n\n"
        "<code>/results</code> — ваши результаты · <code>/help</code> — подробнее",
        reply_markup=chat_picker_keyboard(),
    )


@router.message(F.chat_shared)
async def chat_shared(message: Message) -> None:
    """User picked a group through the input-bar button."""
    shared: ChatShared = message.chat_shared
    title = shared.title or "Рабочий чат"
    result = await gateway.enroll(
        shared.chat_id, title, message.from_user, can_dm=True, is_admin=True
    )
    if result:
        await message.answer(
            f"✅ Чат <b>{title}</b> подключён.\n\n"
            f"Теперь отправьте там <code>/enroll</code>, чтобы коллеги отметились, "
            f"а затем соберите команду на сайте."
        )
    else:
        await message.answer(
            "Не получилось подключить чат. Убедитесь, что я добавлен в него как участник."
        )


@router.callback_query(F.data.startswith("score:"))
async def score_selected(query: CallbackQuery) -> None:
    _, assignment_id, competency_id, score = query.data.split(":")
    telegram_id = query.from_user.id
    session = SESSIONS.get(telegram_id)

    if not session:
        await query.answer("Сессия истекла — откройте ссылку на оценку заново", show_alert=True)
        return

    session["buffer"][int(competency_id)] = int(score)
    await query.answer(f"Оценка {score} ✓")

    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    session["competency_index"] += 1

    # Finished every competency for this person -> save, then offer a comment
    if session["competency_index"] >= len(session["competencies"]):
        responses = [
            {"competency_id": cid, "score": value} for cid, value in session["buffer"].items()
        ]
        if await gateway.submit(int(assignment_id), responses, telegram_id):
            for assignment in session["assignments"]:
                if assignment["id"] == int(assignment_id):
                    assignment["completed"] = True

        session["competency_index"] = 0
        session["buffer"] = {}
        session["awaiting_comment_for"] = int(assignment_id)

        target = next(
            (a for a in session["assignments"] if a["id"] == int(assignment_id)), None
        )
        who = "себе" if target and target["kind"] == "self" else (
            target["reviewee"]["display_name"] if target else "коллеге"
        )
        await query.message.answer(
            f"💬 Хотите добавить комментарий к <b>{who}</b>?\n\n"
            f"<i>Напишите пару фраз — что получается хорошо, что стоит усилить. "
            f"Текст покажут анонимно, вперемешку с другими.</i>",
            reply_markup=comment_keyboard(int(assignment_id)),
        )
        return

    await _ask_current(query.message, telegram_id)


@router.callback_query(F.data.startswith("skipcomment:"))
async def skip_comment(query: CallbackQuery) -> None:
    session = SESSIONS.get(query.from_user.id)
    if session:
        session["awaiting_comment_for"] = None
    await query.answer("Пропущено")
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _ask_current(query.message, query.from_user.id)


@router.message(F.text & ~F.text.startswith("/"), F.chat.type == "private")
async def free_text(message: Message) -> None:
    """Any plain message while we are waiting for a comment becomes that comment."""
    telegram_id = message.from_user.id
    session = SESSIONS.get(telegram_id)
    if not session or not session.get("awaiting_comment_for"):
        return

    assignment_id = session["awaiting_comment_for"]
    competencies = session["competencies"]
    # Attach the note to the first competency — it is stored per assignment and
    # surfaced as an anonymous free-text comment.
    await gateway.submit(
        assignment_id,
        [{"competency_id": competencies[0]["id"], "score": 0, "comment": message.text[:1000]}],
        telegram_id,
        comment_only=True,
    )
    session["awaiting_comment_for"] = None
    await message.answer("Спасибо, записал 🙏")
    await _ask_current(message, telegram_id)


@router.message(Command("results"), F.chat.type == "private")
async def results(message: Message) -> None:
    data = await gateway.get_results(message.from_user.id)
    if not data or not data.get("found"):
        await message.answer(
            "Пока нет завершённых оценок.\n"
            "Результаты появятся, когда организатор закроет раунд."
        )
        return

    result = data["result"]
    lines = [
        f"📊 <b>Ваши результаты</b> — команда «{data['team_name']}»",
        "",
        f"Самооценка: <b>{result.get('overall_self') or '—'}</b>    "
        f"Команда: <b>{result.get('overall_peer') or '—'}</b>",
        "",
    ]
    for item in result["scores"]:
        peer = item.get("peer_average")
        own = item.get("self_score")
        filled = int(round(peer or 0))
        lines.append(
            f"<b>{item['competency']}</b>\n"
            f"  {'▰' * filled}{'▱' * (SCORE_MAX - filled)}  "
            f"команда {peer or '—'} · вы {own or '—'}"
        )

    comments = result.get("comments") or []
    if comments:
        lines += ["", "💬 <b>Что написали коллеги</b> <i>(анонимно)</i>"]
        lines += [f"  • <i>{c}</i>" for c in comments[:8]]

    if result.get("message"):
        lines += ["", f"🔒 <i>{result['message']}</i>"]
    if data.get("is_leader"):
        lines += ["", "Вы лидер команды — полная сводка доступна на сайте."]

    await message.answer("\n".join(lines))


@router.message(Command("help"), F.chat.type == "private")
async def help_command(message: Message) -> None:
    await message.answer(
        "<b>Как работает Review 360</b>\n\n"
        "Каждый в команде оценивает коллег и себя по нескольким компетенциям. "
        "Разница между самооценкой и взглядом команды — самое полезное в методе.\n\n"
        "<b>Порядок</b>\n"
        "1. Добавьте меня в рабочий чат\n"
        "2. <code>/enroll</code> в чате — коллеги жмут «Участвую»\n"
        "3. На сайте соберите команду и запустите раунд\n"
        "4. Я пришлю каждому опрос в личку\n\n"
        "<b>Анонимность</b>\n"
        "Средние показываются, только когда ответили минимум 3 человека — "
        "иначе автора легко вычислить. Комментарии показываются вперемешку.\n\n"
        "<code>/results</code> — ваши результаты",
        reply_markup=chat_picker_keyboard(),
    )
