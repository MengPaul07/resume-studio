"""Integration tests for the agent loop and context assembly.

These tests catch issues that would otherwise only surface in frontend testing:
- Cross-module references (e.g., CHAT_WINDOW)
- Agent loop SSE event structure
- Empty response / error handling
- Tool execution ordering
"""

from __future__ import annotations

import pytest


# ── _build_context integration tests ──


class TestBuildContext:
    """Verify context assembly works end-to-end with mocked session."""

    @pytest.fixture
    def build_context(self):
        from src.services.content_refinement_v3.agent._context import _build_context

        return _build_context

    def test_chat_window_defined(self):
        """CHAT_WINDOW must be accessible from _context.py (was missing after module split)."""
        from src.services.content_refinement_v3.agent._context import CHAT_WINDOW

        assert CHAT_WINDOW == 9999  # full history, no sliding window

    def test_build_context_basic(self, build_context, monkeypatch):
        """_build_context should return correct keys with mocked session."""
        from src.services.content_refinement_v3.agent import _context

        def fake_get_session_content(*, session_id, message_limit, event_limit):
            return {
                "state": {
                    "refined_document_obj": {"summary": "test resume"},
                    "doc_type": "resume",
                },
                "messages": [
                    {"role": "user", "content": "hello"},
                    {"role": "assistant", "content": "hi there"},
                ],
            }

        monkeypatch.setattr(_context, "get_session_content", fake_get_session_content)

        result = build_context("test_session", "test message")

        assert "full_resume" in result
        assert "chat_history" in result
        assert "profile_text" in result
        assert "doc_type" in result
        assert result["full_resume"] == {"summary": "test resume"}
        assert result["doc_type"] == "resume"
        assert len(result["chat_history"]) == 2


# ── Agent loop integration tests ──


class TestAgentLoopIntegration:
    """Test _run_agent_loop with mocked LLM to verify SSE and response structure."""

    @pytest.fixture
    def run_loop(self):
        from src.services.content_refinement_v3.agent._agent_loop import _run_agent_loop

        return _run_agent_loop

    @pytest.fixture
    def ctx(self):
        from src.services.content_refinement_v3.agent._types import TurnContext

        return TurnContext(
            session_id="test_session",
            turn_id="test_turn",
            message="test message",
            allow_mutation=True,
            selected_steps=[],
            step_outputs={},
            latest_refine_payload=None,
            latest_suggest_payload=None,
        )

    def _setup_mocks(self, monkeypatch, tool_calls_list: list, llm_content: str = ""):
        """Set up common mocks for agent loop tests."""
        from src.services.content_refinement_v3.agent import _context, _agent_loop as al

        def fake_get_session_content(*, session_id, message_limit, event_limit):
            return {
                "state": {
                    "refined_document_obj": {"summary": "test resume", "workExperience": []},
                    "doc_type": "resume",
                },
                "messages": [],
            }

        monkeypatch.setattr(_context, "get_session_content", fake_get_session_content)

        # Mock LLM — returns tool calls round 1, then compose round 2
        call_count = [0]

        class FakeMessage:
            def __init__(self, content="", tool_calls=None, reasoning_content=None):
                self.content = content
                self.tool_calls = tool_calls
                self.reasoning_content = reasoning_content

        class FakeChoice:
            def __init__(self, msg, finish_reason="tool_calls"):
                self.message = msg
                self.finish_reason = finish_reason

        class FakeResponse:
            def __init__(self, msg, finish_reason="tool_calls"):
                self.choices = [FakeChoice(msg, finish_reason)]
                self.usage = None

        def fake_completion(**kwargs):
            call_count[0] += 1
            if call_count[0] <= len(tool_calls_list):
                tc = tool_calls_list[call_count[0] - 1]
                return FakeResponse(
                    FakeMessage(content=llm_content, tool_calls=tc),
                    finish_reason="tool_calls",
                )
            # Fallback: empty response
            return FakeResponse(FakeMessage(content="done", tool_calls=None), finish_reason="stop")

        monkeypatch.setattr(al, "completion", fake_completion)

    def test_sse_events_structure(self, run_loop, ctx, monkeypatch):
        """Agent loop should return sse_events with step_start/step_done for each tool."""
        # Create a mock tool call — read_resume then compose
        class FakeFunction:
            def __init__(self, name, arguments):
                self.name = name
                self.arguments = arguments

        class FakeToolCall:
            def __init__(self, id, name, arguments):
                self.id = id
                self.function = FakeFunction(name, arguments)

        # Round 1: read_resume
        tc1 = FakeToolCall("call_1", "read_resume", '{"session_id": "test_session"}')

        self._setup_mocks(monkeypatch, [[tc1]])

        result = run_loop("test_session", "test message", ctx)

        assert "sse_events" in result, f"Missing sse_events in: {list(result.keys())}"
        events = result["sse_events"]
        assert len(events) >= 2, f"Expected >=2 events, got {len(events)}: {events}"

        # Events should include thinking, step_start, step_done
        kinds = [ev[0] for ev in events]
        assert "step_start" in kinds, f"Missing step_start in: {kinds}"
        assert "step_done" in kinds, f"Missing step_done in: {kinds}"

        # thinking events should be strings
        thinking_evs = [ev for ev in events if ev[0] == "thinking"]
        for _, text in thinking_evs:
            assert isinstance(text, str), f"thinking text should be str, got {type(text)}: {text!r}"

    def test_empty_response_returns_error(self, run_loop, ctx, monkeypatch):
        """Empty LLM response (no tools, no content) should return error, not fallback."""
        from src.services.content_refinement_v3.agent import _context, _agent_loop as al

        def fake_get_session_content(*, session_id, message_limit, event_limit):
            return {"state": {}, "messages": []}
        monkeypatch.setattr(_context, "get_session_content", fake_get_session_content)

        class FakeMessage:
            content = None
            tool_calls = None
            reasoning_content = None

        class FakeChoice:
            message = FakeMessage()
            finish_reason = "stop"

        class FakeResponse:
            choices = [FakeChoice()]
            usage = None

        monkeypatch.setattr(al, "completion", lambda **kwargs: FakeResponse())

        result = run_loop("test_session", "test message", ctx)

        # Should contain error message, not a fallback guess
        assert "error" in result.get("assistant_message", "").lower() or \
               "empty" in result.get("assistant_message", "").lower(), \
               f"Expected error message, got: {result.get('assistant_message', '')}"

    def test_response_schema_consistent(self, run_loop, ctx, monkeypatch):
        """All agent loop responses should have the same top-level keys."""
        from src.services.content_refinement_v3.agent import _context, _agent_loop as al

        def fake_get_session_content(*, session_id, message_limit, event_limit):
            return {"state": {}, "messages": []}
        monkeypatch.setattr(_context, "get_session_content", fake_get_session_content)

        class FakeMessage:
            content = "Here is a direct response"
            tool_calls = None
            reasoning_content = None

        class FakeChoice:
            message = FakeMessage()
            finish_reason = "stop"

        class FakeResponse:
            choices = [FakeChoice()]
            usage = None

        monkeypatch.setattr(al, "completion", lambda **kwargs: FakeResponse())

        result = run_loop("test_session", "test message", ctx)

        required_keys = {"assistant_message", "items", "fact_issues", "guide_prompts", "thinking", "sse_events"}
        missing = required_keys - set(result.keys())
        assert not missing, f"Missing required keys: {missing}"
        assert isinstance(result["items"], list)
        assert isinstance(result["fact_issues"], list)
        assert isinstance(result["sse_events"], list)

    def test_unknown_tool_does_not_crash_loop(self, run_loop, ctx, monkeypatch):
        """A hallucinated tool name should be returned to the LLM as a tool error."""
        from src.services.content_refinement_v3.agent import _context, _agent_loop as al

        def fake_get_session_content(*, session_id, message_limit, event_limit):
            return {"state": {}, "messages": []}
        monkeypatch.setattr(_context, "get_session_content", fake_get_session_content)

        class FakeFunction:
            def __init__(self, name, arguments="{}"):
                self.name = name
                self.arguments = arguments

        class FakeToolCall:
            def __init__(self, id, name, arguments="{}"):
                self.id = id
                self.function = FakeFunction(name, arguments)

        class FakeMessage:
            def __init__(self, content="", tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls
                self.reasoning_content = None

        class FakeChoice:
            def __init__(self, msg):
                self.message = msg
                self.finish_reason = "tool_calls"

        class FakeResponse:
            def __init__(self, msg):
                self.choices = [FakeChoice(msg)]
                self.usage = None

        calls = [0]

        def fake_completion(**kwargs):
            calls[0] += 1
            if calls[0] == 1:
                return FakeResponse(FakeMessage(tool_calls=[FakeToolCall("bad_1", "made_up_tool")]))
            tool_messages = [m for m in kwargs["messages"] if m.get("role") == "tool"]
            assert tool_messages
            assert "unknown tool" in tool_messages[-1]["content"]
            return FakeResponse(FakeMessage(tool_calls=[
                FakeToolCall("compose_1", "compose", '{"assistant_message":"Recovered from bad tool."}')
            ]))

        monkeypatch.setattr(al, "completion", fake_completion)

        result = run_loop("test_session", "test message", ctx)

        assert result["assistant_message"] == "Recovered from bad tool."
        assert "made_up_tool" in result["tool_names"]
        assert "compose" in result["tool_names"]

    def test_context_reads_saved_target_jd(self, monkeypatch):
        """Target JD stored in session RAG context should be injected on later turns."""
        from src.services.content_refinement_v3.agent import _context

        def fake_get_session_content(*, session_id, message_limit, event_limit):
            return {
                "state": {
                    "refined_document_obj": {"summary": "test resume"},
                    "rag_context_by_path": {
                        "target_jd": {
                            "id": "jd_1",
                            "text": "Backend Engineer JD with Python and distributed systems.",
                        }
                    },
                },
                "messages": [],
            }

        monkeypatch.setattr(_context, "get_session_content", fake_get_session_content)

        result = _context._build_context("test_session", "optimize this")

        assert result["target_jd"] == "Backend Engineer JD with Python and distributed systems."


def test_resume_turn_returns_apply_ready_suggestions(monkeypatch):
    """Confirming an ask_user pause should continue the saved agent context, not stop at a hard-coded message."""
    from src.services.content_refinement_v3.agent import turn_runner as tr

    session = {
        "id": "s1",
        "state": {
            "review_payload": {
                "paused_messages": [
                    {"role": "system", "content": "system"},
                    {
                        "role": "assistant",
                        "content": "Need confirmation.",
                        "tool_calls": [{"id": "ask_1", "function": {"name": "ask_user"}}],
                    },
                ],
            },
            "refined_document_obj": {"personalInfo": {"phone": "old"}},
        },
    }

    monkeypatch.setattr(tr, "get_session", lambda session_id, include_state=True: session)
    monkeypatch.setattr(
        tr,
        "get_session_content",
        lambda **kwargs: {"state": session["state"], "node_events": [], "messages": []},
    )
    monkeypatch.setattr(tr, "add_message", lambda **kwargs: {"id": "m1"})
    monkeypatch.setattr(tr, "finish_turn", lambda **kwargs: None)
    monkeypatch.setattr(tr, "save_session_state", lambda **kwargs: None)
    monkeypatch.setattr(tr, "_save_compact_turn_log", lambda **kwargs: None)
    monkeypatch.setattr(
        tr,
        "_run_agent_loop",
        lambda *args, **kwargs: {
            "assistant_message": "已根据你的确认继续处理。",
            "items": [{
                "path": "personalInfo.phone",
                "op": "update",
                "value": "new",
                "current_value": "old",
                "reason": "用户确认",
                "confidence": 0.95,
            }],
            "fact_issues": [],
            "guide_prompts": [],
            "thinking": "User confirmed the sensitive field, so I can apply it.",
        },
    )

    events = list(tr.resume_turn_sse(session_id="s1", turn_id="t1", user_response="confirmed"))
    completed = [event for event in events if event.startswith("event: turn.completed")]
    assert completed
    import json

    payload = json.loads([line for line in completed[-1].splitlines() if line.startswith("data: ")][0][6:])
    items = payload["turn_output_bundle"]["suggestion_document_obj"]["items"]
    assert items
    assert items[0]["path"] == "personalInfo.phone"
    assert items[0]["actionability"] == "apply_ready"
    assert payload["assistant_message"] == "已根据你的确认继续处理。"
