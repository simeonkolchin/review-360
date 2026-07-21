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


APP_NAME = os.getenv("BOT_NAME", "Review 360 Bot")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
# Optional SOCKS5/HTTP proxy for reaching api.telegram.org.
# Some hosts cannot route to Telegram directly; leave empty when they can.
TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY", "").strip()


GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway:8010").rstrip("/")
BOT_API_TOKEN = os.getenv("BOT_API_TOKEN", "bot-dev-token")
REQUEST_TIMEOUT_SEC = _env_int("REQUEST_TIMEOUT_SEC", 30)

SCORE_MIN = _env_int("SCORE_MIN", 1)
SCORE_MAX = _env_int("SCORE_MAX", 5)
