"""User preference memory — per-user JSON store.

Only stores preferences (writing style, tone, format preferences).
Facts about resumes are NOT stored — the agent already has full conversation
history for per-resume context, so extracting facts would be redundant.

Stored at: src/services/data/user_preferences/{userId}.json
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "user_preferences"

_locks: dict[str, threading.Lock] = {}


def _ensure_dir():
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _file_path(user_id: str) -> Path:
    return _DATA_DIR / f"{user_id}.json"


def _user_lock(user_id: str) -> threading.Lock:
    if user_id not in _locks:
        _locks[user_id] = threading.Lock()
    return _locks[user_id]


def load_memory(user_id: str) -> dict[str, Any]:
    _ensure_dir()
    fp = _file_path(user_id)
    if not fp.exists():
        return {"preferences": []}
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return {"preferences": []}


def save_memory(user_id: str, data: dict[str, Any]):
    _ensure_dir()
    fp = _file_path(user_id)
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_preference(user_id: str, key: str, value: str) -> bool:
    """Add or update a preference. Returns True if changed."""
    with _user_lock(user_id):
        data = load_memory(user_id)
        prefs: list[dict] = data.get("preferences", [])
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        for p in prefs:
            if p.get("key") == key:
                if p.get("value") == value:
                    return False
                p["value"] = value
                p["updated_at"] = now
                save_memory(user_id, data)
                return True

        prefs.append({"key": key, "value": value, "updated_at": now})
        data["preferences"] = prefs
        save_memory(user_id, data)
        return True


def memory_to_prompt(user_id: str) -> str:
    """Render the user's preferences as a structured prompt block."""
    data = load_memory(user_id)
    prefs = data.get("preferences", []) or []

    if not prefs:
        return ""

    lines = ["USER MEMORY (persisted across sessions):"]
    for p in prefs:
        lines.append(f"  - {p['value']}")
    return "\n".join(lines)
