"""Structured logging.

Records what happened to career data in a form that can be searched later,
without ever writing the data itself: log lines name entities by identifier and
kind, never by content. A log that quoted a user's career would be a second,
unmanaged copy of it — outliving the deletion guarantees the rest of this module
works to uphold.
"""

import json
import logging
from typing import Any

SAFE_KEYS = {
    "profile_id",
    "entry_id",
    "entry_type",
    "snapshot_id",
    "document_ref",
    "section",
    "count",
    "outcome",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in SAFE_KEYS:
                payload[key] = str(value)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
