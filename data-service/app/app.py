import logging

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select

from app import APP_NAME, APP_VERSION, DEFAULT_COMPETENCIES, LOG_LEVEL
from app.database import Base, async_session_maker, engine
from app.models import Competency
from app.routes import data_router, health_router
from app.utils.logging import setup_logging
from app.utils.openapi import save_openapi_spec

logger = logging.getLogger(__name__)


async def init_database() -> None:
    """Create tables and seed the default competency set."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        existing = await session.scalar(select(Competency).limit(1))
        if existing is None:
            for position, (name, description) in enumerate(DEFAULT_COMPETENCIES):
                session.add(Competency(name=name, description=description, position=position))
            await session.commit()
            logger.info("Seeded %s default competencies", len(DEFAULT_COMPETENCIES))


def get_application() -> FastAPI:
    setup_logging(LOG_LEVEL)

    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description=(
            "Хранилище Review 360: пользователи, чаты, команды, раунды оценки, "
            "ответы и статистика. Доступен только шлюзу по X-Service-Token."
        ),
        openapi_tags=[
            {"name": "Data", "description": "CRUD и агрегация данных оценки"},
            {"name": "Health", "description": "Проверка работоспособности сервиса и БД"},
        ],
    )

    app.include_router(data_router.router, tags=["Data"])
    app.include_router(health_router.router, tags=["Health"])

    Instrumentator(should_group_status_codes=False).instrument(app).expose(
        app, endpoint="/metrics", include_in_schema=False
    )

    @app.on_event("startup")
    async def _startup() -> None:
        await init_database()
        logger.info("%s v%s started", APP_NAME, APP_VERSION)

    return app


app = get_application()
save_openapi_spec(app)
