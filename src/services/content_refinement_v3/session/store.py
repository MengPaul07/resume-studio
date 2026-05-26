import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4


_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "session_memory"
_DB_PATH = _DATA_DIR / "session_memory.sqlite3"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _from_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        parsed = json.loads(value)
        return parsed if parsed is not None else fallback
    except Exception:
        return fallback


def _ensure_store() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _connect() -> sqlite3.Connection:
    _ensure_store()
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            resume_id TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            doc_type TEXT NOT NULL DEFAULT 'resume',
            status TEXT NOT NULL DEFAULT 'active',
            window_size INTEGER NOT NULL DEFAULT 10,
            current_version_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_resume_id ON sessions(resume_id);

        CREATE TABLE IF NOT EXISTS session_state (
            session_id TEXT PRIMARY KEY,
            raw_resume_obj_json TEXT NOT NULL DEFAULT '{}',
            normalized_resume_obj_json TEXT NOT NULL DEFAULT '{}',
            refined_resume_obj_json TEXT NOT NULL DEFAULT '{}',
            rag_context_by_path_json TEXT NOT NULL DEFAULT '{}',
            suggestion_resume_obj_json TEXT NOT NULL DEFAULT '{"items":[]}',
            review_payload_json TEXT NOT NULL DEFAULT '{"items":[]}',
            quality_report_json TEXT NOT NULL DEFAULT '{}',
            section_quality_map_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            turn_id TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS turns (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            user_message_id TEXT NOT NULL DEFAULT '',
            assistant_message_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT NOT NULL DEFAULT '',
            error_text TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS node_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            turn_id TEXT NOT NULL,
            node_name TEXT NOT NULL,
            status TEXT NOT NULL,
            duration_ms INTEGER NOT NULL DEFAULT 0,
            payload_json TEXT NOT NULL DEFAULT '{}',
            error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS session_versions (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            parent_version_id TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'state',
            turn_id TEXT NOT NULL DEFAULT '',
            refined_resume_obj_json TEXT NOT NULL DEFAULT '{}',
            suggestion_resume_obj_json TEXT NOT NULL DEFAULT '{"items":[]}',
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_messages_session_created
            ON messages(session_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_turns_session_started
            ON turns(session_id, started_at);
        CREATE INDEX IF NOT EXISTS idx_node_events_session_created
            ON node_events(session_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_node_events_turn_created
            ON node_events(turn_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_session_versions_session_created
            ON session_versions(session_id, created_at);
        """
    )
    _ensure_column(conn, "sessions", "doc_type", "TEXT NOT NULL DEFAULT 'resume'")
    conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl_fragment: str) -> None:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {str(row[1]) for row in rows}
    if column in existing:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_fragment}")


def create_session(
    *,
    title: str,
    window_size: int = 10,
    raw_resume_obj: Dict[str, Any] | None = None,
    normalized_resume_obj: Dict[str, Any] | None = None,
    refined_resume_obj: Dict[str, Any] | None = None,
    doc_type: str = "resume",
    resume_id: str = "",
) -> Dict[str, Any]:
    now = _utc_now()
    session_id = uuid4().hex
    raw = raw_resume_obj if isinstance(raw_resume_obj, dict) else {}
    normalized = normalized_resume_obj if isinstance(normalized_resume_obj, dict) else (raw or {})
    refined = refined_resume_obj if isinstance(refined_resume_obj, dict) else (normalized or raw or {})
    safe_window = max(1, min(int(window_size or 10), 50))

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO sessions (id, resume_id, title, doc_type, status, window_size, current_version_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'active', ?, '', ?, ?)
            """,
            (session_id, str(resume_id or ""), title.strip() or "Tailor Session", str(doc_type or "resume"), safe_window, now, now),
        )
        conn.execute(
            """
            INSERT INTO session_state (
                session_id,
                raw_resume_obj_json,
                normalized_resume_obj_json,
                refined_resume_obj_json,
                rag_context_by_path_json,
                suggestion_resume_obj_json,
                review_payload_json,
                quality_report_json,
                section_quality_map_json,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                _to_json(raw),
                _to_json(normalized),
                _to_json(refined),
                _to_json({}),
                _to_json({"items": []}),
                _to_json({"items": []}),
                _to_json({}),
                _to_json({}),
                now,
            ),
        )
        version_id = uuid4().hex
        conn.execute(
            """
            INSERT INTO session_versions (
                id, session_id, parent_version_id, source, turn_id, refined_resume_obj_json, suggestion_resume_obj_json, note, created_at
            )
            VALUES (?, ?, '', 'init', '', ?, ?, 'initial state', ?)
            """,
            (
                version_id,
                session_id,
                _to_json(refined),
                _to_json({"items": []}),
                now,
            ),
        )
        conn.execute(
            """
            UPDATE sessions
            SET current_version_id = ?
            WHERE id = ?
            """,
            (version_id, session_id),
        )
        conn.commit()
    return get_session(session_id, include_state=True) or {}


def get_session(session_id: str, include_state: bool = False) -> Dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, title, doc_type, status, window_size, current_version_id, resume_id, created_at, updated_at
            FROM sessions
            WHERE id = ?
            """,
            (session_id,),
        ).fetchone()
        if not row:
            return None
        session = dict(row)
        if include_state:
            session["state"] = get_session_state(session_id)
        return session


def get_session_state(session_id: str) -> Dict[str, Any]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT
                raw_resume_obj_json,
                normalized_resume_obj_json,
                refined_resume_obj_json,
                rag_context_by_path_json,
                suggestion_resume_obj_json,
                review_payload_json,
                quality_report_json,
                section_quality_map_json,
                updated_at
            FROM session_state
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        if not row:
            return {
                "raw_resume_obj": {},
                "normalized_resume_obj": {},
                "refined_resume_obj": {},
                "rag_context_by_path": {},
                "suggestion_resume_obj": {"items": []},
                "review_payload": {"items": []},
                "quality_report": {},
                "section_quality_map": {},
                "updated_at": "",
            }
        return {
            "raw_resume_obj": _from_json(row["raw_resume_obj_json"], {}),
            "normalized_resume_obj": _from_json(row["normalized_resume_obj_json"], {}),
            "refined_resume_obj": _from_json(row["refined_resume_obj_json"], {}),
            "rag_context_by_path": _from_json(row["rag_context_by_path_json"], {}),
            "suggestion_resume_obj": _from_json(row["suggestion_resume_obj_json"], {"items": []}),
            "review_payload": _from_json(row["review_payload_json"], {"items": []}),
            "quality_report": _from_json(row["quality_report_json"], {}),
            "section_quality_map": _from_json(row["section_quality_map_json"], {}),
            "updated_at": str(row["updated_at"] or ""),
        }


def save_session_state(
    *,
    session_id: str,
    raw_resume_obj: Dict[str, Any] | None = None,
    normalized_resume_obj: Dict[str, Any] | None = None,
    refined_resume_obj: Dict[str, Any] | None = None,
    rag_context_by_path: Dict[str, Any] | None = None,
    suggestion_resume_obj: Dict[str, Any] | None = None,
    review_payload: Dict[str, Any] | None = None,
    quality_report: Dict[str, Any] | None = None,
    section_quality_map: Dict[str, Any] | None = None,
) -> None:
    prev = get_session_state(session_id)
    now = _utc_now()

    raw = raw_resume_obj if isinstance(raw_resume_obj, dict) else prev.get("raw_resume_obj", {})
    normalized = (
        normalized_resume_obj if isinstance(normalized_resume_obj, dict) else prev.get("normalized_resume_obj", {})
    )
    refined = refined_resume_obj if isinstance(refined_resume_obj, dict) else prev.get("refined_resume_obj", {})
    rag = rag_context_by_path if isinstance(rag_context_by_path, dict) else prev.get("rag_context_by_path", {})
    suggestion = (
        suggestion_resume_obj
        if isinstance(suggestion_resume_obj, dict)
        else prev.get("suggestion_resume_obj", {"items": []})
    )
    review = review_payload if isinstance(review_payload, dict) else prev.get("review_payload", {"items": []})
    quality = quality_report if isinstance(quality_report, dict) else prev.get("quality_report", {})
    section_quality = (
        section_quality_map if isinstance(section_quality_map, dict) else prev.get("section_quality_map", {})
    )

    with _connect() as conn:
        conn.execute(
            """
            UPDATE session_state
            SET
                raw_resume_obj_json = ?,
                normalized_resume_obj_json = ?,
                refined_resume_obj_json = ?,
                rag_context_by_path_json = ?,
                suggestion_resume_obj_json = ?,
                review_payload_json = ?,
                quality_report_json = ?,
                section_quality_map_json = ?,
                updated_at = ?
            WHERE session_id = ?
            """,
            (
                _to_json(raw),
                _to_json(normalized),
                _to_json(refined),
                _to_json(rag),
                _to_json(suggestion),
                _to_json(review),
                _to_json(quality),
                _to_json(section_quality),
                now,
                session_id,
            ),
        )
        conn.execute(
            """
            UPDATE sessions
            SET updated_at = ?
            WHERE id = ?
            """,
            (now, session_id),
        )
        conn.commit()


def add_message(*, session_id: str, role: str, content: str, turn_id: str = "") -> Dict[str, Any]:
    now = _utc_now()
    message_id = uuid4().hex
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO messages (id, session_id, turn_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (message_id, session_id, turn_id or "", role, content, now),
        )
        conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        conn.commit()
    return {
        "id": message_id,
        "session_id": session_id,
        "turn_id": turn_id or "",
        "role": role,
        "content": content,
        "created_at": now,
    }


def list_messages(session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, session_id, turn_id, role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (session_id, max(1, int(limit))),
        ).fetchall()
    items = [dict(row) for row in rows]
    items.reverse()
    return items


def create_turn(*, session_id: str, user_message_id: str = "") -> Dict[str, Any]:
    now = _utc_now()
    turn_id = uuid4().hex
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO turns (id, session_id, user_message_id, assistant_message_id, status, started_at, ended_at, error_text)
            VALUES (?, ?, ?, '', 'running', ?, '', '')
            """,
            (turn_id, session_id, user_message_id or "", now),
        )
        conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        conn.commit()
    return {
        "id": turn_id,
        "session_id": session_id,
        "user_message_id": user_message_id or "",
        "assistant_message_id": "",
        "status": "running",
        "started_at": now,
        "ended_at": "",
        "error_text": "",
    }


def finish_turn(
    *,
    turn_id: str,
    status: str,
    assistant_message_id: str = "",
    error_text: str = "",
) -> None:
    now = _utc_now()
    with _connect() as conn:
        conn.execute(
            """
            UPDATE turns
            SET status = ?, assistant_message_id = ?, ended_at = ?, error_text = ?
            WHERE id = ?
            """,
            (status, assistant_message_id or "", now, error_text or "", turn_id),
        )
        conn.commit()


def add_node_event(
    *,
    session_id: str,
    turn_id: str,
    node_name: str,
    status: str,
    duration_ms: int = 0,
    payload: Dict[str, Any] | None = None,
    error: str = "",
) -> Dict[str, Any]:
    now = _utc_now()
    payload_data = payload if isinstance(payload, dict) else {}
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO node_events (session_id, turn_id, node_name, status, duration_ms, payload_json, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                turn_id,
                node_name,
                status,
                max(0, int(duration_ms or 0)),
                _to_json(payload_data),
                error or "",
                now,
            ),
        )
        conn.commit()
        event_id = int(cur.lastrowid or 0)
    return {
        "id": event_id,
        "session_id": session_id,
        "turn_id": turn_id,
        "node_name": node_name,
        "status": status,
        "duration_ms": max(0, int(duration_ms or 0)),
        "payload": payload_data,
        "error": error or "",
        "created_at": now,
    }


def list_node_events(session_id: str, limit: int = 200, turn_id: str = "") -> List[Dict[str, Any]]:
    with _connect() as conn:
        if turn_id:
            rows = conn.execute(
                """
                SELECT id, session_id, turn_id, node_name, status, duration_ms, payload_json, error, created_at
                FROM node_events
                WHERE session_id = ? AND turn_id = ?
                ORDER BY created_at ASC, id ASC
                LIMIT ?
                """,
                (session_id, turn_id, max(1, int(limit))),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, session_id, turn_id, node_name, status, duration_ms, payload_json, error, created_at
                FROM node_events
                WHERE session_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (session_id, max(1, int(limit))),
            ).fetchall()
    items: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["payload"] = _from_json(str(item.get("payload_json", "")), {})
        item.pop("payload_json", None)
        items.append(item)
    if not turn_id:
        items.reverse()
    return items


def get_message_by_id(message_id: str) -> Dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, session_id, turn_id, role, content, created_at
            FROM messages
            WHERE id = ?
            """,
            (message_id,),
        ).fetchone()
    return dict(row) if row else None


def get_turn(turn_id: str) -> Dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, session_id, user_message_id, assistant_message_id, status, started_at, ended_at, error_text
            FROM turns
            WHERE id = ?
            """,
            (turn_id,),
        ).fetchone()
    return dict(row) if row else None


def list_turns(session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, session_id, user_message_id, assistant_message_id, status, started_at, ended_at, error_text
            FROM turns
            WHERE session_id = ?
            ORDER BY started_at DESC, id DESC
            LIMIT ?
            """,
            (session_id, max(1, int(limit))),
        ).fetchall()
    items = [dict(row) for row in rows]
    items.reverse()
    return items


def list_sessions(limit: int = 50) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, title, doc_type, status, window_size, current_version_id, created_at, updated_at
            FROM sessions
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()
    return [dict(row) for row in rows]


def add_session_version(
    *,
    session_id: str,
    refined_resume_obj: Dict[str, Any] | None = None,
    suggestion_resume_obj: Dict[str, Any] | None = None,
    source: str = "state",
    turn_id: str = "",
    note: str = "",
    parent_version_id: str = "",
) -> Dict[str, Any]:
    now = _utc_now()
    version_id = uuid4().hex
    safe_refined = refined_resume_obj if isinstance(refined_resume_obj, dict) else {}
    safe_suggestion = suggestion_resume_obj if isinstance(suggestion_resume_obj, dict) else {"items": []}
    with _connect() as conn:
        parent = str(parent_version_id or "").strip()
        if not parent:
            row = conn.execute(
                "SELECT current_version_id FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            parent = str(row["current_version_id"] or "") if row else ""
        conn.execute(
            """
            INSERT INTO session_versions (
                id, session_id, parent_version_id, source, turn_id, refined_resume_obj_json, suggestion_resume_obj_json, note, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                session_id,
                parent,
                str(source or "state"),
                str(turn_id or ""),
                _to_json(safe_refined),
                _to_json(safe_suggestion),
                str(note or ""),
                now,
            ),
        )
        conn.execute(
            """
            UPDATE sessions
            SET current_version_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (version_id, now, session_id),
        )
        conn.commit()
    return {
        "id": version_id,
        "session_id": session_id,
        "parent_version_id": parent,
        "source": str(source or "state"),
        "turn_id": str(turn_id or ""),
        "refined_resume_obj": safe_refined,
        "suggestion_resume_obj": safe_suggestion,
        "note": str(note or ""),
        "created_at": now,
    }


def list_session_versions(session_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, session_id, parent_version_id, source, turn_id, refined_resume_obj_json, suggestion_resume_obj_json, note, created_at
            FROM session_versions
            WHERE session_id = ?
            ORDER BY created_at ASC, id ASC
            LIMIT ?
            """,
            (session_id, max(1, int(limit))),
        ).fetchall()
    out: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["refined_resume_obj"] = _from_json(str(item.get("refined_resume_obj_json", "")), {})
        item["suggestion_resume_obj"] = _from_json(str(item.get("suggestion_resume_obj_json", "")), {"items": []})
        item.pop("refined_resume_obj_json", None)
        item.pop("suggestion_resume_obj_json", None)
        out.append(item)
    return out


def get_session_version(session_id: str, version_id: str) -> Dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, session_id, parent_version_id, source, turn_id, refined_resume_obj_json, suggestion_resume_obj_json, note, created_at
            FROM session_versions
            WHERE session_id = ? AND id = ?
            """,
            (session_id, version_id),
        ).fetchone()
    if not row:
        return None
    item = dict(row)
    item["refined_resume_obj"] = _from_json(str(item.get("refined_resume_obj_json", "")), {})
    item["suggestion_resume_obj"] = _from_json(str(item.get("suggestion_resume_obj_json", "")), {"items": []})
    item.pop("refined_resume_obj_json", None)
    item.pop("suggestion_resume_obj_json", None)
    return item


def delete_sessions_by_resume_id(resume_id: str) -> int:
    """Delete all sessions and cascaded data for a given resume_id. Returns count of deleted sessions."""
    with _connect() as conn:
        # Get session IDs first for cascade
        sids = [r[0] for r in conn.execute(
            "SELECT id FROM sessions WHERE resume_id = ?", (resume_id,)
        ).fetchall()]
        if not sids:
            return 0
        for sid in sids:
            conn.execute("DELETE FROM sessions WHERE id = ?", (sid,))
        conn.commit()
        return len(sids)
