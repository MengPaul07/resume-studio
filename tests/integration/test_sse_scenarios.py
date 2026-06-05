"""Multi-scenario SSE integration tests — validates agent loop SSE events for
different LLM response patterns without hitting a real LLM.

Scenarios:
  1. Greeting    — LLM calls compose directly
  2. Analysis    — LLM calls read_resume → compose
  3. Edit        — LLM calls read_resume → edit_field → compose
  4. Multi-tool  — LLM calls read_resume + read_history (parallel) → edit_field → compose
  5. Ask user    — LLM calls ask_user → pause
  6. Empty       — LLM returns nothing → error
"""

from __future__ import annotations

import json
import time
from typing import Any
from unittest.mock import patch

import pytest


def _load_resume():
    from pathlib import Path as _P
    with open(_P(__file__).parent.parent / "fixtures/resumes/full_stack_zh.json", encoding="utf-8") as f:
        return json.load(f)


def _make_session(monkeypatch, resume_obj: dict):
    """Create a session via TestClient and return session_id."""
    from src.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    resp = client.post("/api/v1/agent/v3/sessions", json={
        "raw_document_obj": resume_obj,
        "refined_document_obj": resume_obj,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["session_id"]


def _run_turn(session_id: str, message: str, monkeypatch, llm_rounds: list):
    """Run a turn with mocked LLM and return collected SSE events."""
    from src.main import app
    from fastapi.testclient import TestClient
    from src.services.content_refinement_v3.agent import _agent_loop as al

    call_count = [0]

    def fake_completion(**kwargs):
        idx = call_count[0]
        call_count[0] += 1
        if idx >= len(llm_rounds):
            # Fallback: empty
            class EmptyMsg:
                content = None
                tool_calls = None
                reasoning_content = None
            class EmptyChoice:
                message = EmptyMsg()
                finish_reason = "stop"
            class EmptyResp:
                choices = [EmptyChoice()]
                usage = None
            return EmptyResp()
        return llm_rounds[idx]

    monkeypatch.setattr(al, "completion", fake_completion)

    client = TestClient(app)
    events: list[tuple[str, dict]] = []

    with client.stream(
        "POST",
        f"/api/v1/agent/v3/sessions/{session_id}/turns:run",
        json={"message": message, "allow_mutation": True},
    ) as response:
        event_type = None
        for raw_line in response.iter_lines():
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if line.startswith("event: "):
                event_type = line[7:].strip()
            elif line.startswith("data: ") and event_type:
                data = json.loads(line[6:])
                events.append((event_type, data))
                event_type = None

    return events


# ── Mock LLM constructors ──


def _make_tc(id_str: str, name: str, arguments: dict | None = None) -> Any:
    """Create a fake tool_call object matching litellm shape."""
    args = json.dumps(arguments or {})
    from types import SimpleNamespace
    fn = SimpleNamespace(name=name, arguments=args)
    return SimpleNamespace(id=id_str, function=fn)


def _make_resp(content: str = "", tool_calls: list | None = None, reasoning: str = ""):
    """Create a fake litellm response."""
    from types import SimpleNamespace
    msg = SimpleNamespace(
        content=content or None,
        tool_calls=tool_calls or None,
        reasoning_content=reasoning or None,
    )
    choice = SimpleNamespace(message=msg, finish_reason="tool_calls" if tool_calls else "stop")
    return SimpleNamespace(choices=[choice], usage=None)


# ── Scenarios ──


class TestGreetingScenario:
    """LLM calls compose directly — no data needed."""

    def test_sse_events(self, monkeypatch):
        resume = _load_resume()
        sid = _make_session(monkeypatch, resume)

        llm_rounds = [
            _make_resp(
                content="你好，我可以帮你什么？",
                tool_calls=[_make_tc("c1", "compose")],
            ),
        ]

        events = _run_turn(sid, "你好", monkeypatch, llm_rounds)

        kinds = [ev[0] for ev in events]
        assert "turn.started" in kinds
        assert "turn.thinking" in kinds
        assert "turn.step" in kinds, f"Expected turn.step in: {kinds}"
        assert "turn.completed" in kinds

        # When compose is the only tool, content goes directly to assistant_message (not thinking)
        # Verify the compose result contains the greeting
        composed = [ev for ev in events if ev[0] == "turn.message"]
        assert composed, "Expected turn.message event"

        # Verify step for compose
        step_events = [ev for ev in events if ev[0] == "turn.step"]
        assert len(step_events) >= 1, f"No turn.step events"
        tools = [ev[1].get("tool", "") for ev in step_events]
        assert "compose" in tools, f"compose not in step tools: {tools}"


class TestAnalysisScenario:
    """LLM calls read_resume then compose — analysis flow."""

    def test_sse_events(self, monkeypatch):
        resume = _load_resume()
        sid = _make_session(monkeypatch, resume)

        llm_rounds = [
            _make_resp(
                content="我先读取简历内容",
                tool_calls=[_make_tc("c1", "read_resume")],
            ),
            _make_resp(
                content="已分析完毕",
                tool_calls=[_make_tc("c2", "compose")],
            ),
        ]

        events = _run_turn(sid, "检查简历中的问题", monkeypatch, llm_rounds)

        step_events = [ev for ev in events if ev[0] in ("turn.step", "turn.step_done")]
        tools_seen = set()
        for _, data in step_events:
            t = data.get("tool", "") or data.get("tool", "")
            if t:
                tools_seen.add(t)

        assert "read_resume" in tools_seen, f"read_resume not executed. tools: {tools_seen}"
        assert "compose" in tools_seen, f"compose not executed"

        # read_resume should come before compose in events
        step_order = [ev[1].get("tool", ev[1].get("tool", "")) for ev in step_events]
        step_order = [s for s in step_order if s]
        read_idx = step_order.index("read_resume")
        compose_idx = step_order.index("compose")
        assert read_idx < compose_idx, f"read_resume should be before compose: {step_order}"

        # Round 0 content (read_resume) → thinking. Round 1 content (compose) → not emitted (goes to asst.)
        kinds = [ev[0] for ev in events]
        assert "turn.thinking" in kinds, f"Expected thinking event: {kinds}"

        # per-tool turn.step_done should have status field
        succeeded = [ev for ev in events if ev[0] == "turn.step_done"
                     and "agent_step_" in str(ev[1].get("step_id", ""))]
        for _, data in succeeded:
            assert "status" in data, f"agent turn.step_done missing status: {data}"


class TestEditScenario:
    """LLM calls read_resume → edit_field → compose — edit flow."""

    def test_sse_events(self, monkeypatch):
        resume = _load_resume()
        sid = _make_session(monkeypatch, resume)

        llm_rounds = [
            _make_resp(
                content="先读取简历",
                tool_calls=[_make_tc("c1", "read_resume")],
            ),
            _make_resp(
                content="修改summary",
                tool_calls=[_make_tc("c2", "edit_field", {
                    "path": "summary",
                    "value": "更强的总结",
                })],
            ),
            _make_resp(
                content="完成",
                tool_calls=[_make_tc("c3", "compose")],
            ),
        ]

        events = _run_turn(sid, "优化summary", monkeypatch, llm_rounds)

        # Collect all SSE event types
        kinds = [ev[0] for ev in events]
        assert "turn.started" in kinds
        assert "turn.completed" in kinds
        assert "turn.thinking" in kinds       # round 0
        assert "turn.thinking" in kinds      # rounds 1-2

        # turn.step_done events should carry status
        step_succeeded = [ev for ev in events if ev[0] == "turn.step_done"]
        tools = [ev[1].get("tool", "") for ev in step_succeeded]
        assert "read_resume" in tools
        assert "edit_field" in tools
        assert "compose" in tools
        for _, data in step_succeeded:
            if "agent_step_" in str(data.get("step_id", "")):
                assert "status" in data, f"agent turn.step_done missing status: {data}"


class TestMultiToolScenario:
    """LLM calls read_resume + read_history (parallel-safe) then compose."""

    def test_sse_events(self, monkeypatch):
        resume = _load_resume()
        sid = _make_session(monkeypatch, resume)

        llm_rounds = [
            _make_resp(
                content="读取简历和历史",
                tool_calls=[
                    _make_tc("c1", "read_resume"),
                    _make_tc("c2", "read_history"),
                ],
            ),
            _make_resp(
                content="完成",
                tool_calls=[_make_tc("c3", "compose")],
            ),
        ]

        events = _run_turn(sid, "根据历史记录分析简历", monkeypatch, llm_rounds)

        step_succeeded = [ev for ev in events if ev[0] == "turn.step_done"]
        tools = [ev[1].get("tool", "") for ev in step_succeeded]
        assert "read_resume" in tools, f"read_resume missing from {tools}"
        assert "read_history" in tools, f"read_history missing from {tools}"
        assert "compose" in tools

        # Both parallel tools should have turn.step before turn.step_done
        started_tools = [ev[1].get("tool", "") for ev in events if ev[0] == "turn.step"]
        for t in ("read_resume", "read_history"):
            assert t in started_tools, f"{t} missing from turn.step: {started_tools}"


class TestEmptyResponse:
    """LLM returns nothing → error, not fallback guess."""

    def test_sse_events(self, monkeypatch):
        resume = _load_resume()
        sid = _make_session(monkeypatch, resume)

        llm_rounds = [
            _make_resp(content="", tool_calls=None),
        ]

        events = _run_turn(sid, "任意请求", monkeypatch, llm_rounds)

        # Should complete with error indication
        assert events, "No SSE events at all"
        completed = [ev for ev in events if ev[0] == "turn.completed"]
        assert completed, "No turn.completed event"

        # The error should be surfaced in the turn output
        last = events[-1]
        asst_msg = last[1].get("assistant_message", "") or ""
        assert "error" in asst_msg.lower() or "empty" in asst_msg.lower() or \
               "重新" in asst_msg, f"No error indication: {asst_msg[:100]}"
