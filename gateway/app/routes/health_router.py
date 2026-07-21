import httpx
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app import APP_NAME, APP_VERSION, DATA_SERVICE_URL

router = APIRouter()


@router.get("/health", summary="Health-check endpoint")
async def health():
    errors: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(f"{DATA_SERVICE_URL}/health")
        if response.status_code >= 400:
            errors.append(f"data-service: status={response.status_code}")
    except Exception as exc:
        errors.append(f"data-service: {exc}")

    if errors:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"message": "Service unhealthy", "errors": errors},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK, content={"message": "Service is working"}
    )


@router.get("/", include_in_schema=False)
async def root():
    return {"service": APP_NAME, "version": APP_VERSION, "status": "ok"}
