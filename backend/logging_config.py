"""Structlog setup and in-memory ring buffer for the log viewer."""
import logging
from collections import deque
from threading import Lock
from typing import Any

import structlog

_buffer: deque[dict[str, Any]] = deque(maxlen=500)
_buf_lock = Lock()
_seq = 0


def _buffer_processor(
    logger: Any, method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    global _seq
    with _buf_lock:
        _seq += 1
        entry: dict[str, Any] = {"seq": _seq}
        for k, v in event_dict.items():
            entry[k] = v if isinstance(v, (str, int, float, bool)) or v is None else str(v)
        _buffer.append(entry)
    return event_dict


def configure() -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _buffer_processor,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logs(since: int = 0) -> list[dict[str, Any]]:
    with _buf_lock:
        return [dict(e) for e in _buffer if e["seq"] > since]
