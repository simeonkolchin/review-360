import os

from dotenv import load_dotenv

load_dotenv()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except Exception:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


APP_NAME = os.getenv("GATEWAY_NAME", "Review 360 Gateway")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
PORT = _env_int("GATEWAY_PORT", 8010)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Downstream data service (owns PostgreSQL)
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://data-service:8011").rstrip("/")
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN", "internal-service-token")
REQUEST_TIMEOUT_SEC = _env_int("REQUEST_TIMEOUT_SEC", 30)

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "")

# Auth
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_TTL_HOURS = _env_int("JWT_TTL_HOURS", 24)
AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "review360_token")
DEV_LOGIN_ENABLED = _env_bool("DEV_LOGIN_ENABLED", True)
TELEGRAM_AUTH_MAX_AGE_SEC = _env_int("TELEGRAM_AUTH_MAX_AGE_SEC", 86400)

# Token the bot uses to reach the gateway's /bot endpoints
BOT_API_TOKEN = os.getenv("BOT_API_TOKEN", "bot-dev-token")

CORS_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:8080").split(",") if o.strip()
]
