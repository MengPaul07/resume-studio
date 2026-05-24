"""User preference & key-fact memory — per-user JSON store.

Stored at: src/services/data/user_preferences/{userId}.json
Auto-updated after each turn by a background LLM extraction call.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "user_preferences"

# Simple write lock per user file
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
    """Load preferences and key_facts for a user."""
    _ensure_dir()
    fp = _file_path(user_id)
    if not fp.exists():
        return {"preferences": [], "key_facts": []}
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return {"preferences": [], "key_facts": []}


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
                    return False  # unchanged
                p["value"] = value
                p["updated_at"] = now
                save_memory(user_id, data)
                return True

        prefs.append({"key": key, "value": value, "updated_at": now})
        data["preferences"] = prefs
        save_memory(user_id, data)
        return True


def upsert_fact(user_id: str, key: str, value: str) -> bool:
    """Add or update a key fact. Returns True if changed."""
    with _user_lock(user_id):
        data = load_memory(user_id)
        facts: list[dict] = data.get("key_facts", [])
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        for f in facts:
            if f.get("key") == key:
                if f.get("value") == value:
                    return False
                f["value"] = value
                f["updated_at"] = now
                save_memory(user_id, data)
                return True

        facts.append({"key": key, "value": value, "updated_at": now})
        data["key_facts"] = facts
        save_memory(user_id, data)
        return True


def memory_to_prompt(user_id: str) -> str:
    """Render the user's memory as a structured prompt block.

    Returns empty string if there's nothing useful to inject.
    """
    data = load_memory(user_id)
    prefs = data.get("preferences", []) or []
    facts = data.get("key_facts", []) or []

    if not prefs and not facts:
        return ""

    lines = ["USER MEMORY (persisted across sessions):"]
    if prefs:
        lines.append("Preferences:")
        for p in prefs:
            lines.append(f"  - {p['value']}")
    if facts:
        lines.append("Key Facts:")
        for f in facts:
            lines.append(f"  - {f['value']}")
    return "\n".join(lines)
