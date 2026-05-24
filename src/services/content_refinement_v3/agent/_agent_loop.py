"""Agent loop — function-calling agent with tool execution."""

from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import threading
import time
from typing import Any

from litellm import completion
from src.services.build_llm import build_llm
from ._types import ToolResult, TurnContext
from ._registry import ToolRegistry
from ._tools import schema_list, registered_tools
from ._context import _build_context

logger = logging.getLogger(__name__)


def _build_registry() -> ToolRegistry:
    """Register all agent tools — auto-collected from @tool decorators."""
    registry = ToolRegistry()
    for name, entry in registered_tools().items():
        registry.register(name, entry.fn)
    return registry


def _run_agent_loop(session_id: str, message: str, ctx: TurnContext,
                    on_sse_event=None, target_jd: str = "", tracer=None,
                    system_prompt: str = "", tools_override: list | None = None,
                    resume_messages: list | None = None) -> dict[str, Any]:
    """Function-calling agent loop. LLM selects tools, code executes them.

    If resume_messages is provided, skips context building and continues from
    the saved messages (used when resuming after a pause).

    Returns dict with: assistant_message, items, fact_issues, guide_prompts,
    thinking, sse_events, _paused (optional).
    """
    from src.services.content_refinement_v3.prompts.agent import build_agent_system_prompt

    llm = build_llm()
    tools = tools_override if tools_override is not None else schema_list()
    registry = _build_registry()

    if resume_messages:
        messages = resume_messages
        system_prompt = system_prompt or messages[0].get("content", "") if messages else ""
    else:
        context = _build_context(session_id, message)
        chat_history = context.get("chat_history", [])
        profile_text = context.get("profile_text", "")
        doc_type = context.get("doc_type", "resume")

        system_prompt = system_prompt or build_agent_system_prompt(doc_type=doc_type)
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        if profile_text:
            messages.append({"role": "system", "content": f"User profile for this resume:\n{profile_text}"})
        resolved_target_jd = str(target_jd or context.get("target_jd", "") or "").strip()
        if resolved_target_jd:
            messages.append({"role": "system", "content": f"TARGET JOB DESCRIPTION — the user is optimizing their resume for this position:\n{resolved_target_jd}"})
        for h in chat_history:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": str(message or "").strip()})

    all_items: list[dict[str, Any]] = []
    fact_issues: list[dict[str, Any]] = []
    jd_matches: list[dict[str, Any]] = []
    thinking_buf: list[str] = []
    tool_names: list[str] = []
    sse_events: list[tuple[str, dict[str, Any]]] = []
    interview_meta: dict[str, Any] = {}

    def _emit(kind: str, data: Any) -> None:
        """Append to sse_events and optionally push to real-time callback."""
        sse_events.append((kind, data))
        if on_sse_event:
            on_sse_event(kind, data)

    tool_failures: dict[str, int] = {}
    step_counter = 0
    state_lock = threading.Lock()
    max_rounds = 6

    for round_idx in range(max_rounds):
        _total_chars = sum(len(str(m.get("content", ""))) + len(str(m.get("tool_calls", ""))) for m in messages)
        logger.warning("[agent_loop] round=%d context_chars=%d messages=%d",
                       round_idx, _total_chars, len(messages))
        llm_span = None
        if tracer:
            llm_span = tracer.start_span("llm.call", model=llm.model, round=round_idx)

        try:
            t0 = time.perf_counter()
            resp = completion(
                model=llm.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                api_key=llm.api_key or None,
                api_base=llm.api_base or None,
                temperature=llm.temperature if llm.temperature > 0 else 0.2,
                max_tokens=16384,
                timeout=120,
            )
            llm_duration_ms = int((time.perf_counter() - t0) * 1000)
        except Exception as exc:
            if tracer and llm_span:
                tracer.end_span(llm_span, status="error", error=str(exc)[:200])
            logger.warning("[agent_loop] LLM call FAILED in round %d: %s", round_idx, exc)
            import traceback as _tb
            tb_text = _tb.format_exc()
            logger.warning("[agent_loop] traceback: %s", tb_text)
            break

        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or None
        content = str(getattr(msg, "content", "") or "").strip()
        finish = str(getattr(resp.choices[0], "finish_reason", "?"))
        usage = getattr(resp, "usage", None)

        if tracer and llm_span:
            tracer.end_span(llm_span, status="ok",
                prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
                finish_reason=finish,
                duration_ms=llm_duration_ms,
                has_tools=bool(tool_calls),
            )

        logger.warning("[agent_loop] round=%d has_tools=%s content_len=%d finish=%s tokens_in=%s tokens_out=%s",
                       round_idx, bool(tool_calls), len(content), finish,
                       getattr(usage, "prompt_tokens", "?") if usage else "?",
                       getattr(usage, "completion_tokens", "?") if usage else "?")

        # Debug dump (only when AGENT_DEBUG_DUMP env var is set)
        if os.environ.get("AGENT_DEBUG_DUMP"):
            try:
                os.makedirs("outputs", exist_ok=True)
                with open("outputs/agent_loop_dump.txt", "a", encoding="utf-8") as _df:
                    _df.write(f"\n=== ROUND {round_idx} ===\n")
                    _df.write(f"has_tools={bool(tool_calls)} content_len={len(content)} finish={finish}\n")
                    _df.write(f"prompt_tokens={getattr(usage, 'prompt_tokens', '?') if usage else '?'}\n")
                    _df.write(f"completion_tokens={getattr(usage, 'completion_tokens', '?') if usage else '?'}\n")
                    _df.write(f"last_role={messages[-1].get('role','?') if messages else 'none'}\n")
                    if content:
                        _df.write(f"content={content[:300]}\n")
                    if tool_calls:
                        _df.write(f"tool_calls={[tc.function.name for tc in tool_calls]}\n")
                    _df.write(f"message_count={len(messages)}\n")
            except Exception:
                pass

        # Empty response → error (no fallback guessing)
        if not tool_calls and not content:
            logger.warning("[agent_loop] round=%d EMPTY RESPONSE", round_idx)
            return {
                "assistant_message": "Agent error: LLM returned empty response. Please rephrase your request.",
                "items": all_items, "fact_issues": fact_issues, "jd_matches": jd_matches,
                "guide_prompts": [], "thinking": "\n".join(thinking_buf),
                "sse_events": sse_events,
                "tool_names": list(tool_names),
            }

        # No tool_calls, has content → LLM direct text response (rare, prompt asks for tools)
        if not tool_calls:
            return {
                "assistant_message": content, "items": all_items,
                "fact_issues": fact_issues, "guide_prompts": [],
                "thinking": "\n".join(thinking_buf), "sse_events": sse_events,
                "tool_names": list(tool_names),
            }

        # Push LLM content: round 0 = thinking, round 1+ = reasoning
        # Skip if compose is the only tool — final answer belongs in compose, not thinking
        is_only_compose = len(tool_calls) == 1 and tool_calls[0].function.name == "compose"
        if content and not is_only_compose:
            kind = "reasoning" if round_idx > 0 else "thinking"
            _emit(kind, content)

        # Build assistant message with tool_calls
        asst_msg: dict[str, Any] = {
            "role": "assistant",
            "content": content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        }
        reasoning = getattr(msg, "reasoning_content", None)
        if reasoning:
            asst_msg["reasoning_content"] = reasoning
        messages.append(asst_msg)

        tool_registry = registered_tools()

        # Parse all tool calls
        calls: list[tuple[Any, str, dict[str, Any]]] = []
        for tc in tool_calls:
            try:
                fn_args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                fn_args = {}
            fn_args["session_id"] = session_id
            calls.append((tc, tc.function.name, fn_args))
            # Log: LLM decided to call this tool
            _emit("llm_tool_decision", {
                "round": round_idx, "name": tc.function.name,
                "arguments": {k: v for k, v in fn_args.items() if k != "session_id"},
            })

        # Group: parallel-safe tools go to thread pool, rest sequential
        parallel_calls = [(tc, n, a) for tc, n, a in calls
                        if tool_registry.get(n) is not None and tool_registry[n].parallel_safe]
        serial_calls = [(tc, n, a) for tc, n, a in calls
                       if tool_registry.get(n) is None or not tool_registry[n].parallel_safe]

        _compose_result: list[dict[str, Any]] = []
        _paused_result: list[dict[str, Any]] = []

        def _exec_one(tc: Any, fn_name: str, fn_args: dict[str, Any]) -> None:
            """Execute one tool call, emit SSE events, handle compose/ask_user."""
            nonlocal step_counter
            with state_lock:
                step_counter += 1
                step_id = f"agent_step_{step_counter}"
                thinking_idx = len(thinking_buf)
                thinking_buf.append(f"[{fn_name}]")
                tool_names.append(fn_name)

            # SSE: step_start
            _emit("step_start", {"step_id": step_id, "tool": fn_name})

            # Log: full tool call with args
            _emit("tool_call", {"step_id": step_id, "name": fn_name, "arguments": fn_args})

            tool_span = None
            if tracer:
                tool_span = tracer.start_span("tool.execute", tool=fn_name, step_id=step_id)

            t0 = time.perf_counter()
            res = registry.execute(fn_name, **fn_args)
            ms = int((time.perf_counter() - t0) * 1000)

            if tracer and tool_span:
                tracer.end_span(tool_span, status="ok" if res.success else "error",
                    tool=fn_name, duration_ms=ms, error=res.error or "")

            status = "OK" if res.success else "FAIL"
            with state_lock:
                thinking_buf[thinking_idx] = f"[{fn_name}] {status}"

            # Log: full tool result
            _emit("tool_result", {
                "step_id": step_id, "name": fn_name,
                "success": res.success, "data": res.data if res.success else {},
                "error": res.error or "", "ms": ms,
            })

            # SSE: step_done with status
            _emit("step_done", {"step_id": step_id, "tool": fn_name, "ms": ms, "status": status})

            if not res.success:
                tool_failures[fn_name] = tool_failures.get(fn_name, 0) + 1
                if tool_failures[fn_name] <= 2:
                    with state_lock:
                        messages.append({
                            "role": "tool", "tool_call_id": tc.id,
                            "content": f"[{fn_name}] ERROR: {res.error}\nPlease fix and retry. Attempt {tool_failures[fn_name]}/2.",
                        })
                    return
                logger.warning("[agent_loop] %s failed %d times, permanently", fn_name, tool_failures[fn_name])

            # compose → signal early return
            if fn_name == "compose" and res.success:
                data = res.data if isinstance(res.data, dict) else {}
                msg_text = str(data.get("assistant_message", ""))
                _compose_result.append({
                    "assistant_message": msg_text,
                    "items": list(all_items),
                    "fact_issues": list(fact_issues),
                    "jd_matches": list(jd_matches),
                    "guide_prompts": data.get("guide_prompts", []),
                    "show_jd_cards": bool(data.get("show_jd_cards", False)),
                    "thinking": "\n".join(thinking_buf),
                    "sse_events": sse_events,
                    "tool_names": list(tool_names),
                    "interview_meta": dict(interview_meta),
                })
                return

            # ask_user → signal pause
            if fn_name == "ask_user" and res.success:
                data = res.data if isinstance(res.data, dict) else {}
                ask_items = data.get("items", []) or []
                for ai in ask_items:
                    if isinstance(ai, dict):
                        fact_issues.append({
                            "path": str(ai.get("path", "")),
                            "current_value": str(ai.get("current_value", "")),
                            "suggested_value": str(ai.get("suggested_value", "")),
                            "op": str(ai.get("op", "update")),
                            "reason": str(ai.get("reason", "")),
                            "confirmation_hint": f"请确认 {ai.get('path', '')} 的正确值",
                        })
                _paused_result.append({
                    "assistant_message": "涉及敏感数据修改，请确认以下信息后继续。",
                    "items": all_items,
                    "fact_issues": fact_issues,
                    "guide_prompts": [],
                    "thinking": "\n".join(thinking_buf),
                    "sse_events": sse_events,
                    "tool_names": list(tool_names),
                    "_paused": True,
                    "_messages": [dict(m) for m in messages],
                })
                return

            # ask_coding_question → emit SSE event for frontend code editor
            if fn_name == "ask_coding_question" and res.success:
                data = res.data if isinstance(res.data, dict) else {}
                for key in ("phase", "attitude", "message_blocks", "next_wait_seconds"):
                    value = data.get(key)
                    if value not in (None, "", []):
                        interview_meta[key] = value
                _emit("coding_question", data)

            if fn_name in ("start_interview", "ask_question", "end_interview") and res.success:
                data = res.data if isinstance(res.data, dict) else {}
                for key in ("phase", "attitude", "message_blocks", "next_wait_seconds"):
                    value = data.get(key)
                    if value not in (None, "", []):
                        interview_meta[key] = value
                if fn_name == "end_interview":
                    interview_meta["ended"] = True

            # search_jd → collect for frontend cards
            if fn_name == "search_jd" and res.success:
                data = res.data if isinstance(res.data, dict) else {}
                matches = data.get("matches", [])
                if matches:
                    jd_matches[:] = matches  # replace with latest search result

            # edit_field → accumulate to all_items
            if fn_name == "edit_field" and res.success:
                data = res.data if isinstance(res.data, dict) else {}
                written = data.get("written")
                all_items.append({
                    "path": str(data.get("path", "")),
                    "op": str(fn_args.get("op", "update")),
                    "value": written if written is not None else fn_args.get("value", ""),
                    "current_value": fn_args.get("current_value", ""),
                    "reason": str(fn_args.get("reason", "")),
                    "actionability": str(fn_args.get("actionability", "apply_ready")),
                    "confidence": float(fn_args.get("confidence", 0.8) or 0.8),
                })

            # set_target_jd → collect for frontend
            if fn_name == "set_target_jd" and res.success:
                data = res.data if isinstance(res.data, dict) else {}
                jd_text = data.get("target_jd", "")
                if jd_text:
                    jd_matches.append({"id": data.get("jd_id", ""), "text": jd_text, "selected": True})

            with state_lock:
                messages.append({
                    "role": "tool", "tool_call_id": tc.id,
                    "content": _tool_result_to_text(fn_name, res),
                })

        # Execute parallel-safe tools concurrently
        if parallel_calls:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(parallel_calls))) as _pex:
                _futures = {_pex.submit(_exec_one, tc, n, a): (tc, n) for tc, n, a in parallel_calls}
                for _f in concurrent.futures.as_completed(_futures):
                    _f.result()
                    if _compose_result:
                        return _compose_result[0]
                    if _paused_result:
                        return _paused_result[0]

        if _compose_result:
            return _compose_result[0]
        if _paused_result:
            return _paused_result[0]

        # Execute serial tools sequentially
        for tc, fn_name, fn_args in serial_calls:
            _exec_one(tc, fn_name, fn_args)
            if _compose_result:
                return _compose_result[0]
            if _paused_result:
                return _paused_result[0]

        # Hint LLM to compose when stuck re-reading/searching
        tools_this_round = [n for _, n, _ in calls]
        only_reads = all(t in ("read_resume", "read_history", "search_jd") for t in tools_this_round)
        if only_reads and round_idx >= 2:
            messages.append({
                "role": "system",
                "content": "You have gathered enough data. Call compose() now to summarize your findings.",
            })

    # Max rounds reached — LLM kept working without composing, return what we have
    has_edits = len(all_items) > 0
    return {
        "assistant_message": (
            f"已为您处理 {len(all_items)} 条修改，请检查预览区确认结果。"
            if has_edits else
            "处理超时，请重新描述您的需求。"
        ),
        "items": all_items,
        "fact_issues": fact_issues,
        "guide_prompts": [],
        "thinking": "\n".join(thinking_buf),
        "sse_events": sse_events,
        "tool_names": list(tool_names),
    }


def _tool_result_to_text(name: str, result: ToolResult) -> str:
    """Convert a tool result to a compact text representation for the LLM."""
    if not result.success:
        return f"[{name}] ERROR: {result.error}"
    data = result.data if isinstance(result.data, dict) else {}
    if name == "read_resume":
        resume = data.get("resume", {})
        if not resume:
            return "[read_resume] Resume is empty or not found."
        import json as _json
        return f"[read_resume] Resume JSON:\n{_json.dumps(resume, ensure_ascii=False)}"
    elif name == "read_history":
        history = data.get("history", [])
        if not history:
            return "[read_history] No recent messages."
        lines = [f"[read_history] {len(history)} recent messages:"]
        for h in history[-5:]:
            lines.append(f"  {h['role']}: {h['content'][:120]}")
        return "\n".join(lines)
    elif name == "set_target_jd":
        jd_text = data.get("target_jd", "")
        preview = jd_text[:100].replace("\n", " ") if jd_text else "(empty)"
        return f"[set_target_jd] OK — target JD set: {preview}..."
    elif name == "edit_field":
        import json as _json
        written = data.get("written", data.get("value", ""))
        written_str = _json.dumps(written, ensure_ascii=False) if isinstance(written, (dict, list)) else str(written)[:200]
        return f"[edit_field] OK: {data.get('path', '?')} = {written_str}"
    elif name == "search_jd":
        matches = data.get("matches", [])
        if not matches:
            return f"[search_jd] No JD matches found. {data.get('hint', '')}"
        lines = [f"[search_jd] {len(matches)} JDs returned. To set as target, call set_target_jd with the chosen JD text."]
        for i, m in enumerate(matches):
            lines.append(f"\n--- JD {i+1} ---\n{m.get('text', '')}")
        return "\n".join(lines)
    elif name == "start_interview":
        return f"[start_interview] {data.get('greeting', '')}"
    elif name == "ask_question":
        return (
            f"[ask_question] phase={data.get('phase', '')}; topic={data.get('topic', '')}\n"
            f"{data.get('question', '')}"
        )
    elif name == "ask_coding_question":
        return (
            f"[ask_coding_question] difficulty={data.get('difficulty', '')}; language={data.get('language', '')}; "
            f"time_limit={data.get('time_limit', '')}\n{data.get('problem', '')}"
        )
    elif name == "end_interview":
        return (
            f"[end_interview] Overall Score: {data.get('overall_score', 0)}/10\n"
            f"Summary: {data.get('summary', '')}\n"
            f"Rounds Evaluation: {data.get('rounds_evaluation', '')}\n"
            f"Improvement Actions: {data.get('improvement_actions', '')}"
        )
    return f"[{name}] OK"
