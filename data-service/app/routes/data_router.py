"""Internal data API. Only the gateway calls this — never exposed publicly."""

import json
import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import SCORE_MAX, SCORE_MIN, SERVICE_TOKEN
from app.database import get_session
from app.engine.aggregation import build_assignments_for_team, build_user_result, user_to_schema
from app.models import (
    Assignment,
    Chat,
    Competency,
    Event,
    LoginToken,
    Membership,
    ReviewRound,
    Response,
    RoundStatus,
    Team,
    TeamMember,
    TgUser,
)
from app.schemas.requests import (
    EnrollRequest,
    EventRequest,
    TeamCreateRequest,
    SubmitResponsesRequest,
)
from app.schemas.responses import (
    AssignmentResponse,
    BotTaskResponse,
    ChatResponse,
    CompetencyResponse,
    MemberResponse,
    RoundProgressResponse,
    TeamResponse,
    TeamResultsResponse,
    UserResponse,
)

router = APIRouter()


async def _reload(session: AsyncSession, model, pk: int):
    """Re-read an entity after commit.

    `session.get()` would hand back the identity-mapped instance whose
    relationships were never loaded, and touching them then triggers a lazy
    (sync) load inside async context -> MissingGreenlet. Expunging first forces
    a real SELECT so the selectin loaders run.
    """
    session.expunge_all()
    return await session.scalar(select(model).where(model.id == pk))




async def require_service_token(x_service_token: str = Header(default="")) -> None:
    if not secrets.compare_digest(x_service_token, SERVICE_TOKEN):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid service token")


# --------------------------------------------------------------------------- users


@router.post("/users/upsert", response_model=UserResponse, dependencies=[Depends(require_service_token)])
async def upsert_user(payload: dict, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(TgUser).where(TgUser.telegram_id == payload["telegram_id"]))
    if user is None:
        user = TgUser(telegram_id=payload["telegram_id"])
        session.add(user)
    for field in ("username", "first_name", "last_name", "photo_url"):
        if payload.get(field):
            setattr(user, field, payload[field])
    await session.commit()
    await session.refresh(user)
    return user_to_schema(user)


# --------------------------------------------------------------------------- chats


@router.post("/enroll", dependencies=[Depends(require_service_token)])
async def enroll(payload: EnrollRequest, session: AsyncSession = Depends(get_session)):
    """A user tapped 'join' in a group, or opened the bot privately."""
    user = await session.scalar(select(TgUser).where(TgUser.telegram_id == payload.telegram_id))
    if user is None:
        user = TgUser(telegram_id=payload.telegram_id)
        session.add(user)
    for field in ("username", "first_name", "last_name", "photo_url"):
        if getattr(payload, field, None):
            setattr(user, field, getattr(payload, field))
    await session.flush()

    chat = await session.scalar(
        select(Chat).where(Chat.telegram_chat_id == payload.telegram_chat_id)
    )
    if chat is None:
        chat = Chat(
            telegram_chat_id=payload.telegram_chat_id,
            title=payload.chat_title,
            added_by_id=user.id,
        )
        session.add(chat)
        await session.flush()
    elif payload.chat_title:
        chat.title = payload.chat_title

    membership = await session.scalar(
        select(Membership).where(
            Membership.chat_id == chat.id, Membership.tg_user_id == user.id
        )
    )
    if membership is None:
        membership = Membership(chat_id=chat.id, tg_user_id=user.id)
        session.add(membership)
    if payload.can_dm:
        membership.can_dm = True
    if payload.is_admin:
        membership.is_admin = True

    await session.commit()
    return {"chat_id": chat.id, "telegram_id": user.telegram_id, "enrolled": True}


@router.get("/chats", response_model=list[ChatResponse], dependencies=[Depends(require_service_token)])
async def list_chats(telegram_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(TgUser).where(TgUser.telegram_id == telegram_id))
    if user is None:
        return []
    chat_ids = list(
        await session.scalars(select(Membership.chat_id).where(Membership.tg_user_id == user.id))
    )
    if not chat_ids:
        return []
    chats = await session.scalars(select(Chat).where(Chat.id.in_(chat_ids)))
    return [
        ChatResponse(
            id=c.id,
            telegram_chat_id=c.telegram_chat_id,
            title=c.title,
            member_count=len(c.memberships),
            team_count=len(c.teams),
        )
        for c in chats
    ]


async def _get_chat_for_user(session: AsyncSession, chat_id: int, telegram_id: int) -> Chat:
    chat = await session.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
    if not any(m.tg_user.telegram_id == telegram_id for m in chat.memberships):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this chat")
    return chat


@router.get(
    "/chats/{chat_id}/members",
    response_model=list[MemberResponse],
    dependencies=[Depends(require_service_token)],
)
async def chat_members(chat_id: int, telegram_id: int, session: AsyncSession = Depends(get_session)):
    chat = await _get_chat_for_user(session, chat_id, telegram_id)
    return [
        MemberResponse(
            telegram_id=m.tg_user.telegram_id,
            username=m.tg_user.username,
            display_name=m.tg_user.display_name,
            photo_url=m.tg_user.photo_url,
            can_dm=m.can_dm,
            is_admin=m.is_admin,
        )
        for m in chat.memberships
    ]


# --------------------------------------------------------------------------- teams


def _team_to_schema(team: Team) -> TeamResponse:
    active = next((r.id for r in team.rounds if r.status == RoundStatus.active), None)
    return TeamResponse(
        id=team.id,
        name=team.name,
        leader=user_to_schema(team.leader) if team.leader else None,
        members=[user_to_schema(m.tg_user) for m in team.members],
        active_round_id=active,
    )


@router.get(
    "/chats/{chat_id}/teams",
    response_model=list[TeamResponse],
    dependencies=[Depends(require_service_token)],
)
async def list_teams(chat_id: int, telegram_id: int, session: AsyncSession = Depends(get_session)):
    chat = await _get_chat_for_user(session, chat_id, telegram_id)
    return [_team_to_schema(t) for t in chat.teams]


@router.post(
    "/chats/{chat_id}/teams",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_service_token)],
)
async def create_team(
    chat_id: int,
    telegram_id: int,
    payload: TeamCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    chat = await _get_chat_for_user(session, chat_id, telegram_id)

    allowed = {m.tg_user.telegram_id: m.tg_user for m in chat.memberships}
    unknown = set(payload.member_telegram_ids) - set(allowed)
    if unknown:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Users not enrolled in chat: {sorted(unknown)}"
        )
    if payload.leader_telegram_id and payload.leader_telegram_id not in allowed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Leader is not enrolled in the chat")
    if len(payload.member_telegram_ids) < 2:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A team needs at least 2 members")

    team = Team(
        chat_id=chat.id,
        name=payload.name,
        leader_id=allowed[payload.leader_telegram_id].id if payload.leader_telegram_id else None,
    )
    session.add(team)
    await session.flush()
    for tg_id in payload.member_telegram_ids:
        session.add(TeamMember(team_id=team.id, tg_user_id=allowed[tg_id].id))
    await session.commit()

    return _team_to_schema(await _reload(session, Team, team.id))


@router.delete("/teams/{team_id}", dependencies=[Depends(require_service_token)])
async def delete_team(team_id: int, session: AsyncSession = Depends(get_session)):
    team = await session.get(Team, team_id)
    if team is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
    await session.delete(team)
    await session.commit()
    return {"message": "deleted"}


# --------------------------------------------------------------------------- rounds


def _progress(round_: ReviewRound) -> RoundProgressResponse:
    total = len(round_.assignments)
    done = sum(1 for a in round_.assignments if a.completed)
    by_reviewer: dict[int, list[Assignment]] = {}
    for a in round_.assignments:
        by_reviewer.setdefault(a.reviewer_id, []).append(a)
    return RoundProgressResponse(
        id=round_.id,
        team_id=round_.team_id,
        team_name=round_.team.name,
        status=round_.status.value,
        token=round_.token,
        total_assignments=total,
        completed_assignments=done,
        participants_done=sum(1 for t in by_reviewer.values() if all(x.completed for x in t)),
        participants_total=len(by_reviewer),
    )


@router.post(
    "/teams/{team_id}/rounds",
    response_model=RoundProgressResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_service_token)],
)
async def start_round(team_id: int, session: AsyncSession = Depends(get_session)):
    team = await session.get(Team, team_id)
    if team is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
    if any(r.status == RoundStatus.active for r in team.rounds):
        raise HTTPException(status.HTTP_409_CONFLICT, "Team already has an active round")

    member_ids = [m.tg_user_id for m in team.members]
    if len(member_ids) < 2:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A team needs at least 2 members")

    round_ = ReviewRound(team_id=team.id, status=RoundStatus.active, token=secrets.token_urlsafe(16))
    session.add(round_)
    await session.flush()
    for reviewer_id, reviewee_id, kind in build_assignments_for_team(member_ids, team.leader_id):
        session.add(
            Assignment(round_id=round_.id, reviewer_id=reviewer_id, reviewee_id=reviewee_id, kind=kind)
        )
    await session.commit()
    return _progress(await _reload(session, ReviewRound, round_.id))


@router.get(
    "/rounds/{round_id}",
    response_model=RoundProgressResponse,
    dependencies=[Depends(require_service_token)],
)
async def get_round(round_id: int, session: AsyncSession = Depends(get_session)):
    round_ = await session.get(ReviewRound, round_id)
    if round_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Round not found")
    return _progress(round_)


@router.post(
    "/rounds/{round_id}/close",
    response_model=RoundProgressResponse,
    dependencies=[Depends(require_service_token)],
)
async def close_round(round_id: int, session: AsyncSession = Depends(get_session)):
    round_ = await session.get(ReviewRound, round_id)
    if round_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Round not found")
    round_.status = RoundStatus.closed
    round_.closed_at = datetime.now(UTC)
    await session.commit()
    return _progress(await _reload(session, ReviewRound, round_id))


@router.get(
    "/rounds/{round_id}/results",
    response_model=TeamResultsResponse,
    dependencies=[Depends(require_service_token)],
)
async def round_results(round_id: int, session: AsyncSession = Depends(get_session)):
    round_ = await session.get(ReviewRound, round_id)
    if round_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Round not found")
    competencies = list(await session.scalars(select(Competency).order_by(Competency.position)))
    assignments = list(round_.assignments)
    return TeamResultsResponse(
        round_id=round_.id,
        team_name=round_.team.name,
        status=round_.status.value,
        competencies=[
            CompetencyResponse(id=c.id, name=c.name, description=c.description) for c in competencies
        ],
        members=[
            build_user_result(m.tg_user, round_.id, assignments, competencies)
            for m in round_.team.members
        ],
    )


# --------------------------------------------------------------------------- bot flow


@router.get(
    "/bot/tasks", response_model=BotTaskResponse, dependencies=[Depends(require_service_token)]
)
async def bot_tasks(token: str, telegram_id: int, session: AsyncSession = Depends(get_session)):
    """What this user still has to fill in for the round behind `token`."""
    round_ = await session.scalar(select(ReviewRound).where(ReviewRound.token == token))
    if round_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Round not found")
    if round_.status != RoundStatus.active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Round is not active")

    user = await session.scalar(select(TgUser).where(TgUser.telegram_id == telegram_id))
    if user is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not part of this round")

    mine = [a for a in round_.assignments if a.reviewer_id == user.id]
    if not mine:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not part of this round")

    competencies = list(await session.scalars(select(Competency).order_by(Competency.position)))
    return BotTaskResponse(
        round_id=round_.id,
        team_name=round_.team.name,
        competencies=[
            CompetencyResponse(id=c.id, name=c.name, description=c.description) for c in competencies
        ],
        assignments=[
            AssignmentResponse(
                id=a.id,
                reviewee=user_to_schema(a.reviewee),
                kind=a.kind.value,
                completed=a.completed,
            )
            for a in mine
        ],
    )


@router.post("/bot/responses", dependencies=[Depends(require_service_token)])
async def submit_responses(
    payload: SubmitResponsesRequest, session: AsyncSession = Depends(get_session)
):
    assignment = await session.get(Assignment, payload.assignment_id)
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")

    for item in payload.responses:
        if payload.comment_only:
            # Only attach the note; never touch the score that was already saved
            existing = await session.scalar(
                select(Response).where(
                    Response.assignment_id == assignment.id,
                    Response.competency_id == item.competency_id,
                )
            )
            if existing is not None:
                existing.comment = item.comment
            continue
        if not SCORE_MIN <= item.score <= SCORE_MAX:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Score must be between {SCORE_MIN} and {SCORE_MAX}",
            )
        existing = await session.scalar(
            select(Response).where(
                Response.assignment_id == assignment.id,
                Response.competency_id == item.competency_id,
            )
        )
        if existing:
            existing.score = item.score
            existing.comment = item.comment
        else:
            session.add(
                Response(
                    assignment_id=assignment.id,
                    competency_id=item.competency_id,
                    score=item.score,
                    comment=item.comment,
                )
            )

    await session.flush()
    total_competencies = await session.scalar(select(func.count(Competency.id)))
    answered = await session.scalar(
        select(func.count(Response.id)).where(Response.assignment_id == assignment.id)
    )
    assignment.completed = answered >= total_competencies
    await session.commit()

    return {"assignment_id": assignment.id, "completed": assignment.completed}


@router.get("/bot/results", dependencies=[Depends(require_service_token)])
async def bot_results(telegram_id: int, session: AsyncSession = Depends(get_session)):
    """Latest closed-round results for a user, for display inside the bot."""
    user = await session.scalar(select(TgUser).where(TgUser.telegram_id == telegram_id))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    member_rows = list(await session.scalars(select(TeamMember).where(TeamMember.tg_user_id == user.id)))
    competencies = list(await session.scalars(select(Competency).order_by(Competency.position)))

    for tm in sorted(member_rows, key=lambda r: r.id, reverse=True):
        team = await session.get(Team, tm.team_id)
        for round_ in sorted(team.rounds, key=lambda r: r.id, reverse=True):
            if round_.status == RoundStatus.closed:
                result = build_user_result(user, round_.id, list(round_.assignments), competencies)
                return {
                    "found": True,
                    "team_name": team.name,
                    "is_leader": team.leader_id == user.id,
                    "result": result.model_dump(),
                }
    return {"found": False}


# --------------------------------------------------------------------------- stats


@router.post("/events", dependencies=[Depends(require_service_token)])
async def record_event(payload: EventRequest, session: AsyncSession = Depends(get_session)):
    session.add(
        Event(
            kind=payload.kind,
            telegram_id=payload.telegram_id,
            chat_id=payload.chat_id,
            payload=json.dumps(payload.payload, ensure_ascii=False) if payload.payload else None,
        )
    )
    await session.commit()
    return {"recorded": True}


@router.get("/stats", dependencies=[Depends(require_service_token)])
async def stats(session: AsyncSession = Depends(get_session)):
    counts = {
        "users": await session.scalar(select(func.count(TgUser.id))),
        "chats": await session.scalar(select(func.count(Chat.id))),
        "teams": await session.scalar(select(func.count(Team.id))),
        "rounds": await session.scalar(select(func.count(ReviewRound.id))),
        "responses": await session.scalar(select(func.count(Response.id))),
        "events": await session.scalar(select(func.count(Event.id))),
    }
    by_kind = await session.execute(select(Event.kind, func.count(Event.id)).group_by(Event.kind))
    return {"counts": counts, "events_by_kind": {k: v for k, v in by_kind.all()}}


# --------------------------------------------------------------------------- login via bot

LOGIN_TOKEN_TTL_SEC = 600


@router.post("/login-tokens", dependencies=[Depends(require_service_token)])
async def create_login_token(session: AsyncSession = Depends(get_session)):
    token = secrets.token_urlsafe(24)
    session.add(LoginToken(token=token))
    await session.commit()
    return {"token": token}


@router.post("/login-tokens/confirm", dependencies=[Depends(require_service_token)])
async def confirm_login_token(payload: dict, session: AsyncSession = Depends(get_session)):
    """Called by the bot once the user pressed Start on the deep link."""
    record = await session.scalar(
        select(LoginToken).where(LoginToken.token == payload["token"])
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown login token")
    if record.consumed:
        raise HTTPException(status.HTTP_409_CONFLICT, "Token already used")

    age = (datetime.now(UTC) - record.created_at).total_seconds()
    if age > LOGIN_TOKEN_TTL_SEC:
        raise HTTPException(status.HTTP_410_GONE, "Login token expired")

    user = await session.scalar(
        select(TgUser).where(TgUser.telegram_id == payload["telegram_id"])
    )
    if user is None:
        user = TgUser(telegram_id=payload["telegram_id"])
        session.add(user)
    for field in ("username", "first_name", "last_name", "photo_url"):
        if payload.get(field):
            setattr(user, field, payload[field])

    record.telegram_id = payload["telegram_id"]
    record.confirmed = True
    await session.commit()
    return {"confirmed": True}


@router.post("/login-tokens/consume", dependencies=[Depends(require_service_token)])
async def consume_login_token(payload: dict, session: AsyncSession = Depends(get_session)):
    """Polled by the site; returns the user once (then the token is burned)."""
    record = await session.scalar(
        select(LoginToken).where(LoginToken.token == payload["token"])
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown login token")
    if not record.confirmed:
        return {"confirmed": False}
    if record.consumed:
        raise HTTPException(status.HTTP_409_CONFLICT, "Token already used")

    record.consumed = True
    user = await session.scalar(select(TgUser).where(TgUser.telegram_id == record.telegram_id))
    await session.commit()
    return {"confirmed": True, "user": user_to_schema(user).model_dump()}
