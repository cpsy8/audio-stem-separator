"""Atomic JSON persistence for QueueState."""
import json
import os
import threading
from pathlib import Path

from .models import QueueState


REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "queue.json"
TMP_PATH = REPO_ROOT / "queue.json.tmp"
INPUT_DIR = REPO_ROOT / "input"
OUTPUT_DIR = REPO_ROOT / "output"

_lock = threading.RLock()


def ensure_dirs() -> None:
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)


def load_state() -> QueueState:
    with _lock:
        if not STATE_PATH.exists():
            return QueueState()
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            state = QueueState.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            return QueueState()
        # crash recovery: any "running" -> "queued"
        for job in state.jobs:
            if job.status == "running":
                job.status = "queued"
                job.started_at = None
        return state


def save_state(state: QueueState) -> None:
    with _lock:
        TMP_PATH.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )
        os.replace(TMP_PATH, STATE_PATH)


def state_lock() -> threading.RLock:
    return _lock
