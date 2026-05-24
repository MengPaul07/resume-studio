"""V3-facing session backend facade.

The v3 agent loop still reuses the existing session persistence primitives.
Keeping those imports behind this facade prevents public v3 routes/tools from
depending on legacy route/module names directly.
"""

from src.services.content_refinement_v3.session.service import (
    _normalize_suggestion_document_obj,
    _tasks_to_suggestion_items,
    get_session_content,
    partial_execute_task,
    partial_generate_suggest,
    rollback_to_version,
    start_session,
)
from src.services.content_refinement_v3.session.store import (
    add_message,
    add_node_event,
    add_session_version,
    create_turn,
    finish_turn,
    get_session,
    list_node_events,
    save_session_state,
)

__all__ = [
    "_normalize_suggestion_document_obj",
    "_tasks_to_suggestion_items",
    "add_message",
    "add_node_event",
    "add_session_version",
    "create_turn",
    "finish_turn",
    "get_session",
    "get_session_content",
    "list_node_events",
    "partial_execute_task",
    "partial_generate_suggest",
    "_tasks_to_suggestion_items",
    "rollback_to_version",
    "save_session_state",
    "start_session",
]
