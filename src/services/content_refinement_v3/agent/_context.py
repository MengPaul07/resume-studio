"""Context assembly for agent loop."""

from __future__ import annotations

from typing import Any

from src.services.content_refinement_v3.backends.session import get_session_content
CHAT_WINDOW = 9999  # full history, no sliding window


def _build_context(session_id: str, message: str, target_jd: str = "") -> dict[str, Any]:
    """Centralized context assembly — single place for all context-building logic.

    Returns all the data _propose_direct_edit needs: resume, chat history, etc.
    This prevents context assembly from scattering across different functions.
    """
    snapshot = get_session_content(session_id=session_id, message_limit=CHAT_WINDOW, event_limit=200)
    state = snapshot.get("state", {}) if isinstance(snapshot.get("state", {}), dict) else {}
    full_resume = (
        state.get("refined_document_obj", {}) if isinstance(state.get("refined_document_obj", {}), dict)
        else state.get("refined_resume_obj", {}) if isinstance(state.get("refined_resume_obj", {}), dict)
        else state.get("normalized_resume_obj", {}) if isinstance(state.get("normalized_resume_obj", {}), dict)
        else {}
    )

    # Chat history — recent messages for multi-turn context
    messages = snapshot.get("messages", []) if isinstance(snapshot.get("messages", []), list) else []
    chat_history: list[dict[str, str]] = []
    for m in messages:
        if isinstance(m, dict) and m.get("content"):
            chat_history.append({
                "role": str(m.get("role", "user"))[:20],
                "content": str(m["content"])[:500],
            })

    # User memory — cross-session preferences & facts
    # user_id stored in rag_context to survive agent thread (contextvar doesn't propagate)
    rag_ctx = state.get("rag_context_by_path", {}) if isinstance(state.get("rag_context_by_path", {}), dict) else {}
    user_id = str(rag_ctx.get("__user_id__", ""))
    from src.services.content_refinement_v3.memory.preference_store import memory_to_prompt
    profile_text = memory_to_prompt(user_id) if user_id else ""

    rag_context = state.get("rag_context_by_path", {}) if isinstance(state.get("rag_context_by_path", {}), dict) else {}
    saved_target = rag_context.get("target_jd", {}) if isinstance(rag_context.get("target_jd", {}), dict) else {}
    resolved_target_jd = str(target_jd or saved_target.get("text", "") or saved_target.get("full_text", "") or "").strip()

    return {
        "full_resume": full_resume,
        "chat_history": chat_history,
        "profile_text": profile_text,
        "doc_type": state.get("doc_type", "resume"),
        "state": state,
        "target_jd": resolved_target_jd,
    }


