"""Unit tests for mock interview module."""
from __future__ import annotations


class TestInterviewPrompt:
    def test_prompt_structure(self):
        from src.services.content_refinement_v3.prompts.interview import build_interview_prompt

        prompt = build_interview_prompt()
        assert "professional technical interviewer" in prompt.lower()
        assert "start_interview" in prompt
        assert "ask_question" in prompt
        assert "end_interview" in prompt
        assert "compose" in prompt
        assert "interviewer persona" in prompt.lower()
        assert "li yan" in prompt.lower()
        assert "project deep-dive" in prompt.lower()

    def test_prompt_with_jd(self):
        from src.services.content_refinement_v3.prompts.interview import build_interview_prompt

        jd = "Backend Engineer - Go Python Distributed Systems"
        prompt = build_interview_prompt(jd)
        assert jd in prompt
        assert "TARGET JOB DESCRIPTION" in prompt

    def test_prompt_without_jd(self):
        from src.services.content_refinement_v3.prompts.interview import build_interview_prompt

        prompt = build_interview_prompt("")
        assert "TARGET JOB DESCRIPTION" not in prompt

    def test_persona_prompt_accepts_length_and_preferences(self):
        from src.services.content_refinement_v3.prompts.interview import build_interview_prompt

        prompt = build_interview_prompt(
            preset_id="helena-brooks",
            rounds=10,
            user_preferences="Focus on audit trails and incident response.",
        )
        assert "Helena Brooks" in prompt
        assert "Investment Bank Risk Panelist" in prompt
        # PLANNED_LENGTH removed — rounds now controlled by frontend length selector
        assert "Focus on audit trails and incident response." in prompt

    def test_non_internet_industry_persona(self):
        from src.services.content_refinement_v3.prompts.interview import build_interview_prompt

        prompt = build_interview_prompt(preset_id="aisha-patel")
        assert "Healthcare AI Safety Reviewer" in prompt
        assert "patient safety" in prompt.lower()

    def test_research_professor_persona(self):
        from src.services.content_refinement_v3.prompts.interview import build_interview_prompt

        prompt = build_interview_prompt(preset_id="eleanor-park")
        assert "Research Faculty Interviewer" in prompt
        assert "experimental rigor" in prompt
        assert "publications" in prompt.lower() or "publication" in prompt.lower()

    def test_public_sector_persona(self):
        from src.services.content_refinement_v3.prompts.interview import build_interview_prompt

        prompt = build_interview_prompt(preset_id="grace-okafor")
        assert "Public Sector Digital Services Lead" in prompt
        assert "accessibility" in prompt.lower()
        assert "stakeholder" in prompt.lower()


class TestInterviewSchemaList:
    def test_returns_correct_tools(self):
        from src.services.content_refinement_v3.agent._interview_tools import interview_schema_list
        from src.services.content_refinement_v3.agent._tools import registered_tools

        schemas = interview_schema_list()
        assert len(schemas) == 6
        all_names = set(registered_tools().keys())
        interview_names = {
            n
            for n in all_names
            if n in ("start_interview", "ask_question", "ask_coding_question", "end_interview")
        }
        assert interview_names == {
            "start_interview",
            "ask_question",
            "ask_coding_question",
            "end_interview",
        }

    def test_no_edit_field_in_interview(self):
        from src.services.content_refinement_v3.agent._interview_tools import interview_schema_list

        schemas = interview_schema_list()
        interview_names = {s["function"]["name"] for s in schemas}
        assert interview_names == {
            "start_interview",
            "ask_question",
            "ask_coding_question",
            "end_interview",
            "compose",
            "read_resume",
        }
        for name in ("edit_field", "search_jd", "ask_user"):
            assert name not in interview_names, f"{name} should not be in interview tools"

    def test_review_mode_tools_are_limited_to_coaching(self):
        from src.services.content_refinement_v3.agent._interview_tools import interview_review_schema_list

        schemas = interview_review_schema_list()
        names = {s["function"]["name"] for s in schemas}
        assert names == {"compose", "read_resume", "read_history"}
        for name in ("edit_field", "ask_user", "start_interview", "ask_question", "ask_coding_question", "end_interview"):
            assert name not in names, f"{name} should not be available in review mode"


class TestInterviewTools:
    def test_start_interview(self):
        from src.services.content_refinement_v3.agent._interview_tools import tool_start_interview

        result = tool_start_interview(greeting="Hello, let's begin.")
        assert result.success
        assert result.data["greeting"] == "Hello, let's begin."

    def test_ask_question(self):
        from src.services.content_refinement_v3.agent._interview_tools import tool_ask_question

        result = tool_ask_question(
            phase="technical",
            topic="concurrency",
            question="How does Go handle goroutines?",
        )
        assert result.success
        assert result.data["phase"] == "technical"
        assert result.data["topic"] == "concurrency"

    def test_end_interview(self):
        from src.services.content_refinement_v3.agent._interview_tools import tool_end_interview

        result = tool_end_interview(
            overall_score=8,
            summary="Good performance overall.",
            rounds_evaluation="Q1: Strong. Q2: Could improve.",
            improvement_actions="Practice system design.",
        )
        assert result.success
        assert result.data["overall_score"] == 8
        assert result.data["summary"] == "Good performance overall."


class TestInterviewRegistry:
    def test_tools_registered(self):
        from src.services.content_refinement_v3.agent._tools import registered_tools

        tools = registered_tools()
        names = set(tools.keys())
        assert "start_interview" in names
        assert "ask_question" in names
        assert "ask_coding_question" in names
        assert "end_interview" in names
        assert tools["end_interview"].fn.__name__ == "tool_end_interview"
        assert tools["ask_coding_question"].fn.__name__ == "tool_ask_coding_question"


class TestInterviewModeLogging:
    """Verify interview turns are logged via tracer."""

    def test_tracer_emits_turn_span(self):
        from src.services.logging._trace import TurnTracer

        tracer = TurnTracer()
        span = tracer.start_span("turn.run", message="interview test")
        assert span.name == "turn.run"
        assert span.data.get("message") == "interview test"

    def test_interview_tool_spans(self):
        import time

        from src.services.logging._trace import TurnTracer

        tracer = TurnTracer()
        span = tracer.start_span("tool.execute", tool="start_interview")
        time.sleep(0.01)
        tracer.end_span(span, status="ok", tool="start_interview", duration_ms=100)
        assert span.status == "ok"
        assert span.data["tool"] == "start_interview"
        assert span.duration_ms > 0
