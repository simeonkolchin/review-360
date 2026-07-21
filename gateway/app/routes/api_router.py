"""Public API consumed by the frontend. Every endpoint requires a session."""

from fastapi import APIRouter, Depends, status

from app.schemas.requests import TeamCreateRequest
from app.services import data_client
from app.services.security import get_current_user_id
from app.services.telegram import deep_link, mention, send_message

router = APIRouter()


@router.get("/chats", summary="Chats I belong to")
async def list_chats(telegram_id: int = Depends(get_current_user_id)):
    return await data_client.get("/chats", params={"telegram_id": telegram_id})


@router.get("/chats/{chat_id}/members", summary="Members who enrolled themselves")
async def list_members(chat_id: int, telegram_id: int = Depends(get_current_user_id)):
    return await data_client.get(
        f"/chats/{chat_id}/members", params={"telegram_id": telegram_id}
    )


@router.get("/chats/{chat_id}/teams", summary="Teams in a chat")
async def list_teams(chat_id: int, telegram_id: int = Depends(get_current_user_id)):
    return await data_client.get(f"/chats/{chat_id}/teams", params={"telegram_id": telegram_id})


@router.post(
    "/chats/{chat_id}/teams", status_code=status.HTTP_201_CREATED, summary="Create a team"
)
async def create_team(
    chat_id: int,
    payload: TeamCreateRequest,
    telegram_id: int = Depends(get_current_user_id),
):
    team = await data_client.post(
        f"/chats/{chat_id}/teams",
        params={"telegram_id": telegram_id},
        json=payload.model_dump(),
    )
    await data_client.record_event(
        "team_created", telegram_id, team_id=team["id"], members=len(team["members"])
    )
    return team


@router.delete("/teams/{team_id}", summary="Delete a team")
async def delete_team(team_id: int, telegram_id: int = Depends(get_current_user_id)):
    result = await data_client.delete(f"/teams/{team_id}")
    await data_client.record_event("team_deleted", telegram_id, team_id=team_id)
    return result


@router.post(
    "/teams/{team_id}/rounds",
    status_code=status.HTTP_201_CREATED,
    summary="Start a review round",
)
async def start_round(team_id: int, telegram_id: int = Depends(get_current_user_id)):
    """Creates the round, then announces it in the group with a deep link."""
    round_ = await data_client.post(f"/teams/{team_id}/rounds")

    # Find the chat and members so the announcement can tag everyone.
    chats = await data_client.get("/chats", params={"telegram_id": telegram_id})
    link = deep_link(round_["token"])
    round_["bot_deep_link"] = link

    for chat in chats:
        teams = await data_client.get(
            f"/chats/{chat['id']}/teams", params={"telegram_id": telegram_id}
        )
        team = next((t for t in teams if t["id"] == team_id), None)
        if not team:
            continue
        if link:
            mentions = " ".join(
                mention(m["display_name"], m["telegram_id"]) for m in team["members"]
            )
            text = (
                f"🎯 <b>Стартовала оценка 360</b> — команда «{team['name']}»\n\n"
                f"{mentions}\n\n"
                "Нажмите кнопку ниже: бот откроется и сразу начнёт опрос.\n"
                "Оценки анонимны — никто не увидит, кто какую поставил."
            )
            await send_message(
                chat["telegram_chat_id"],
                text,
                reply_markup={"inline_keyboard": [[{"text": "Пройти оценку", "url": link}]]},
            )
        break

    await data_client.record_event("round_started", telegram_id, round_id=round_["id"])
    return round_


@router.get("/rounds/{round_id}", summary="Round progress")
async def get_round(round_id: int, telegram_id: int = Depends(get_current_user_id)):
    round_ = await data_client.get(f"/rounds/{round_id}")
    round_["bot_deep_link"] = deep_link(round_["token"])
    return round_


@router.post("/rounds/{round_id}/close", summary="Close a round")
async def close_round(round_id: int, telegram_id: int = Depends(get_current_user_id)):
    round_ = await data_client.post(f"/rounds/{round_id}/close")
    await data_client.record_event("round_closed", telegram_id, round_id=round_id)
    return round_


@router.get("/rounds/{round_id}/results", summary="Aggregated team results")
async def round_results(round_id: int, telegram_id: int = Depends(get_current_user_id)):
    await data_client.record_event("results_viewed", telegram_id, round_id=round_id)
    return await data_client.get(f"/rounds/{round_id}/results")


@router.get("/stats", summary="Usage statistics")
async def stats(telegram_id: int = Depends(get_current_user_id)):
    return await data_client.get("/stats")
