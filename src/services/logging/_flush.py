"""Flush optional TurnTracer spans to separate trace logs.

Production agent turns use agent/_turn_log.py. This module is kept for explicit
span debugging and no longer writes to the compact manual turn log directory.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._trace import TurnTracer

logger = logging.getLogger(__name__)

_OUTPUT_DIR = Path(__file__).resolve().parents[3] / "outputs"
_TRACE_LOG_DIR = _OUTPUT_DIR / "trace_logs"
_MAX_JSON_AGE_DAYS = 7
_DEBUG_LOG_PATH = _OUTPUT_DIR / "turn_tracer_debug.txt"
_DEBUG_LOG_MAX_BYTES = 5 * 1024 * 1024  # 5MB
_DEBUG_LOG_BACKUPS = 4


def _ensure_dirs() -> None:
    _TRACE_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _rotate_debug_log() -> None:
    """Rotate turn_tracer_debug.txt if it exceeds max size."""
    path = _DEBUG_LOG_PATH
    if not path.exists():
        return
    size = path.stat().st_size
    if size < _DEBUG_LOG_MAX_BYTES:
        return
    for i in range(_DEBUG_LOG_BACKUPS - 1, -1, -1):
        src = path if i == 0 else path.with_name(f"{path.name}.{i}")
        dst = path.with_name(f"{path.name}.{i + 1}")
        if src.exists():
            dst.write_text(src.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    path.write_text("", encoding="utf-8")


def _cleanup_old_json_logs() -> None:
    """Remove JSON logs older than _MAX_JSON_AGE_DAYS."""
    cutoff = time.time() - _MAX_JSON_AGE_DAYS * 86400
    if not _TRACE_LOG_DIR.exists():
        return
    for day_dir in _TRACE_LOG_DIR.iterdir():
        if not day_dir.is_dir():
            continue
        try:
            mtime = day_dir.stat().st_mtime
            if mtime < cutoff:
                import shutil
                shutil.rmtree(day_dir, ignore_errors=True)
                logger.info("[flush] cleaned old log dir: %s", day_dir.name)
        except Exception:
            pass


def flush_turn_tracer(
    tracer: TurnTracer,
    *,
    session_id: str,
    turn_id: str,
    message: str,
    db_path: str,
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist all spans to an optional JSON trace log.

    Normal agent turns use content_refinement_v3/agent/_turn_log.py. The db_path
    argument is kept for old call sites, but SQLite span storage is
    retired so this function no longer creates a second production log path.
    """
    _ensure_dirs()
    _rotate_debug_log()
    _cleanup_old_json_logs()

    now = datetime.now(timezone.utc)
    iso = now.isoformat()
    day_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M%S")

    meta = tracer.meta()
    trace_data = {
        "timestamp": iso,
        "session_id": session_id,
        "turn_id": turn_id,
        "message": str(message or "")[:300],
        "meta": meta,
        "spans": [s.to_dict() for s in tracer.spans],
        "result": result or {},
    }

    # 1. JSON log
    try:
        day_dir = _TRACE_LOG_DIR / day_str
        day_dir.mkdir(parents=True, exist_ok=True)
        sess_short = session_id[:8] if len(session_id) >= 8 else session_id
        turn_short = turn_id[:8] if len(turn_id) >= 8 else turn_id
        json_path = day_dir / f"{time_str}_{sess_short}_{turn_short}.json"
        json_path.write_text(json.dumps(trace_data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        logger.warning("[flush] JSON write failed: %s", exc)

    if db_path:
        logger.debug("[flush] db_path ignored; SQLite span storage is retired")

    # 2. Debug log (agent_loop.txt style, but structured)
    try:
        lines = [f"[turn] {iso} session={session_id[:12]} turn={turn_id[:12]} msg={str(message or '')[:80]}"]
        for span in tracer.spans:
            lines.append(f"  [{span.name}] {span.status} {span.duration_ms}ms {json.dumps(span.data, ensure_ascii=False)[:200]}")
        _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        _rotate_debug_log()
    except Exception:
        pass

    return trace_data
