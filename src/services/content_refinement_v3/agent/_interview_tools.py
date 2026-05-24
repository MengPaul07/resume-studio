"""Interview agent tools — start/ask/end. Separate from resume editing tools."""

from __future__ import annotations

from typing import Any

from ._tools import tool, registered_tools
from ._types import ToolResult


# Re-export only interview schemas (not resume editing tools)
def interview_schema_list():
    """Return JSON schemas for interview tools only."""
    return [
        {"type": "function", "function": t.schema}
        for name, t in registered_tools().items()
        if name in ("start_interview", "ask_question", "ask_coding_question", "end_interview", "compose", "read_resume")
    ]


def interview_review_schema_list():
    """Return schemas for post-interview review mode.

    Review mode should coach, debrief, and run lightweight retry drills. It must
    not mutate resume content or restart the formal interview tool flow.
    """
    return [
        {"type": "function", "function": t.schema}
        for name, t in registered_tools().items()
        if name in ("compose", "read_resume", "read_history")
    ]


@tool("start_interview",
      "Start the interview. Introduce yourself as the interviewer and ask the first question.",
      {"type": "object", "properties": {
          "greeting": {"type": "string", "description": "Interviewer introduction with first question"},
          "phase": {"type": "string", "description": "Current interview phase"},
          "attitude": {"type": "string", "enum": ["neutral", "interested", "skeptical", "impatient", "satisfied"], "description": "Interviewer attitude after this message"},
          "message_blocks": {"type": "array", "items": {"type": "string"}, "description": "1-3 short conversational blocks for chat display"},
          "next_wait_seconds": {"type": "integer", "description": "How many seconds the UI should wait before a proactive nudge"},
      }, "required": ["greeting"]})
def tool_start_interview(*, greeting: str = "", phase: str = "opening",
                         attitude: str = "neutral", message_blocks: list | None = None,
                         next_wait_seconds: int = 90, **kwargs: Any) -> ToolResult:
    return ToolResult(success=True, tool_name="start_interview",
                      data={
                          "greeting": greeting,
                          "phase": phase,
                          "attitude": attitude,
                          "message_blocks": message_blocks or [],
                          "next_wait_seconds": next_wait_seconds,
                      })


@tool("ask_question",
      "Ask the next interview question. ONE question at a time.",
      {"type": "object", "properties": {
          "phase": {"type": "string", "enum": ["technical", "resume_deep_dive", "behavioral"],
                    "description": "Current interview phase"},
          "topic": {"type": "string", "description": "What skill/experience this question targets"},
          "question": {"type": "string", "description": "The interview question to ask"},
          "attitude": {"type": "string", "enum": ["neutral", "interested", "skeptical", "impatient", "satisfied"], "description": "Interviewer attitude after this message"},
          "message_blocks": {"type": "array", "items": {"type": "string"}, "description": "1-3 short conversational blocks for chat display"},
          "next_wait_seconds": {"type": "integer", "description": "How many seconds the UI should wait before a proactive nudge"},
      }, "required": ["phase", "topic", "question"]})
def tool_ask_question(*, phase: str = "", topic: str = "",
                       question: str = "", attitude: str = "neutral",
                       message_blocks: list | None = None,
                       next_wait_seconds: int = 90, **kwargs: Any) -> ToolResult:
    return ToolResult(success=True, tool_name="ask_question",
                      data={
                          "phase": phase,
                          "topic": topic,
                          "question": question,
                          "attitude": attitude,
                          "message_blocks": message_blocks or [],
                          "next_wait_seconds": next_wait_seconds,
                      })


@tool("end_interview",
      """End the interview. Give an overall score with brief justification, evaluate each question asked, and suggest improvement actions.""",
      {"type": "object", "properties": {
          "overall_score": {"type": "integer", "description": "Overall score 1-10"},
          "summary": {"type": "string", "description": "Overall assessment, 2-3 sentences"},
          "rounds_evaluation": {"type": "string", "description": "Per-question evaluation"},
          "improvement_actions": {"type": "string", "description": "2-3 concrete improvement actions"},
          "attitude": {"type": "string", "enum": ["satisfied", "skeptical", "neutral"], "description": "Final interviewer attitude"},
      }, "required": ["overall_score", "summary", "rounds_evaluation"]})
def tool_end_interview(*, overall_score: int = 0, summary: str = "",
                        rounds_evaluation: str = "",
                        improvement_actions: str = "", attitude: str = "", **kwargs: Any) -> ToolResult:
    return ToolResult(success=True, tool_name="end_interview",
                      data={
                          "overall_score": overall_score,
                          "summary": summary,
                          "rounds_evaluation": rounds_evaluation,
                          "improvement_actions": improvement_actions,
                          "attitude": attitude or ("satisfied" if overall_score >= 7 else "skeptical"),
                      })


@tool("ask_coding_question",
      "Send a coding problem to the candidate's code editor. MUST be called for every coding round — NEVER ask for code in plain chat text. The problem opens automatically in the candidate's editor with starter_code pre-filled. Call this tool again to update the editor: switch languages, modify starter_code, or send a completely new problem. Always provide language (infer from resume: Python if they mention Python, Java if Java, etc.) and appropriate starter_code.",
      {"type": "object", "properties": {
          "problem": {"type": "string", "description": "Full problem statement with examples, constraints, and expected complexity"},
          "language": {"type": "string", "enum": ["python", "java", "cpp", "javascript", "golang"], "description": "REQUIRED. Scan the resume for programming languages mentioned. If Python appears, pick python; if Java appears, pick java; if C++ appears, pick cpp; if unknown default to python. When candidate asks to switch languages, call this tool again with the new language."},
          "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"], "description": "Problem difficulty"},
          "time_limit": {"type": "integer", "description": "Suggested time in minutes"},
          "starter_code": {"type": "string", "description": "Starter code scaffold. Include function signature, class skeleton, imports, and minimal test examples. For easy problems, pre-fill ~30% (signature + imports + docstring). For medium, ~15% (signature only). For hard, ~5% (just imports). The editor will auto-fill this so the candidate doesn't start from an empty file."},
          "attitude": {"type": "string", "enum": ["neutral", "interested", "skeptical", "impatient", "satisfied"], "description": "Interviewer attitude after this message"},
          "next_wait_seconds": {"type": "integer", "description": "How many seconds the UI should wait before a proactive nudge"},
      }, "required": ["problem", "language"]})
def tool_ask_coding_question(*, problem: str = "", language: str = "python",
                               difficulty: str = "medium", time_limit: int = 15,
                               starter_code: str = "",
                               attitude: str = "neutral", next_wait_seconds: int = 90,
                               **kwargs: Any) -> ToolResult:
    return ToolResult(success=True, tool_name="ask_coding_question",
                      data={
                          "problem": problem, "language": language,
                          "difficulty": difficulty, "time_limit": time_limit,
                          "starter_code": starter_code,
                          "phase": "technical",
                          "attitude": attitude,
                          "next_wait_seconds": next_wait_seconds,
                      })
