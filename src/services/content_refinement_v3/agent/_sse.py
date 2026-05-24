"""SSE wire format — pure functions, single source of truth."""

from __future__ import annotations

import json
from typing import Any, Generator

from ._types import TurnContext, TurnEvent


def format_event(event: TurnEvent) -> str:
    return f"event: {event.event_type}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"


def sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Low-level: format an SSE string from raw event_type + data dict."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def emit_event(event_type: str, data: dict[str, Any]):
    """Yield a generic SSE event for forwarding to the frontend."""
    yield sse_event(event_type, data)


def record_event(ctx: TurnContext, event_type: str, data: dict[str, Any]) -> None:
    """Record SSE event to ctx.sse_trace for turn logging."""
    if not hasattr(ctx, "sse_trace"):
        ctx.sse_trace = []  # type: ignore
    ctx.sse_trace.append({"event": event_type, "data": data})  # type: ignore


# ── High-level helpers used by orchestration ──

def emit_plan_updated(ctx: TurnContext, next_tool: str, reason_brief: str) -> Generator[str, None, None]:
    yield sse_event("plan.updated", {
        "turn_id": ctx.turn_id,
        "executed_steps": [s.tool for s in ctx.selected_steps],
        "next_tool": next_tool,
        "reason_brief": reason_brief,
        "intent_state": ctx.intent_state,
    })


def emit_plan_step(ctx: TurnContext, step_id: str, tool: str, reason_brief: str) -> Generator[str, None, None]:
    yield sse_event("plan.step", {
        "turn_id": ctx.turn_id,
        "step_id": step_id,
        "tool": tool,
        "reason_brief": reason_brief,
    })


def emit_step_started(ctx: TurnContext, step_id: str, tool: str) -> Generator[str, None, None]:
    yield sse_event("step.started", {
        "turn_id": ctx.turn_id,
        "step_id": step_id,
        "tool": tool,
    })


def emit_step_succeeded(ctx: TurnContext, step_id: str, tool: str, duration_ms: int, **extra: Any) -> Generator[str, None, None]:
    payload: dict[str, Any] = {
        "turn_id": ctx.turn_id,
        "step_id": step_id,
        "tool": tool,
        "duration_ms": duration_ms,
    }
    payload.update(extra)
    record_event(ctx, "step.succeeded", payload)
    yield sse_event("step.succeeded", payload)


def emit_step_failed(ctx: TurnContext, step_id: str, tool: str, error: str) -> Generator[str, None, None]:
    yield sse_event("step.failed", {
        "turn_id": ctx.turn_id,
        "step_id": step_id,
        "tool": tool,
        "error": error,
    })


def emit_turn_started(session_id: str, turn_id: str, user_message: str) -> Generator[str, None, None]:
    yield sse_event("turn.started", {
        "session_id": session_id,
        "turn_id": turn_id,
        "user_message": user_message,
    })


def emit_turn_composed(ctx: TurnContext, assistant_message: str) -> Generator[str, None, None]:
    yield sse_event("turn.composed", {
        "turn_id": ctx.turn_id,
        "assistant_message": assistant_message,
    })


def emit_turn_completed(payload: dict[str, Any]) -> Generator[str, None, None]:
    yield sse_event("turn.completed", payload)

# Note: emit_turn_completed doesn't take ctx, so can't record.
# Recording happens in run_turn_sse directly.


def emit_selfcheck_started(ctx: TurnContext) -> Generator[str, None, None]:
    yield sse_event("selfcheck.started", {
        "turn_id": ctx.turn_id,
        "retry_count": ctx.retry_count,
    })


def emit_selfcheck_completed(ctx: TurnContext, result: dict[str, Any]) -> Generator[str, None, None]:
    yield sse_event("selfcheck.completed", {
        "turn_id": ctx.turn_id,
        "retry_count": ctx.retry_count,
        "self_check_result": result,
    })


def emit_turn_restarting(ctx: TurnContext, feedback: str) -> Generator[str, None, None]:
    """Emitted when self_check triggers a full turn restart from rewrite_message."""
    yield sse_event("turn.restarting", {
        "turn_id": ctx.turn_id,
        "retry_count": ctx.retry_count,
        "feedback": feedback,
        "restart_from": "rewrite_message",
    })


def emit_thinking(ctx: TurnContext, thinking: str) -> Generator[str, None, None]:
    """Emitted after direct_edit returns its thinking process."""
    data = {"turn_id": ctx.turn_id, "text": thinking}
    if len(thinking) > 10:
        record_event(ctx, "thinking", data)
    yield sse_event("thinking", data)


def emit_reasoning(ctx: TurnContext, reasoning: str) -> Generator[str, None, None]:
    """Emitted when LLM returns its decision reasoning after seeing tool results.

    Distinct from thinking: thinking = initial analysis; reasoning = post-step
    decision rationale ("what I'll do next and why").
    """
    data = {"turn_id": ctx.turn_id, "text": reasoning}
    if len(reasoning) > 10:
        record_event(ctx, "reasoning", data)
    yield sse_event("reasoning", data)


def emit_tool_executed(ctx: TurnContext, tool_name: str, success: bool,
                       data: dict[str, Any] | None = None) -> Generator[str, None, None]:
    """Emitted after a tool executes in the agent loop."""
    payload = {"turn_id": ctx.turn_id, "tool_name": tool_name, "success": success, "data": data or {}}
    record_event(ctx, "tool.executed", payload)
    yield sse_event("tool.executed", payload)


def emit_turn_paused(ctx: TurnContext, items: list[dict[str, Any]]) -> Generator[str, None, None]:
    """Emitted when agent pauses for user confirmation (ask_user tool)."""
    data = {"turn_id": ctx.turn_id, "fact_issues": items}
    record_event(ctx, "turn.paused", data)
    yield sse_event("turn.paused", data)
