from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    KeyboardButtonRequestChat,
    ReplyKeyboardMarkup,
)

from app import SCORE_MAX, SCORE_MIN

SCORE_LABELS = {1: "1 · слабо", 2: "2", 3: "3 · норма", 4: "4", 5: "5 · отлично"}


def enroll_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✋ Участвую", callback_data="enroll")]]
    )


def score_keyboard(assignment_id: int, competency_id: int) -> InlineKeyboardMarkup:
    """Score buttons for one competency, two rows so the labels stay readable."""
    buttons = [
        InlineKeyboardButton(
            text=SCORE_LABELS.get(score, str(score)),
            callback_data=f"score:{assignment_id}:{competency_id}:{score}",
        )
        for score in range(SCORE_MIN, SCORE_MAX + 1)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons[:3], buttons[3:]])


def comment_keyboard(assignment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="Пропустить →", callback_data=f"skipcomment:{assignment_id}")
        ]]
    )


def chat_picker_keyboard() -> ReplyKeyboardMarkup:
    """Button in the input bar that opens Telegram's own group picker.

    Uses KeyboardButtonRequestChat, so the user selects a group from their list
    instead of copying IDs around, and Telegram sends us the chat back.
    """
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(
                text="📂 Выбрать рабочий чат",
                request_chat=KeyboardButtonRequestChat(
                    request_id=1,
                    chat_is_channel=False,
                    bot_is_member=True,
                    request_title=True,
                    request_username=True,
                ),
            )
        ]],
        resize_keyboard=True,
        is_persistent=True,
    )
