"""Turning raw responses into anonymous, aggregated 360 results.

The rule that matters: peer scores are only ever exposed as an average, and
only once at least MIN_RESPONSES_FOR_RESULTS people have answered. With fewer
answers it is trivial to deduce who said what, which destroys the honesty the
method depends on.
"""

from collections import defaultdict

from app import MIN_RESPONSES_FOR_RESULTS
from app.models import Assignment, AssignmentKind, Competency, TgUser
from app.schemas.responses import (
    CompetencyScore,
    UserResponse,
    UserResultResponse,
)


def user_to_schema(user: TgUser) -> UserResponse:
    return UserResponse(
        telegram_id=user.telegram_id,
        username=user.username,
        display_name=user.display_name,
        photo_url=user.photo_url,
    )


def build_user_result(
    reviewee: TgUser,
    round_id: int,
    assignments: list[Assignment],
    competencies: list[Competency],
) -> UserResultResponse:
    """Aggregate every response about `reviewee` into per-competency scores."""

    self_scores: dict[int, int] = {}
    leader_scores: dict[int, int] = {}
    peer_scores: dict[int, list[int]] = defaultdict(list)
    comments: list[str] = []

    for assignment in assignments:
        if assignment.reviewee_id != reviewee.id:
            continue
        for response in assignment.responses:
            if assignment.kind == AssignmentKind.self_review:
                self_scores[response.competency_id] = response.score
            elif assignment.kind == AssignmentKind.leader:
                leader_scores[response.competency_id] = response.score
            else:
                peer_scores[response.competency_id].append(response.score)
            # Comments are shown detached from their author — the whole point
            # of 360 feedback is that people can be candid.
            if response.comment and response.comment.strip():
                comments.append(response.comment.strip())

    scores: list[CompetencyScore] = []
    peer_totals: list[float] = []
    self_totals: list[float] = []

    for competency in competencies:
        peers = peer_scores.get(competency.id, [])
        enough = len(peers) >= MIN_RESPONSES_FOR_RESULTS
        peer_average = round(sum(peers) / len(peers), 2) if (peers and enough) else None

        self_score = self_scores.get(competency.id)
        if self_score is not None:
            self_totals.append(self_score)
        if peer_average is not None:
            peer_totals.append(peer_average)

        scores.append(
            CompetencyScore(
                competency_id=competency.id,
                competency=competency.name,
                self_score=self_score,
                peer_average=peer_average,
                leader_score=leader_scores.get(competency.id),
                responses_count=len(peers),
                hidden_for_anonymity=bool(peers) and not enough,
            )
        )

    any_peer_hidden = any(s.hidden_for_anonymity for s in scores)
    message = None
    if any_peer_hidden:
        message = (
            f"Средние оценки коллег появятся, когда ответят минимум "
            f"{MIN_RESPONSES_FOR_RESULTS} человека — это защищает анонимность."
        )

    return UserResultResponse(
        user=user_to_schema(reviewee),
        round_id=round_id,
        scores=scores,
        overall_self=round(sum(self_totals) / len(self_totals), 2) if self_totals else None,
        overall_peer=round(sum(peer_totals) / len(peer_totals), 2) if peer_totals else None,
        comments=comments if len(comments) >= MIN_RESPONSES_FOR_RESULTS else [],
        is_available=True,
        message=message,
    )


def build_assignments_for_team(
    member_ids: list[int], leader_id: int | None
) -> list[tuple[int, int, AssignmentKind]]:
    """Produce (reviewer, reviewee, kind) triples for a whole team.

    Everyone rates themselves and every teammate. When a reviewer is the team
    leader the task is tagged `leader` so the leader's view can be reported
    separately from the peer average.
    """
    triples: list[tuple[int, int, AssignmentKind]] = []
    for reviewer in member_ids:
        for reviewee in member_ids:
            if reviewer == reviewee:
                kind = AssignmentKind.self_review
            elif leader_id is not None and reviewer == leader_id:
                kind = AssignmentKind.leader
            else:
                kind = AssignmentKind.peer
            triples.append((reviewer, reviewee, kind))
    return triples
