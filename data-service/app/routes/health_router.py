from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import APP_NAME, APP_VERSION
from app.database import async_session_maker
from app.schemas.responses import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Health-check endpoint")
async def health():
    errors: list[str] = []

    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        errors.append(f"database: {exc}")

    if errors:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"message": "Service unhealthy", "errors": errors},
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Service is working"},
    )


@router.get("/", include_in_schema=False)
async def root():
    return {"service": APP_NAME, "version": APP_VERSION, "status": "ok"}
