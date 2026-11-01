"""ARI-only logging, JSON lines and rotation. No stdout or global logger mutation."""

import json
import logging
import sys
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from uuid import UUID

EVENT_CODES = frozenset({"runtime_started", "runtime_start_failed", "device_operation_blocked"})


class EventFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Even accidental free-form messages and exceptions never enter the output.
        message = record.getMessage()
        event = message if message in EVENT_CODES else "unstructured_event_redacted"
        run_id = getattr(record, "run_id", None)
        return json.dumps(
            {
                "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
                "level": record.levelname,
                "event": event,
                "run_id": str(run_id) if isinstance(run_id, UUID) else "unknown",
            },
            ensure_ascii=False,
        )


def configure_logging(path: Path, run_id: UUID) -> logging.LoggerAdapter:
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ari")
    close_logging()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    formatter = EventFormatter()
    file_handler = RotatingFileHandler(path, maxBytes=1_048_576, backupCount=3, encoding="utf-8")
    stderr_handler = logging.StreamHandler(sys.stderr)
    for handler in (file_handler, stderr_handler):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logging.LoggerAdapter(logger, {"run_id": run_id})


def close_logging() -> None:
    logger = logging.getLogger("ari")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
