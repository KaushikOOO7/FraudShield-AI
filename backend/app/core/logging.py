import json
import logging


class SafeJSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"level": record.levelname, "event": record.getMessage()}
        for name in ("request_id", "route", "status_code", "duration_ms"):
            if hasattr(record, name):
                payload[name] = getattr(record, name)
        return json.dumps(payload)


def configure_logging() -> logging.Logger:
    # HTTPX INFO lines contain request URLs; provider credentials can be query parameters.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logger = logging.getLogger("fraudshield")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(SafeJSONFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
