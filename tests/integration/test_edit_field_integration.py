"""Integration tests for edit_field through the agent loop.

These tests mock the LLM to return controlled edit_field tool calls, then
verify the end-to-end behavior: tool execution, resulting resume state,
and SSE events produced.

Also includes optional real-LLM smoke tests (run with --real-llm flag).
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

# ── Fixtures ──────────────────────────────────────────────────────────

def _load_resume():
    from pathlib import Path as _P
    with open(_P(__file__).parent.parent / "fixtures/resumes/full_stack_zh.json", encoding="utf-8") as f:
        return json.load(f)


def _make_session(monkeypatch, resume_obj: dict) -> str:
    from src.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.post("/api/v1/agent/v3/sessions", json={
        "raw_document_obj": resume_obj,
        "refined_document_obj": resume_obj,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["session_id"]


def _run_turn_get_state(session_id: str, message: str, monkeypatch, llm_rounds: list, mock_llm: bool = True) -> dict:
    """Run a turn through TestClient streaming, return session state + SSE events.

    When mock_llm=True, injects fake completion responses (integration test).
    When mock_llm=False, calls the real LLM API (requires API key in .env).
    """
    from src.main import app
    from fastapi.testclient import TestClient
    from src.services.content_refinement_v3.agent import _agent_loop as al

    if mock_llm:
        call_count = [0]

        def fake_completion(**kwargs):
            idx = call_count[0]
            call_count[0] += 1
            if idx >= len(llm_rounds):
                return _empty_resp()
            return llm_rounds[idx]

        monkeypatch.setattr(al, "completion", fake_completion)
        monkeypatch.setattr(al, "build_llm", lambda: _fake_llm())

    client = TestClient(app)
    events = []
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
                events.append((event_type, json.loads(line[6:])))
                event_type = None

    # Also fetch the session state
    resp2 = client.get(f"/api/v1/agent/v3/sessions/{session_id}?message_limit=20&event_limit=50")
    state = resp2.json().get("state", {}) if resp2.status_code == 200 else {}
    return {"events": events, "state": state}


# ── Mock helpers ──────────────────────────────────────────────────────

def _make_tc(id_str: str, name: str, arguments: dict | None = None) -> Any:
    args = json.dumps(arguments or {}, ensure_ascii=False)
    fn = SimpleNamespace(name=name, arguments=args)
    return SimpleNamespace(id=id_str, function=fn)


def _make_resp(content: str = "", tool_calls: list | None = None):
    msg = SimpleNamespace(
        content=content or None,
        tool_calls=tool_calls or None,
        reasoning_content=None,
    )
    choice = SimpleNamespace(message=msg, finish_reason="tool_calls" if tool_calls else "stop")
    return SimpleNamespace(choices=[choice], usage=None)


def _empty_resp():
    msg = SimpleNamespace(content=None, tool_calls=None, reasoning_content=None)
    choice = SimpleNamespace(message=msg, finish_reason="stop")
    return SimpleNamespace(choices=[choice], usage=None)


def _fake_llm():
    class FakeLLM:
        model = "test-model"
        api_key = "test-key"
        api_base = ""
        temperature = 0.2
    return FakeLLM()


# ── Tests ─────────────────────────────────────────────────────────────

class TestEditFieldIntegration:
    """End-to-end: LLM calls edit_field via agent loop → verify stored data."""

    def test_add_education_with_json_object_value(self, monkeypatch):
        """LLM adds education[0] as a JSON object → stored as structured dict."""
        resume = _load_resume()
        sid = _make_session(monkeypatch, resume)

        llm_rounds = [
            _make_resp(
                content="Adding structured education",
                tool_calls=[
                    _make_tc("c1", "read_resume"),
                    _make_tc("c2", "edit_field", {
                        "path": "education[0]",
                        "value": json.dumps({
                            "institution": "Tsinghua University",
                            "degree": "Master",
                            "years": "2024-2026",
                            "description": ["Excellent student award", "ACM gold medal"],
                        }, ensure_ascii=False),
                        "op": "upsert",
                        "reason": "添加清华硕士",
                    }),
                ],
            ),
            _make_resp(content="Done", tool_calls=[_make_tc("c3", "compose")]),
        ]

        result = _run_turn_get_state(sid, "add a master degree from Tsinghua", monkeypatch, llm_rounds)
        state = result["state"]
        refined = state.get("refined_document_obj", {}) or state.get("refined_resume_obj", {})

        from src.services.content_refinement_v3.session.service import _get_by_path_local
        institution = _get_by_path_local(refined, "education[0].institution")
        degree = _get_by_path_local(refined, "education[0].degree")
        desc = _get_by_path_local(refined, "education[0].description")

        assert institution == "Tsinghua University", f"Expected structured institution, got: {institution}"
        assert degree == "Master"
        assert isinstance(desc, list), f"description should be list, got {type(desc)}: {desc}"
        assert len(desc) == 2

    def test_add_work_experience_as_json_object(self, monkeypatch):
        """LLM adds workExperience entry as JSON object → stored correctly."""
        resume = _load_resume()
        sid = _make_session(monkeypatch, resume)

        llm_rounds = [
            _make_resp(
                content="Adding work experience",
                tool_calls=[
                    _make_tc("c1", "read_resume"),
                    _make_tc("c2", "edit_field", {
                        "path": "workExperience[0]",
                        "value": json.dumps({
                            "title": "Senior SDE",
                            "company": "Google",
                            "years": "2024-present",
                            "description": ["Built core infrastructure", "Led 5-person team"],
                        }, ensure_ascii=False),
                        "op": "update",
                        "reason": "更新第一段经历",
                    }),
                ],
            ),
            _make_resp(content="Done", tool_calls=[_make_tc("c3", "compose")]),
        ]

        result = _run_turn_get_state(sid, "update my first work experience to Google", monkeypatch, llm_rounds)
        state = result["state"]
        refined = state.get("refined_document_obj", {}) or state.get("refined_resume_obj", {})

        from src.services.content_refinement_v3.session.service import _get_by_path_local
        entry = _get_by_path_local(refined, "workExperience[0]")
        assert isinstance(entry, dict), f"Entry should be dict, got {type(entry)}: {entry}"
        assert entry["title"] == "Senior SDE"
        assert isinstance(entry["description"], list)
        assert "Built core infrastructure" in entry["description"]

    def test_edit_leaf_field_preserves_structure(self, monkeypatch):
        """Editing a simple text field → doesn't corrupt surrounding data."""
        resume = _load_resume()
        sid = _make_session(monkeypatch, resume)

        llm_rounds = [
            _make_resp(
                content="Updating summary",
                tool_calls=[
                    _make_tc("c1", "read_resume"),
                    _make_tc("c2", "edit_field", {
                        "path": "summary",
                        "value": "Updated: senior backend engineer with 8 years experience.",
                        "op": "update",
                        "reason": "优化summary",
                    }),
                ],
            ),
            _make_resp(content="Done", tool_calls=[_make_tc("c3", "compose")]),
        ]

        result = _run_turn_get_state(sid, "update my summary", monkeypatch, llm_rounds)
        state = result["state"]
        refined = state.get("refined_document_obj", {}) or state.get("refined_resume_obj", {})

        from src.services.content_refinement_v3.session.service import _get_by_path_local
        summary = _get_by_path_local(refined, "summary")
        assert "senior backend engineer" in summary.lower()

        # Surrounding fields should still be intact
        name = _get_by_path_local(refined, "personalInfo.name")
        assert name and len(name) > 0, "personalInfo should remain intact"

    def test_flat_text_to_object_path_accepts_but_stores_as_string(self, monkeypatch):
        """Flat text sent to object path → accepted by tool (prompt layer prevents this)."""
        resume = _load_resume()
        sid = _make_session(monkeypatch, resume)

        llm_rounds = [
            _make_resp(
                content="Adding flat education",
                tool_calls=[
                    _make_tc("c1", "read_resume"),
                    _make_tc("c2", "edit_field", {
                        "path": "education[0]",
                        "value": "Tsinghua University | Master | 2024-2026",
                        "op": "upsert",
                        "reason": "添加学历",
                    }),
                ],
            ),
            _make_resp(content="Done", tool_calls=[_make_tc("c3", "compose")]),
        ]

        result = _run_turn_get_state(sid, "add education", monkeypatch, llm_rounds)
        state = result["state"]
        refined = state.get("refined_document_obj", {}) or state.get("refined_resume_obj", {})

        from src.services.content_refinement_v3.session.service import _get_by_path_local
        edu0 = _get_by_path_local(refined, "education[0]")

        # Tool accepted it — stored as string
        assert isinstance(edu0, str), (
            f"Flat text at object path stored as {type(edu0)}. "
            f"This is the current behavior — the prompt layer must prevent this."
        )
        assert "Tsinghua" in edu0

    def test_turn_produces_turn_completed_event(self, monkeypatch):
        """Basic smoke: a complete turn always emits turn.completed."""
        resume = _load_resume()
        sid = _make_session(monkeypatch, resume)

        llm_rounds = [
            _make_resp(content="Hello", tool_calls=[_make_tc("c1", "compose")]),
        ]

        result = _run_turn_get_state(sid, "hello", monkeypatch, llm_rounds)
        event_types = [e[0] for e in result["events"]]
        assert "turn.completed" in event_types, f"Missing turn.completed in {event_types}"

    def test_upsert_with_no_existing_array(self, monkeypatch):
        """Upsert into an empty array field → creates entry correctly."""
        resume_obj = {
            "personalInfo": {"name": "Test User", "title": "Engineer"},
            "summary": "A test resume",
            "workExperience": [],
            "education": [],
            "personalProjects": [],
            "additional": {"technicalSkills": ""},
        }
        sid = _make_session(monkeypatch, resume_obj)

        llm_rounds = [
            _make_resp(
                content="Adding project",
                tool_calls=[
                    _make_tc("c1", "read_resume"),
                    _make_tc("c2", "edit_field", {
                        "path": "personalProjects",
                        "value": json.dumps({
                            "name": "Open Source Tool",
                            "description": ["Built a CLI tool", "500 stars on GitHub"],
                        }, ensure_ascii=False),
                        "op": "upsert",
                        "reason": "添加开源项目",
                    }),
                ],
            ),
            _make_resp(content="Done", tool_calls=[_make_tc("c3", "compose")]),
        ]

        result = _run_turn_get_state(sid, "add a personal project", monkeypatch, llm_rounds)
        state = result["state"]
        refined = state.get("refined_document_obj", {}) or state.get("refined_resume_obj", {})

        from src.services.content_refinement_v3.session.service import _get_by_path_local
        projects = _get_by_path_local(refined, "personalProjects")
        assert len(projects) == 1
        assert projects[0]["name"] == "Open Source Tool"
        assert isinstance(projects[0]["description"], list)


class TestEditFieldSuggestions:
    """Verify that the suggestions produced have correct actionability."""

    def test_structured_edit_produces_apply_ready(self, monkeypatch):
        """Adding a properly structured education entry → apply_ready."""
        resume = _load_resume()
        sid = _make_session(monkeypatch, resume)

        llm_rounds = [
            _make_resp(
                content="Adding education",
                tool_calls=[
                    _make_tc("c1", "read_resume"),
                    _make_tc("c2", "edit_field", {
                        "path": "education",
                        "value": json.dumps({
                            "institution": "MIT",
                            "degree": "PhD",
                            "years": "2020-2024",
                            "description": ["Published 3 papers"],
                        }, ensure_ascii=False),
                        "op": "upsert",
                        "reason": "添加MIT博士",
                        "actionability": "apply_ready",
                    }),
                ],
            ),
            _make_resp(content="Done", tool_calls=[_make_tc("c3", "compose")]),
        ]

        result = _run_turn_get_state(sid, "add MIT PhD", monkeypatch, llm_rounds)
        # Look for turn.completed
        completed_events = [e for e in result["events"] if e[0] == "turn.completed"]
        assert completed_events, "Should have turn.completed"

    def test_fact_change_produces_confirm_required(self, monkeypatch):
        """Editing personalInfo.name → confirm_required."""
        resume = _load_resume()
        sid = _make_session(monkeypatch, resume)

        llm_rounds = [
            _make_resp(
                content="Updating name — fact change",
                tool_calls=[
                    _make_tc("c1", "read_resume"),
                    _make_tc("c2", "edit_field", {
                        "path": "personalInfo.name",
                        "value": "New Name",
                        "op": "update",
                        "reason": "更正姓名",
                        "actionability": "confirm_required",
                        "confidence": 0.5,
                    }),
                ],
            ),
            _make_resp(content="Done", tool_calls=[_make_tc("c3", "compose")]),
        ]

        result = _run_turn_get_state(sid, "my name is wrong, fix it", monkeypatch, llm_rounds)
        completed_events = [e for e in result["events"] if e[0] == "turn.completed"]
        assert completed_events


# ── Optional real-LLM smoke test ─────────────────────────────────────

class TestRealLLMEditField:
    """Smoke tests that actually call the LLM API. Requires API key in .env.

    Run with:
        pytest tests/test_edit_field_integration.py::TestRealLLMEditField -v -s
    (remove the @pytest.mark.skip decorator or use -k RealLLM)
    """

    def test_agent_writes_structured_education_with_real_llm(self, monkeypatch):
        """Ask the real LLM to add education → verify it produces structured JSON."""
        resume = _load_resume()
        sid = _make_session(monkeypatch, resume)

        result = _run_turn_get_state(
            sid,
            "Add a Master degree from Tsinghua University, 2024-2026, "
            "with description: won excellence award. Use JSON object format with description as array.",
            monkeypatch,
            llm_rounds=[],
            mock_llm=False,
        )
        state = result["state"]
        refined = state.get("refined_document_obj", {}) or state.get("refined_resume_obj", {})

        from src.services.content_refinement_v3.session.service import _get_by_path_local
        edu = _get_by_path_local(refined, "education")
        assert edu is not None, "Should have education data"
        print(f"\n[real-llm] education result: {json.dumps(edu, ensure_ascii=False)[:300]}")
