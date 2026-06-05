"""SSE wire format — pure functions, single source of truth.

All events use the ``turn.`` prefix. Event flow per turn:

    turn.started → turn.step* → turn.thinking* → turn.step_done* → turn.message → turn.completed

Optional: turn.restarting, turn.paused
"""

from __future__ import annotations

import json
from typing import Any, Generator

from ._types import TurnContext


def sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Low-level: format an SSE string from raw event_type + data dict."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def emit_event(event_type: str, data: dict[str, Any]):
    """Yield a generic SSE event for one-off types (e.g. coding_question)."""
    yield sse_event(event_type, data)


def record_event(ctx: TurnContext, event_type: str, data: dict[str, Any]) -> None:
    """Record SSE event to ctx.sse_trace for turn logging."""
    if not hasattr(ctx, "sse_trace"):
        ctx.sse_trace = []  # type: ignore
    ctx.sse_trace.append({"event": event_type, "data": data})  # type: ignore


# ── Turn lifecycle events ──────────────────────────────────────


def emit_turn_started(session_id: str, turn_id: str, user_message: str) -> Generator[str, None, None]:
    yield sse_event("turn.started", {
        "session_id": session_id,
        "turn_id": turn_id,
        "user_message": user_message,
    })


def emit_turn_step(ctx: TurnContext, step_id: str, tool: str) -> Generator[str, None, None]:
    """A new step is about to execute. Merges old plan.step + step.started."""
    yield sse_event("turn.step", {
        "turn_id": ctx.turn_id,
        "step_id": step_id,
        "tool": tool,
    })


def emit_turn_step_done(
    ctx: TurnContext,
    step_id: str,
    tool: str,
    duration_ms: int,
    *,
    status: str = "success",
    error: str = "",
    **extra: Any,
) -> Generator[str, None, None]:
    """Step finished (success or failure). Merges old step.succeeded + step.failed."""
    payload: dict[str, Any] = {
        "turn_id": ctx.turn_id,
        "step_id": step_id,
        "tool": tool,
        "status": status,
        "duration_ms": duration_ms,
    }
    if error:
        payload["error"] = error
    payload.update(extra)
    record_event(ctx, "turn.step_done", payload)
    yield sse_event("turn.step_done", payload)


def emit_turn_thinking(ctx: TurnContext, text: str) -> Generator[str, None, None]:
    """AI is thinking / reasoning. Merges old thinking + reasoning."""
    data = {"turn_id": ctx.turn_id, "text": text}
    if len(text) > 10:
        record_event(ctx, "turn.thinking", data)
    yield sse_event("turn.thinking", data)


def emit_turn_message(ctx: TurnContext, assistant_message: str) -> Generator[str, None, None]:
    """Assistant message text is ready. Replaces old turn.composed."""
    yield sse_event("turn.message", {
        "turn_id": ctx.turn_id,
        "assistant_message": assistant_message,
    })


def emit_turn_completed(payload: dict[str, Any]) -> Generator[str, None, None]:
    """Turn is finished with final payload."""
    yield sse_event("turn.completed", payload)


def emit_turn_paused(ctx: TurnContext, items: list[dict[str, Any]]) -> Generator[str, None, None]:
    """Agent paused waiting for user confirmation (ask_user tool)."""
    data = {"turn_id": ctx.turn_id, "fact_issues": items}
    record_event(ctx, "turn.paused", data)
    yield sse_event("turn.paused", data)


def emit_turn_restarting(ctx: TurnContext, feedback: str) -> Generator[str, None, None]:
    """Self-check triggered a full turn restart from rewrite_message."""
    yield sse_event("turn.restarting", {
        "turn_id": ctx.turn_id,
        "retry_count": ctx.retry_count,
        "feedback": feedback,
        "restart_from": "rewrite_message",
    })
