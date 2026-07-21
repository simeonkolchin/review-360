"""Public API consumed by the frontend. Every endpoint requires a session."""

import re

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.schemas.requests import QuestionnaireRequest, TeamCreateRequest
from app.services import data_client
from app.services.security import get_current_user_id
from app.services.telegram import (
    chat_status,
    sync_members,
    deep_link,
    fetch_file,
    leave_chat as telegram_leave,
    mention,
    send_message,
)

router = APIRouter()

# Telegram file paths look like "photos/file_12.jpg" — nothing else is allowed
# through, so this endpoint can never be pointed somewhere it should not go.
SAFE_FILE_PATH = re.compile(r"^[\w][\w./-]{0,127}$")


@router.get("/avatar/{file_path:path}", summary="Proxy a Telegram profile photo")
async def avatar(file_path: str, _: int = Depends(get_current_user_id)):
    """Serve an avatar without ever exposing the bot token to the browser.

    The bot stores `tg:<file_path>`; the frontend asks for it here and we stream
    the bytes back — which also works for clients that cannot reach Telegram.
    """
    if ".." in file_path or not SAFE_FILE_PATH.match(file_path):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad file path")

    result = await fetch_file(file_path)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar unavailable")

    content, content_type = result
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )


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


@router.get("/chats/{chat_id}/telegram", summary="What Telegram says about this group")
async def chat_telegram_status(chat_id: int, telegram_id: int = Depends(get_current_user_id)):
    """Explain a short roster: how many people the group really has, and whether
    the bot is an admin — without which it cannot see anyone who is not writing
    to it directly."""
    chats = await data_client.get("/chats", params={"telegram_id": telegram_id})
    chat = next((c for c in chats if c["id"] == chat_id), None)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    info = await chat_status(chat["telegram_chat_id"])

    # The group became a supergroup and changed id — follow it, then ask again.
    if info.get("migrate_to"):
        await data_client.post("/chats/migrate", json={
            "from_chat_id": chat["telegram_chat_id"],
            "to_chat_id": info["migrate_to"],
        })
        info = await chat_status(info["migrate_to"])

    # The group photo is usually set after the bot joins; save it when it shows up.
    if info["photo_url"] and info["photo_url"] != chat.get("photo_url"):
        await data_client.post(
            f"/chats/{chat_id}/photo", json={"photo_url": info["photo_url"]}
        )

    return {
        "known": chat["member_count"],
        "member_count": info["member_count"],
        "bot_is_admin": info["bot_is_admin"],
        "bot_in_chat": info["bot_in_chat"],
    }


@router.post("/chats/{chat_id}/sync", summary="Re-read who is in the group")
async def sync_chat_members(chat_id: int, telegram_id: int = Depends(get_current_user_id)):
    """Pull in everyone Telegram will confirm is a member.

    There is no "list members" call, but `getChatMember` answers for a person we
    can name — so we ask about every id the system already knows. Combined with
    the admin list that recovers most of a roster without waiting for people to
    post something.
    """
    chats = await data_client.get("/chats", params={"telegram_id": telegram_id})
    chat = next((c for c in chats if c["id"] == chat_id), None)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    target = chat["telegram_chat_id"]
    info = await chat_status(target)
    if info.get("migrate_to"):
        await data_client.post("/chats/migrate", json={
            "from_chat_id": target, "to_chat_id": info["migrate_to"],
        })
        target = info["migrate_to"]
        info = await chat_status(target)

    known = await data_client.get("/users/ids")
    added = await sync_members(target, chat["title"], known.get("telegram_ids", []))

    await data_client.record_event("chat_synced", telegram_id, chat_id=chat_id, added=added)
    return {
        "added": added,
        "member_count": info.get("member_count"),
        "bot_is_admin": info.get("bot_is_admin"),
    }


# ------------------------------------------------------------------ questionnaires


@router.get("/chats/{chat_id}/questionnaire", summary="Questionnaire used across a chat")
async def chat_questionnaire(chat_id: int, _: int = Depends(get_current_user_id)):
    return await data_client.get(f"/chats/{chat_id}/questionnaire")


@router.put("/chats/{chat_id}/questionnaire", summary="Edit the chat questionnaire")
async def save_chat_questionnaire(
    chat_id: int, payload: QuestionnaireRequest, telegram_id: int = Depends(get_current_user_id)
):
    saved = await data_client.put(
        f"/chats/{chat_id}/questionnaire", json=payload.model_dump()
    )
    await data_client.record_event(
        "questionnaire_saved", telegram_id, scope="chat", chat_id=chat_id,
        questions=len(saved["competencies"]),
    )
    return saved


@router.delete("/chats/{chat_id}/questionnaire", summary="Back to the built-in questionnaire")
async def reset_chat_questionnaire(chat_id: int, telegram_id: int = Depends(get_current_user_id)):
    result = await data_client.delete(f"/chats/{chat_id}/questionnaire")
    await data_client.record_event("questionnaire_reset", telegram_id, chat_id=chat_id)
    return result


@router.post(
    "/chats/{chat_id}/questionnaire/apply",
    summary="Push the chat questionnaire onto every team",
)
async def apply_chat_questionnaire(chat_id: int, telegram_id: int = Depends(get_current_user_id)):
    result = await data_client.post(f"/chats/{chat_id}/questionnaire/apply")
    await data_client.record_event("questionnaire_applied", telegram_id, chat_id=chat_id, **result)
    return result


@router.get("/teams/{team_id}/questionnaire", summary="Questionnaire this team will use")
async def team_questionnaire(team_id: int, _: int = Depends(get_current_user_id)):
    return await data_client.get(f"/teams/{team_id}/questionnaire")


@router.put("/teams/{team_id}/questionnaire", summary="Give this team its own questionnaire")
async def save_team_questionnaire(
    team_id: int, payload: QuestionnaireRequest, telegram_id: int = Depends(get_current_user_id)
):
    saved = await data_client.put(f"/teams/{team_id}/questionnaire", json=payload.model_dump())
    await data_client.record_event(
        "questionnaire_saved", telegram_id, scope="team", team_id=team_id,
        questions=len(saved["competencies"]),
    )
    return saved


@router.delete("/teams/{team_id}/questionnaire", summary="Fall back to the chat questionnaire")
async def reset_team_questionnaire(team_id: int, telegram_id: int = Depends(get_current_user_id)):
    result = await data_client.delete(f"/teams/{team_id}/questionnaire")
    await data_client.record_event("questionnaire_reset", telegram_id, team_id=team_id)
    return result


@router.delete("/chats/{chat_id}", summary="Delete a chat and leave the group")
async def delete_chat(chat_id: int, telegram_id: int = Depends(get_current_user_id)):
    """Wipe everything for a chat, then make the bot leave the Telegram group.

    Deletion happens first: if the bot cannot leave (already removed, network
    blip) the data is gone regardless, which is what the user asked for.
    """
    result = await data_client.delete(
        f"/chats/{chat_id}", params={"telegram_id": telegram_id}
    )
    if result.get("telegram_chat_id"):
        await telegram_leave(result["telegram_chat_id"])
    await data_client.record_event(
        "chat_deleted", telegram_id, chat_id=chat_id, teams=result.get("teams", 0)
    )
    return result


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
