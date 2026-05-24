"""Lightweight tracing — Span + TurnTracer, inspired by LangSmith."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class Span:
    span_id: str
    parent_id: str | None
    name: str
    start: float
    end: float = 0
    status: str = "ok"
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> int:
        return max(0, int((self.end - self.start) * 1000)) if self.end else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "data": self.data,
        }

    def to_db_row(self, session_id: str, turn_id: str, seq: int) -> tuple:
        import json
        return (
            session_id,
            turn_id,
            self.span_id,
            self.parent_id or "",
            self.name,
            self.status,
            self.duration_ms,
            json.dumps(self.data, ensure_ascii=False),
            seq,
        )


class TurnTracer:
    def __init__(self) -> None:
        self._spans: list[Span] = []
        self._stack: list[Span] = []  # parent stack

    def start_span(self, name: str, **data: Any) -> Span:
        parent = self._stack[-1] if self._stack else None
        span = Span(
            span_id=uuid4().hex[:12],
            parent_id=parent.span_id if parent else None,
            name=name,
            start=time.perf_counter(),
            data=data,
        )
        self._spans.append(span)
        self._stack.append(span)
        return span

    def end_span(self, span: Span, status: str = "ok", **data: Any) -> None:
        span.end = time.perf_counter()
        span.status = status
        span.data.update(data)
        if self._stack and self._stack[-1] is span:
            self._stack.pop()

    @property
    def spans(self) -> list[Span]:
        return list(self._spans)

    def to_dict(self) -> dict[str, Any]:
        return {"spans": [s.to_dict() for s in self._spans]}

    def meta(self) -> dict[str, Any]:
        total_ms = 0
        total_tokens = 0
        model = ""
        for s in self._spans:
            if s.name == "llm.call":
                total_tokens += s.data.get("prompt_tokens", 0) + s.data.get("completion_tokens", 0)
                model = s.data.get("model", model)
            total_ms = max(total_ms, int((s.end - self._spans[0].start) * 1000)) if s.end and self._spans else 0
        return {"model": model, "total_tokens": total_tokens, "total_duration_ms": total_ms}
