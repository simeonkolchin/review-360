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


APP_NAME = os.getenv("DATA_SERVICE_NAME", "Review 360 Data Service")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
PORT = _env_int("DATA_SERVICE_PORT", 8011)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = _env_int("DB_PORT", 5432)
DB_USER = os.getenv("DB_USER", "review360")
DB_PASS = os.getenv("DB_PASS", "review360")
DB_NAME = os.getenv("DB_NAME", "review360")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)

# Only the gateway may talk to this service — it is never exposed publicly.
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN", "internal-service-token")

SCORE_MIN = _env_int("SCORE_MIN", 1)
SCORE_MAX = _env_int("SCORE_MAX", 5)
MIN_RESPONSES_FOR_RESULTS = _env_int("MIN_RESPONSES_FOR_RESULTS", 3)

DEFAULT_COMPETENCIES = [
    ("Коммуникация", "Ясно доносит мысли, слушает и даёт обратную связь"),
    ("Ответственность", "Держит слово и доводит начатое до конца"),
    ("Экспертиза", "Владеет своей областью и качественно решает задачи"),
    ("Инициатива", "Предлагает улучшения, не ждёт указаний"),
    ("Командность", "Помогает коллегам, работает на общий результат"),
]
