from pydantic import BaseModel, Field


class TelegramAuthRequest(BaseModel):
    """Payload produced by the Telegram Login Widget."""

    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class DevLoginRequest(BaseModel):
    """Local development login — no signature check. Disabled in production."""

    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    leader_telegram_id: int | None = None
    member_telegram_ids: list[int] = Field(default_factory=list)


class EnrollRequest(BaseModel):
    """Bot -> backend: a user tapped 'join' in a group, or started the bot."""

    telegram_chat_id: int
    chat_title: str
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None
    can_dm: bool = False
    is_admin: bool = False


class ResponseItem(BaseModel):
    competency_id: int
    score: int
    comment: str | None = None


class SubmitResponsesRequest(BaseModel):
    assignment_id: int
    responses: list[ResponseItem]
    # When true the payload only carries a free-text note, so scores are left alone
    comment_only: bool = False


class EventRequest(BaseModel):
    """Activity record written by the gateway for usage statistics."""

    kind: str
    telegram_id: int | None = None
    chat_id: int | None = None
    payload: dict | None = None
