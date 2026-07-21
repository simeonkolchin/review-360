"""HTTP client for the data service.

The gateway owns no database of its own — every read and write goes through
here, which keeps persistence in exactly one place.
"""

import logging

import httpx
from fastapi import HTTPException

from app import DATA_SERVICE_URL, REQUEST_TIMEOUT_SEC, SERVICE_TOKEN

logger = logging.getLogger(__name__)

HEADERS = {"X-Service-Token": SERVICE_TOKEN}


async def request(method: str, path: str, **kwargs):
    url = f"{DATA_SERVICE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=float(REQUEST_TIMEOUT_SEC)) as client:
            response = await client.request(method, url, headers=HEADERS, **kwargs)
    except Exception as exc:
        logger.error("data-service unreachable: %s", exc)
        raise HTTPException(503, f"data-service unavailable: {exc}") from exc

    if response.status_code >= 400:
        detail = response.text
        try:
            detail = response.json().get("detail", detail)
        except Exception:
            pass
        raise HTTPException(response.status_code, detail)

    if response.status_code == 204 or not response.content:
        return None
    return response.json()


async def get(path: str, **kwargs):
    return await request("GET", path, **kwargs)


async def post(path: str, **kwargs):
    return await request("POST", path, **kwargs)


async def put(path: str, **kwargs):
    return await request("PUT", path, **kwargs)


async def delete(path: str, **kwargs):
    return await request("DELETE", path, **kwargs)


async def record_event(kind: str, telegram_id: int | None = None, **payload) -> None:
    """Fire-and-forget usage statistics — never break a request over analytics."""
    try:
        await post(
            "/events",
            json={"kind": kind, "telegram_id": telegram_id, "payload": payload or None},
        )
    except Exception as exc:
        logger.warning("failed to record event %s: %s", kind, exc)
