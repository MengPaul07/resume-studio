"""Core dataclasses for the agent loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Unified return contract for every tool function."""
    success: bool
    tool_name: str
    data: dict[str, Any]
    meta: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: int = 0


@dataclass
class StepRecord:
    step_id: str
    tool: str
    status: str
    duration_ms: int
    reason_brief: str


@dataclass
class TurnContext:
    """Explicit state object replacing mutable closure variables."""
    session_id: str
    turn_id: str
    message: str
    allow_mutation: bool
    max_steps: int = 6

    selected_steps: list[StepRecord] = field(default_factory=list)
    step_outputs: dict[str, ToolResult] = field(default_factory=dict)
    observed_payload: dict[str, Any] = field(default_factory=dict)
    latest_suggest_payload: dict[str, Any] = field(default_factory=dict)
    latest_refine_payload: dict[str, Any] = field(default_factory=dict)
    turn_output_bundle: dict[str, Any] = field(default_factory=dict)
    planner_decision_trace: list[dict[str, Any]] = field(default_factory=list)
    intent_state: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    self_check_feedback: str = ""
    last_self_check: dict[str, Any] = field(default_factory=lambda: {"result": "pass", "reason": "not_run"})
    termination_reason: str = "finish"


@dataclass
class TurnEvent:
    """Structured event decoupled from SSE wire format."""
    event_type: str
    turn_id: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        from ._sse import format_event
        return format_event(self)
