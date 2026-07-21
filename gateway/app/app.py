import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app import APP_NAME, APP_VERSION, CORS_ORIGINS, LOG_LEVEL
from app.routes import api_router, auth_router, bot_router, health_router
from app.utils.logging import setup_logging
from app.utils.openapi import save_openapi_spec

logger = logging.getLogger(__name__)


def get_application() -> FastAPI:
    setup_logging(LOG_LEVEL)

    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description=(
            "Шлюз Review 360. Единственная публичная точка входа: авторизация "
            "через Telegram, команды, раунды оценки, результаты и статистика. "
            "Данные хранит data-service, наружу он не выставлен."
        ),
        openapi_tags=[
            {"name": "Auth", "description": "Авторизация через Telegram и сессии"},
            {"name": "API", "description": "Чаты, команды, раунды оценки и результаты"},
            {"name": "Bot", "description": "Ручки для Telegram-бота (X-Bot-Token)"},
            {"name": "Health", "description": "Проверка работоспособности"},
        ],
    )

    app.include_router(auth_router.router, tags=["Auth"])
    app.include_router(api_router.router, tags=["API"])
    app.include_router(bot_router.router, tags=["Bot"])
    app.include_router(health_router.router, tags=["Health"])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    Instrumentator(should_group_status_codes=False).instrument(app).expose(
        app, endpoint="/metrics", include_in_schema=False
    )

    @app.on_event("startup")
    async def _startup() -> None:
        logger.info("%s v%s started", APP_NAME, APP_VERSION)

    return app


app = get_application()
save_openapi_spec(app)
