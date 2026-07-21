"""SQLAlchemy models for Review 360."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RoundStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    closed = "closed"


class AssignmentKind(str, enum.Enum):
    self_review = "self"
    peer = "peer"
    leader = "leader"


class TgUser(Base):
    """A Telegram user known to the system."""

    __tablename__ = "tg_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def display_name(self) -> str:
        full = " ".join(p for p in [self.first_name, self.last_name] if p).strip()
        return full or (f"@{self.username}" if self.username else f"id{self.telegram_id}")


class Chat(Base):
    """A Telegram group the bot was added to."""

    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    added_by_id: Mapped[int | None] = mapped_column(ForeignKey("tg_users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    added_by: Mapped[TgUser | None] = relationship(lazy="selectin")
    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan", lazy="selectin"
    )
    teams: Mapped[list["Team"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan", lazy="selectin"
    )


class Membership(Base):
    """Someone the bot has seen in a chat.

    The Bot API cannot enumerate a group's members, so this table is built up
    from what Telegram does tell us: joins, admin lists, and anyone who writes
    a message while the bot is present.
    """

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("chat_id", "tg_user_id", name="uq_membership"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    tg_user_id: Mapped[int] = mapped_column(ForeignKey("tg_users.id", ondelete="CASCADE"))
    # True once the user has opened a private chat with the bot — only then can
    # the bot DM them their review tasks.
    can_dm: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chat: Mapped[Chat] = relationship(back_populates="memberships", lazy="selectin")
    tg_user: Mapped[TgUser] = relationship(lazy="selectin")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(128))
    leader_id: Mapped[int | None] = mapped_column(ForeignKey("tg_users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chat: Mapped[Chat] = relationship(back_populates="teams", lazy="selectin")
    leader: Mapped[TgUser | None] = relationship(lazy="selectin")
    members: Mapped[list["TeamMember"]] = relationship(
        back_populates="team", cascade="all, delete-orphan", lazy="selectin"
    )
    rounds: Mapped[list["ReviewRound"]] = relationship(
        back_populates="team", cascade="all, delete-orphan", lazy="selectin"
    )


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "tg_user_id", name="uq_team_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    tg_user_id: Mapped[int] = mapped_column(ForeignKey("tg_users.id", ondelete="CASCADE"))

    team: Mapped[Team] = relationship(back_populates="members", lazy="selectin")
    tg_user: Mapped[TgUser] = relationship(lazy="selectin")


class Competency(Base):
    """One question in a questionnaire.

    Competencies live at three scopes, most specific first:

        team_id set   → this team's own questionnaire
        chat_id set   → the chat-wide questionnaire every team inherits
        both null     → the built-in defaults, seeded on first boot

    A team therefore starts with whatever the chat uses and only diverges once
    someone edits it. Rows are deactivated rather than deleted when historical
    answers point at them, so closed rounds keep making sense.
    """

    __tablename__ = "competencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    chat_id: Mapped[int | None] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=True, index=True
    )
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ReviewRound(Base):
    __tablename__ = "review_rounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    status: Mapped[RoundStatus] = mapped_column(Enum(RoundStatus), default=RoundStatus.draft)
    # Random token used in the bot deep link: t.me/<bot>?start=<token>
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Questionnaire as it stood when the round started. Snapshotting the ids
    # means editing the team's questions later cannot rewrite finished results.
    competency_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    team: Mapped[Team] = relationship(back_populates="rounds", lazy="selectin")
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="round", cascade="all, delete-orphan", lazy="selectin"
    )


class Assignment(Base):
    """One reviewer -> one reviewee task inside a round."""

    __tablename__ = "assignments"
    __table_args__ = (
        UniqueConstraint("round_id", "reviewer_id", "reviewee_id", name="uq_assignment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("review_rounds.id", ondelete="CASCADE"))
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("tg_users.id", ondelete="CASCADE"))
    reviewee_id: Mapped[int] = mapped_column(ForeignKey("tg_users.id", ondelete="CASCADE"))
    kind: Mapped[AssignmentKind] = mapped_column(Enum(AssignmentKind))
    completed: Mapped[bool] = mapped_column(Boolean, default=False)

    round: Mapped[ReviewRound] = relationship(back_populates="assignments", lazy="selectin")
    reviewer: Mapped[TgUser] = relationship(foreign_keys=[reviewer_id], lazy="selectin")
    reviewee: Mapped[TgUser] = relationship(foreign_keys=[reviewee_id], lazy="selectin")
    responses: Mapped[list["Response"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan", lazy="selectin"
    )


class Response(Base):
    """A single score for one competency inside an assignment."""

    __tablename__ = "responses"
    __table_args__ = (
        UniqueConstraint("assignment_id", "competency_id", name="uq_response"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"))
    competency_id: Mapped[int] = mapped_column(ForeignKey("competencies.id", ondelete="CASCADE"))
    score: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignment: Mapped[Assignment] = relationship(back_populates="responses", lazy="selectin")
    competency: Mapped[Competency] = relationship(lazy="selectin")


class Event(Base):
    """Append-only activity log.

    The gateway writes an event for every meaningful action, so usage
    statistics can be reported without instrumenting each table separately.
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class LoginToken(Base):
    """One-time token backing "log in through the bot".

    The Telegram Login Widget needs a public domain registered with BotFather,
    which rules it out for localhost and self-hosted installs. Instead the site
    mints a token, the user opens t.me/<bot>?start=login_<token> and presses
    Start, the bot confirms it, and the waiting page picks up the session.
    """

    __tablename__ = "login_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
