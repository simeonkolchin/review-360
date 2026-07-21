from pydantic import BaseModel


class HealthResponse(BaseModel):
    message: str
    errors: list[str] | None = None


class UserResponse(BaseModel):
    telegram_id: int
    username: str | None = None
    display_name: str
    photo_url: str | None = None


class MemberResponse(UserResponse):
    can_dm: bool = False
    is_admin: bool = False


class ChatResponse(BaseModel):
    id: int
    telegram_chat_id: int
    title: str
    member_count: int
    team_count: int


class TeamResponse(BaseModel):
    id: int
    name: str
    leader: UserResponse | None = None
    members: list[UserResponse] = []
    active_round_id: int | None = None


class CompetencyResponse(BaseModel):
    id: int
    name: str
    description: str | None = None


class QuestionnaireResponse(BaseModel):
    """Which questionnaire applies, and where it came from.

    `source` is what lets the UI say "inherited from the chat" instead of
    pretending every team configured itself.
    """

    source: str  # team | chat | default
    competencies: list[CompetencyResponse]


class ParticipantProgress(BaseModel):
    """Where one reviewer is in the round — the live view a leader watches."""

    user: UserResponse
    # not_started — has not answered anything yet
    # in_progress — some answers submitted
    # done        — every assignment finished
    state: str
    completed: int
    total: int
    can_dm: bool


class RoundProgressResponse(BaseModel):
    id: int
    team_id: int
    team_name: str
    status: str
    token: str
    bot_deep_link: str | None = None
    total_assignments: int
    completed_assignments: int
    participants_done: int
    participants_total: int
    participants: list[ParticipantProgress] = []
    competencies: list["CompetencyResponse"] = []


class CompetencyScore(BaseModel):
    competency_id: int
    competency: str
    self_score: float | None = None
    peer_average: float | None = None
    leader_score: float | None = None
    responses_count: int = 0
    hidden_for_anonymity: bool = False


class UserResultResponse(BaseModel):
    user: UserResponse
    round_id: int
    scores: list[CompetencyScore]
    overall_self: float | None = None
    overall_peer: float | None = None
    comments: list[str] = []
    is_available: bool = True
    message: str | None = None


class TeamResultsResponse(BaseModel):
    round_id: int
    team_name: str
    status: str
    competencies: list[CompetencyResponse]
    members: list[UserResultResponse]


class AssignmentResponse(BaseModel):
    id: int
    reviewee: UserResponse
    kind: str
    completed: bool


class BotTaskResponse(BaseModel):
    round_id: int
    team_name: str
    competencies: list[CompetencyResponse]
    assignments: list[AssignmentResponse]
