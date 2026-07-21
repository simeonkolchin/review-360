import logging
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s:%(lineno)d %(funcName)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _SkipProbePathsAccessFilter(logging.Filter):
    """Keep /health and /metrics polling out of the access log."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not ("/metrics HTTP" in msg or "/health HTTP" in msg)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    access = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, _SkipProbePathsAccessFilter) for f in access.filters):
        access.addFilter(_SkipProbePathsAccessFilter())
