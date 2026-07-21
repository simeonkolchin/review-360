"""Endpoints the Telegram bot calls. Protected by X-Bot-Token."""

from fastapi import APIRouter, Depends

from app.schemas.requests import EnrollRequest, SubmitResponsesRequest
from app.services import data_client
from app.services.security import require_bot_token

router = APIRouter(prefix="/bot", dependencies=[Depends(require_bot_token)])


@router.post("/enroll", summary="Register a user who joined from a group")
async def enroll(payload: EnrollRequest):
    result = await data_client.post("/enroll", json=payload.model_dump())
    await data_client.record_event(
        "enrolled", payload.telegram_id, chat=payload.telegram_chat_id
    )
    return result


@router.post("/leave", summary="Someone left the group")
async def leave(payload: dict):
    return await data_client.post("/leave", json=payload)


@router.post("/reachable", summary="This user has opened the bot, so we may DM them")
async def reachable(payload: dict):
    return await data_client.post("/reachable", json=payload)


@router.get("/tasks", summary="What this user still has to evaluate")
async def tasks(token: str, telegram_id: int):
    return await data_client.get(
        "/bot/tasks", params={"token": token, "telegram_id": telegram_id}
    )


@router.post("/responses", summary="Submit scores for one assignment")
async def responses(payload: SubmitResponsesRequest, telegram_id: int):
    result = await data_client.post("/bot/responses", json=payload.model_dump())
    await data_client.record_event(
        "response_submitted", telegram_id, assignment_id=payload.assignment_id
    )
    return result


@router.get("/results", summary="Own results for display inside the bot")
async def results(telegram_id: int):
    await data_client.record_event("results_viewed_bot", telegram_id)
    return await data_client.get("/bot/results", params={"telegram_id": telegram_id})


@router.post("/confirm-login", summary="Bot confirms a website login")
async def confirm_login(payload: dict):
    return await data_client.post("/login-tokens/confirm", json=payload)
