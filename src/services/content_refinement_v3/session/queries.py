from typing import Any, Dict, List

from .store import (
    get_message_by_id,
    get_session,
    get_turn,
    list_messages,
    list_node_events,
    list_sessions,
    list_turns,
)


def _as_dict(value: Any, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {} if default is None else default


def _to_text(value: Any) -> str:
    return str(value or "").strip()


def build_actions_brief(
    *,
    session_id: str,
    all_actions_turn_limit: int,
    all_actions_event_limit_per_turn: int,
    max_text_len: int = 9000,
) -> Dict[str, Any]:
    turns = list_turns(session_id=session_id, limit=all_actions_turn_limit)
    lines: List[str] = []
    items: List[Dict[str, Any]] = []
    for idx, turn in enumerate(turns, start=1):
        turn_id = str(turn.get("id", ""))
        user_msg = get_message_by_id(str(turn.get("user_message_id", ""))) if turn.get("user_message_id") else None
        user_text = _to_text((user_msg or {}).get("content", ""))
        if len(user_text) > 60:
            user_text = user_text[:60] + "..."

        events = list_node_events(
            session_id=session_id,
            turn_id=turn_id,
            limit=all_actions_event_limit_per_turn,
        )
        step_parts: List[str] = []
        for event in events:
            node_name = _to_text(event.get("node_name", ""))
            status = _to_text(event.get("status", ""))
            if not node_name:
                continue
            short_status = "ok" if status == "success" else ("fail" if status == "failed" else status)
            step_parts.append(f"{node_name}:{short_status}")

        steps = " > ".join(step_parts) if step_parts else "no-steps"
        result = _to_text(turn.get("status", "unknown")) or "unknown"
        line = f"{idx}. {steps} | result={result}"
        if user_text:
            line += f" | user={user_text}"
        lines.append(line)
        items.append(
            {
                "turn_id": turn_id,
                "steps": step_parts,
                "result": result,
                "user": user_text,
            }
        )

    text = "\n".join(lines)
    truncated = False
    if len(text) > max_text_len:
        text = text[:max_text_len] + "\n... [truncated]"
        truncated = True
    return {
        "count": len(items),
        "items": items,
        "text": text,
        "truncated": truncated,
    }


def get_messages(*, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    return list_messages(session_id, limit=limit)


def get_node_events(*, session_id: str, limit: int = 200, turn_id: str = "") -> List[Dict[str, Any]]:
    return list_node_events(session_id, limit=limit, turn_id=turn_id)


def read_actions(
    *,
    session_id: str,
    turn_id: str = "",
    limit: int = 50,
    all_actions_turn_limit: int,
    all_actions_event_limit_per_turn: int,
) -> Dict[str, Any]:
    if turn_id:
        turn = get_turn(turn_id)
        if not turn or str(turn.get("session_id", "")) != session_id:
            raise ValueError("turn not found")
        turns = [turn]
    else:
        turns = list_turns(session_id=session_id, limit=all_actions_turn_limit)

    items: List[Dict[str, Any]] = []
    for turn in turns:
        current_turn_id = str(turn.get("id", ""))
        user_message = get_message_by_id(str(turn.get("user_message_id", ""))) if turn.get("user_message_id") else None
        assistant_message = (
            get_message_by_id(str(turn.get("assistant_message_id", "")))
            if turn.get("assistant_message_id")
            else None
        )
        events = list_node_events(session_id=session_id, turn_id=current_turn_id)
        items.append(
            {
                "turn": turn,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "node_events": events,
            }
        )

    actions_brief = build_actions_brief(
        session_id=session_id,
        all_actions_turn_limit=all_actions_turn_limit,
        all_actions_event_limit_per_turn=all_actions_event_limit_per_turn,
    )
    return {
        "session_id": session_id,
        "turn_count": len(items),
        "items": items,
        "actions_brief": actions_brief,
    }


def get_sessions_list(*, limit: int = 50) -> Dict[str, Any]:
    items = list_sessions(limit=limit)
    return {
        "count": len(items),
        "items": items,
    }


def get_session_content(
    *,
    session_id: str,
    message_limit: int,
    event_limit: int,
    all_actions_turn_limit: int,
    all_actions_event_limit_per_turn: int,
) -> Dict[str, Any]:
    session = get_session(session_id, include_state=True)
    if not session:
        raise ValueError("session not found")

    raw_state = session.get("state", {}) if isinstance(session.get("state", {}), dict) else {}
    state = {
        "raw_document_obj": _as_dict(raw_state.get("raw_resume_obj", {})),
        "normalized_document_obj": _as_dict(raw_state.get("normalized_resume_obj", {})),
        "refined_document_obj": _as_dict(raw_state.get("refined_resume_obj", {})),
        "suggestion_document_obj": _as_dict(raw_state.get("suggestion_resume_obj", {"items": []}), {"items": []}),
        "review_payload": _as_dict(raw_state.get("review_payload", {"items": []}), {"items": []}),
        "rag_context_by_path": _as_dict(raw_state.get("rag_context_by_path", {})),
        "quality_report": _as_dict(raw_state.get("quality_report", {})),
        "section_quality_map": _as_dict(raw_state.get("section_quality_map", {})),
    }

    return {
        "session": {
            "id": str(session.get("id", "")),
            "doc_type": str(session.get("doc_type", "resume")),
            "title": str(session.get("title", "")),
            "status": str(session.get("status", "")),
            "window_size": int(session.get("window_size", 10) or 10),
            "created_at": str(session.get("created_at", "")),
            "updated_at": str(session.get("updated_at", "")),
        },
        "state": state,
        "messages": list_messages(session_id=session_id, limit=message_limit),
        "node_events": list_node_events(session_id=session_id, limit=event_limit),
        "actions_brief": build_actions_brief(
            session_id=session_id,
            all_actions_turn_limit=all_actions_turn_limit,
            all_actions_event_limit_per_turn=all_actions_event_limit_per_turn,
        ),
    }


def check_session(*, session_id: str) -> Dict[str, Any]:
    session = get_session(session_id, include_state=True)
    if not session:
        return {
            "ok": False,
            "session_id": session_id,
            "status": "not_found",
            "checks": {
                "session_exists": False,
                "resume_exists": False,
                "last_turn_failed": False,
            },
        }

    state = session.get("state", {}) if isinstance(session.get("state", {}), dict) else {}
    resume_exists = bool(state.get("refined_resume_obj", {})) or bool(state.get("normalized_resume_obj", {}))
    turns = list_turns(session_id=session_id, limit=1)
    last_turn = turns[-1] if turns else {}
    last_turn_failed = str(last_turn.get("status", "")) == "failed"

    ok = bool(resume_exists) and not last_turn_failed
    return {
        "ok": ok,
        "session_id": session_id,
        "status": "healthy" if ok else "degraded",
        "checks": {
            "session_exists": True,
            "resume_exists": bool(resume_exists),
            "last_turn_failed": bool(last_turn_failed),
        },
        "last_turn": last_turn,
    }
