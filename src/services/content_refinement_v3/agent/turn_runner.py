from __future__ import annotations

import json
import logging
import re
import time
from copy import deepcopy
from typing import Any, Dict, Generator, List, Tuple

from litellm import completion

from src.services.build_llm import build_llm
from src.services.content_refinement_v3.backends.session import (
    _normalize_suggestion_document_obj,
    add_message,
    add_node_event,
    add_session_version,
    create_turn,
    finish_turn,
    get_session,
    get_session_content,
    list_node_events,
    rollback_to_version,
    save_session_state,
)

from ..session.service import _get_by_path_local, _set_by_path_local

from ._types import StepRecord, ToolResult, TurnContext
from ._registry import ToolRegistry
from . import _sse
from ._tools import schema_list, registered_tools

MAX_STEPS = 6
CHAT_WINDOW = 9999  # full history, no sliding window
GLOBAL_SCOPES = ["summary", "workExperience", "education", "personalProjects", "research", "additional", "personalInfo"]
logger = logging.getLogger(__name__)


from ._utils import (_to_display_text, _canonical_semantic_text, _extract_numbers,
    _looks_like_phone_or_email, _is_format_only_candidate, _is_fact_sensitive_change,
    _build_diff_payload, _make_item_key, _tokenize_path, _set_by_path, _delete_by_path)
from ._suggestion import (_expand_two_style_candidates, _build_content_assessment,
    _normalize_suggestions, _visible_suggestions, _extract_fact_issues,
    _extract_low_confidence_items, _actionability_summary,
    _resolve_target_scopes, _merge_suggestion_documents)
from ._context import _build_context
from ._payload import _build_turn_output_bundle, _build_turn_payload, _build_action_turn_payload
from ._agent_loop import _run_agent_loop, _build_registry
from ._utils import (_infer_scope_from_message, _is_global_edit_intent, _is_analysis_only_intent,
    _is_edit_intent, _is_fact_edit_intent, _tokenize_path, _build_diff_payload, _is_fact_sensitive_change)

def _sse_event(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _save_compact_turn_log(
    *,
    session_id: str,
    turn_id: str,
    message: str,
    final_payload: Dict[str, Any],
    ctx: TurnContext,
    agent_dump: Dict[str, Any] | None = None,
) -> None:
    from ._turn_log import save_turn_log

    try:
        log_path = save_turn_log(
            session_id=session_id,
            turn_id=turn_id,
            message=message,
            final_payload=final_payload,
            sse_trace=getattr(ctx, "sse_trace", None) or [],
            agent_dump=agent_dump,
        )
    except Exception as exc:
        logger.warning("[turn] log save failed: %s", exc)
    else:
        if log_path:
            logger.info("[turn] log saved: %s", log_path)


def _compose_general_chat_message(message: str) -> str:
    user_text = str(message or "").strip()
    if not user_text:
        return "我是你的简历优化助手，可以帮你分析、润色并生成可应用修改候选。"
    llm = build_llm()
    system_prompt = (
        "你是简历优化助手。当前场景是聊天问答，不是执行润色。"
        "请自然、简洁回答用户问题；不要输出流程化套话。"
    )
    try:
        response = completion(
            model=llm.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            api_key=llm.api_key or None,
            api_base=llm.api_base or None,
            temperature=0.2,
            max_tokens=4096,
            timeout=60,
        )
        answer = str(getattr(response.choices[0].message, "content", "") or "").strip()
        if answer:
            return answer
    except Exception:
        pass
    return "我是你的简历优化助手，可以帮你分析、润色并生成可应用修改候选。"


# _build_context imported from ._context (with target_jd support)
# _propose_direct_edit removed — replaced by _run_agent_loop
def _compose_and_self_check(
    *,
    message: str,
    latest_refine_payload: Dict[str, Any],
    session_id: str = "",
) -> Dict[str, Any]:
    """Code-based verdict: direct_edit already outputs assistant_message + items.
    No LLM compose call needed — the verdict is determined by item existence and quality.
    """
    full_suggestions = (
        latest_refine_payload.get("full_suggestion_document_obj", {"items": []})
        if isinstance(latest_refine_payload.get("full_suggestion_document_obj", {}), dict)
        else {"items": []}
    )
    visible_suggestions = _visible_suggestions(full_suggestions, include_confirm_required=False)
    fact_issues = _extract_fact_issues(full_suggestions)
    summary = _actionability_summary(full_suggestions)
    scopes = latest_refine_payload.get("target_scopes", []) if isinstance(latest_refine_payload.get("target_scopes", []), list) else []
    scope_text = "、".join([str(scope) for scope in scopes[:4]]) if scopes else "当前范围"
    content_assessment = _build_content_assessment(visible_suggestions, fact_issues)

    assistant_message = str(latest_refine_payload.get("assistant_message", "")).strip()
    thinking = str(latest_refine_payload.get("thinking", "")).strip()
    low_confidence_items = _extract_low_confidence_items(full_suggestions)
    total = summary.get("total", 0)

    if total > 0:
        if not assistant_message:
            assistant_message = f"已为 {scope_text} 生成 {summary.get('apply_ready', 0)} 条可应用修改建议。"
        return {
            "verdict": "pass",
            "reason": f"suggestions_exist: {total} items",
            "fix_hint": "",
            "assistant_message": assistant_message,
            "thinking": thinking,
            "suggestion_document_obj": visible_suggestions,
            "full_suggestion_document_obj": full_suggestions,
            "actionability_summary": summary,
            "fact_issues": fact_issues,
            "low_confidence_items": low_confidence_items,
            "thought_summary": [
                f"范围: {scope_text}",
                f"候选: {summary.get('apply_ready', 0)} 条可应用 / {summary.get('confirm_required', 0)} 条待确认",
            ],
            "content_assessment": content_assessment,
            "vague_actions": [],
            "meta": {"tool": "compose_and_check", "scopes": scopes, "fast_path": True},
        }

    # No items produced — return what direct_edit gave us
    if not assistant_message:
        assistant_message = _compose_general_chat_message(message)
    return {
        "verdict": "pass",
        "reason": "no_items_general_response",
        "fix_hint": "",
        "assistant_message": assistant_message,
        "thinking": thinking,
        "suggestion_document_obj": visible_suggestions,
        "full_suggestion_document_obj": full_suggestions,
        "actionability_summary": summary,
        "fact_issues": fact_issues,
        "low_confidence_items": low_confidence_items,
        "thought_summary": [f"范围: {scope_text}", "未生成修改建议"],
        "content_assessment": content_assessment,
        "vague_actions": [],
        "meta": {"tool": "compose_and_check", "scopes": scopes, "fast_path": True},
    }


def _record_version(*, session_id: str, refined_document_obj: Dict[str, Any], suggestion_document_obj: Dict[str, Any], source: str, turn_id: str, note: str) -> None:
    add_session_version(
        session_id=session_id,
        refined_resume_obj=refined_document_obj,
        suggestion_resume_obj=suggestion_document_obj,
        source=source,
        turn_id=turn_id,
        note=note,
    )


def _session_state_snapshot(session_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    session = get_session(session_id, include_state=True) or {}
    state = session.get("state", {}) if isinstance(session.get("state", {}), dict) else {}
    refined = state.get("refined_document_obj") or state.get("refined_resume_obj") or {}
    refined = refined if isinstance(refined, dict) else {}
    suggestions = state.get("suggestion_document_obj") or state.get("suggestion_resume_obj") or {"items": []}
    suggestions = suggestions if isinstance(suggestions, dict) else {"items": []}
    return session, state, {"refined_document_obj": refined, "suggestion_document_obj": _normalize_suggestions(suggestions)}

def run_turn_sse(*, session_id: str, message: str, allow_mutation: bool, layout_preferences: Dict[str, Any] | None = None, target_jd: str = "", mode: str = "refine", interview_config: Dict[str, Any] | None = None) -> Generator[str, None, None]:
    del layout_preferences

    # Bootstrap
    session = get_session(session_id, include_state=True)
    if not session:
        raise ValueError("session not found")
    session_state_for_target = session.get("state", {}) if isinstance(session.get("state", {}), dict) else {}
    rag_context_for_target = (
        session_state_for_target.get("rag_context_by_path", {})
        if isinstance(session_state_for_target.get("rag_context_by_path", {}), dict)
        else {}
    )
    saved_target_jd = (
        rag_context_for_target.get("target_jd", {})
        if isinstance(rag_context_for_target.get("target_jd", {}), dict)
        else {}
    )
    if not str(target_jd or "").strip():
        target_jd = str(saved_target_jd.get("text", "") or saved_target_jd.get("full_text", "") or "").strip()
    turn = create_turn(session_id=session_id)
    turn_id = str(turn.get("id", ""))
    clean_message = str(message or "").strip()
    if mode == "interview" and not clean_message:
        clean_message = "Start the interview. Introduce yourself as the interviewer and ask the first question."
    add_message(session_id=session_id, turn_id=turn_id, role="user", content=clean_message)
    yield from _sse.emit_turn_started(session_id, turn_id, clean_message)

    # Empty/whitespace-only message: return a generic greeting without the full pipeline
    if not clean_message:
        assistant_msg = "你好，我是你的简历优化助手。你可以直接告诉我想要修改的内容，比如「优化工作经历部分，突出量化成果」或「分析简历的 ATS 关键词覆盖情况」。"
        add_message(session_id=session_id, turn_id=turn_id, role="assistant", content=assistant_msg)
        finish_turn(turn_id=turn_id, status="completed", assistant_message_id="")
        payload = _build_turn_payload(
            session_id=session_id,
            session=session,
            turn_id=turn_id,
            selected_steps=[],
            step_outputs={},
            termination_reason="composed",
            latest_state=get_session_content(session_id=session_id, message_limit=CHAT_WINDOW, event_limit=200).get("state", {}),
            turn_output_bundle={"assistant_message": assistant_msg, "suggestion_document_obj": {"items": []}, "fact_issues": [], "thought_summary": ["范围: 无"], "content_assessment": {}, "intent_state": {"intent_class": "general_chat", "active_scope": "", "goal": "", "confidence": 1.0}},
        )
        yield from _sse.emit_turn_completed(payload)
        return

    ctx = TurnContext(
        session_id=session_id,
        turn_id=turn_id,
        message=clean_message,
        allow_mutation=allow_mutation,
        max_steps=MAX_STEPS,
    )
    registry = _build_registry()

    try:
        # 1. Direct edit — single LLM call: receives raw user message + full resume JSON,
        #    self-classifies intent, outputs all edit items + assistant_message.
        #    This replaces the old observe_content → rewrite_message → IntentResolver →
        #    ChainPlanner → propose_direct_edit pipeline.
        step_id = "step_direct_edit"
        # Agent loop: LLM selects tools autonomously (read_resume, edit_field, compose, etc.)
        yield from _sse.emit_plan_updated(ctx, "agent_loop", "reasoning")
        yield from _sse.emit_plan_step(ctx, step_id, "agent_loop", "reasoning")
        yield from _sse.emit_step_started(ctx, step_id, "agent_loop")

        yield from _sse.emit_thinking(ctx, "正在分析你的请求...")

        import queue
        import threading
        import time as _time

        _started = _time.perf_counter()
        _agent_result_container: list[dict[str, Any]] = []
        _agent_error: list[str] = []

        # Queue + thread for real-time SSE streaming
        _q: queue.Queue = queue.Queue()

        # Capture LLM config in main thread before spawning — contextvars
        # are not inherited by threading.Thread workers.
        from src.utils.context import get_llm_config as _get_llm_cfg
        _captured_llm_config = _get_llm_cfg()

        def _on_event(kind: str, data: Any) -> None:
            _q.put(("event", kind, data))

        def _run_agent_thread() -> None:
            # Re-hydrate LLM config in agent thread context
            from src.utils.context import set_llm_config as _set_llm_cfg
            _set_llm_cfg(_captured_llm_config)
            try:
                if mode == "interview":
                    from src.services.content_refinement_v3.prompts.interview import build_interview_prompt
                    from src.services.content_refinement_v3.agent._interview_tools import interview_schema_list
                    ic = interview_config or {}
                    result = _run_agent_loop(session_id, clean_message, ctx,
                        on_sse_event=_on_event, target_jd=target_jd,
                        system_prompt=build_interview_prompt(
                            target_jd=target_jd,
                            preset_id=ic.get("preset_id"),
                            company=ic.get("company"),
                            role=ic.get("role"),
                            level=ic.get("level"),
                            style=ic.get("style"),
                            depth=ic.get("depth"),
                            focus=ic.get("focus"),
                            rounds=ic.get("rounds"),
                            language=ic.get("language"),
                            time_pressure=ic.get("time_pressure"),
                            user_preferences=ic.get("user_preferences"),
                        ),
                        tools_override=interview_schema_list())
                elif mode == "interview_review":
                    from src.services.content_refinement_v3.prompts.interview_review import build_interview_review_prompt
                    from src.services.content_refinement_v3.agent._interview_tools import interview_review_schema_list
                    result = _run_agent_loop(session_id, clean_message, ctx,
                        on_sse_event=_on_event, target_jd=target_jd,
                        system_prompt=build_interview_review_prompt(),
                        tools_override=interview_review_schema_list())
                else:
                    result = _run_agent_loop(session_id, clean_message, ctx,
                        on_sse_event=_on_event, target_jd=target_jd)
                _q.put(("result", result))
            except Exception as exc:
                import traceback as _tb
                _q.put(("error", f"{exc}\n{_tb.format_exc()}"))

        _thread = threading.Thread(target=_run_agent_thread, daemon=True)
        _thread.start()

        # Drain queue: yield SSE events in real-time, wait for final result
        agent_result = None
        while True:
            item = _q.get()
            if item[0] == "event":
                _, kind, data = item
                if kind == "thinking":
                    yield from _sse.emit_thinking(ctx, data)
                elif kind == "reasoning":
                    yield from _sse.emit_reasoning(ctx, data)
                elif kind == "step_start":
                    yield from _sse.emit_step_started(ctx, data["step_id"], data["tool"])
                elif kind == "step_done":
                    extra = {k: v for k, v in data.items() if k not in ("step_id", "tool", "ms")}
                    yield from _sse.emit_step_succeeded(ctx, data["step_id"], data["tool"], data.get("ms", 0), **extra)
                elif kind == "coding_question":
                    yield from _sse.emit_event("coding_question", data)
            elif item[0] == "result":
                agent_result = item[1]
                break
            elif item[0] == "error":
                _agent_error.append(item[1])
                logger.error("[v3][agent_loop.thread] %s", item[1])
                break

        _thread.join(timeout=5)
        _duration = int((_time.perf_counter() - _started) * 1000)

        if not agent_result:
            error_msg = _agent_error[0] if _agent_error else "agent loop returned no result"
            yield from _sse.emit_step_failed(ctx, step_id, "agent_loop", error_msg)
            error_payload = {"session_id": session_id, "turn_id": turn_id, "error": error_msg, "termination_reason": "error"}
            finish_turn(turn_id=turn_id, status="failed", error_text=error_msg)
            yield _sse_event("turn.completed", error_payload)
            return

        # Record agent loop step
        ctx.selected_steps.append(StepRecord(step_id=step_id, tool="agent_loop",
                                              status="success", duration_ms=_duration,
                                              reason_brief="agent_loop"))

        if mode in {"interview", "interview_review"}:
            assistant_msg = str(agent_result.get("assistant_message", "")).strip()
            turn_output_bundle = {
                "assistant_message": assistant_msg,
                "thinking": agent_result.get("thinking", ""),
                "suggestion_document_obj": {"items": []},
                "actionability_summary": {"total": 0, "apply_ready": 0, "confirm_required": 0},
                "fact_issues": [],
                "low_confidence_items": [],
                "guide_prompts": agent_result.get("guide_prompts", []),
                "step_reason_summary": [{"step_id": s.step_id, "tool": s.tool, "reason_brief": s.reason_brief} for s in ctx.selected_steps],
                "self_check_result": {"result": "pass", "reason": "interview_agent"},
                "planner_decision_trace": ctx.planner_decision_trace,
                "thought_summary": [],
                "content_assessment": {},
                "intent_state": {"intent_class": mode, "confidence": 1.0},
                "vague_actions": [],
                "interview": {
                    **(
                        agent_result.get("interview_meta", {})
                        if isinstance(agent_result.get("interview_meta", {}), dict)
                        else {}
                    ),
                    "ended": bool(
                        (
                            agent_result.get("interview_meta", {})
                            if isinstance(agent_result.get("interview_meta", {}), dict)
                            else {}
                        ).get("ended")
                    ) or any(name == "end_interview" for name in agent_result.get("tool_names", [])),
                    "tools": agent_result.get("tool_names", []),
                },
            }
            ctx.turn_output_bundle = turn_output_bundle
            ctx.termination_reason = "composed"
            yield from _sse.emit_step_succeeded(ctx, step_id, "agent_loop", _duration,
                thinking=agent_result.get("thinking", ""), interview=turn_output_bundle["interview"])
            yield from _sse.emit_turn_composed(ctx, assistant_msg)
            assistant_row = add_message(session_id=session_id, turn_id=turn_id, role="assistant", content=assistant_msg)
            finish_turn(turn_id=turn_id, status="completed", assistant_message_id=str(assistant_row.get("id", "")))

            latest_state = get_session_content(session_id=session_id, message_limit=CHAT_WINDOW, event_limit=200).get("state", {})
            latest_state = latest_state if isinstance(latest_state, dict) else {}
            final_payload = _build_turn_payload(
                session_id=session_id,
                session=session,
                turn_id=turn_id,
                selected_steps=[{"step_id": s.step_id, "tool": s.tool, "status": s.status, "duration_ms": s.duration_ms, "reason_brief": s.reason_brief} for s in ctx.selected_steps],
                step_outputs={},
                termination_reason=ctx.termination_reason,
                latest_state=latest_state,
                turn_output_bundle=ctx.turn_output_bundle,
            )
            yield from _sse.emit_turn_completed(final_payload)
            _save_compact_turn_log(session_id=session_id, turn_id=turn_id, message=clean_message, final_payload=final_payload, ctx=ctx, agent_dump=agent_result)
            return

        # Handle ask_user pause — stop here, don't continue to compose
        if agent_result.get("_paused"):
            fact_issues_paused = agent_result.get("fact_issues", [])
            assistant_msg = agent_result.get("assistant_message", "")

            # Emit pause before completing
            yield from _sse.emit_turn_paused(ctx, fact_issues_paused)

            ctx.termination_reason = "paused"
            step_reason_summary = [{"step_id": s.step_id, "tool": s.tool, "reason_brief": s.reason_brief} for s in ctx.selected_steps]

            # Save assistant message
            assistant_row = add_message(session_id=session_id, turn_id=turn_id, role="assistant", content=assistant_msg)
            finish_turn(turn_id=turn_id, status="paused", assistant_message_id=str(assistant_row.get("id", "")))

            # Save LLM context for resume — avoids full re-run on continuation
            paused_messages = agent_result.get("_messages", [])
            if paused_messages:
                save_session_state(session_id=session_id, review_payload={"paused_messages": paused_messages, "turn_id": turn_id})

            session_state = (session.get("state", {}) or {}) if isinstance(session, dict) else {}
            session_state = session_state if isinstance(session_state, dict) else {}
            step_dicts = [{"step_id": s.step_id, "tool": s.tool, "status": s.status, "duration_ms": s.duration_ms, "reason_brief": s.reason_brief} for s in ctx.selected_steps]
            step_outputs = {s.step_id: {"success": s.status == "success"} for s in ctx.selected_steps}
            final_payload = _build_turn_payload(
                session_id=session_id,
                session=session,
                turn_id=turn_id,
                selected_steps=step_dicts,
                step_outputs=step_outputs,
                termination_reason="paused",
                latest_state=session_state,
                turn_output_bundle={
                    "assistant_message": assistant_msg,
                    "thinking": agent_result.get("thinking", ""),
                    "suggestion_document_obj": {"items": []},
                    "actionability_summary": {"total": 0, "apply_ready": 0, "confirm_required": len(fact_issues_paused)},
                    "fact_issues": fact_issues_paused,
                    "low_confidence_items": [],
                    "guide_prompts": [],
                    "step_reason_summary": step_reason_summary,
                    "self_check_result": {"result": "paused", "reason": "awaiting_user_confirmation"},
                    "planner_decision_trace": ctx.planner_decision_trace,
                    "thought_summary": ["暂停等待用户确认"],
                    "content_assessment": {"candidate_count": 0, "changed_count": 0, "material_change_count": 0, "fact_issue_count": len(fact_issues_paused), "style_variants": []},
                    "intent_state": ctx.intent_state,
                    "vague_actions": [],
                },
            )
            ctx.turn_output_bundle = final_payload.get("turn_output_bundle", {})
            yield from _sse.emit_turn_completed(final_payload)
            return

        # Convert agent result to the format compose_and_check expects
        raw_items = agent_result.get("items", []) or []
        fact_issues_from_agent = agent_result.get("fact_issues", []) or []
        guide_prompts_from_agent = agent_result.get("guide_prompts", []) or []

        # Get actual resume state for computing before/after diffs
        _resume_state = (session.get("state", {}) or {}) if isinstance(session, dict) else {}
        _resume_for_diff = (
            _resume_state.get("refined_document_obj", {}) if isinstance(_resume_state.get("refined_document_obj", {}), dict)
            else _resume_state.get("refined_resume_obj", {}) if isinstance(_resume_state.get("refined_resume_obj", {}), dict)
            else {}
        )

        # Convert raw items to suggestion items
        items_for_pipeline: list[dict[str, Any]] = []
        for i, ri in enumerate(raw_items):
            path = str(ri.get("path", ""))
            if not path:
                continue
            op = str(ri.get("op", "update"))

            # Read actual current value from resume state (not LLM-provided)
            actual_before = _get_by_path_local(_resume_for_diff, path)
            if actual_before is None or actual_before == "":
                actual_before = ri.get("current_value", "")

            # Use _to_display_text for readable display (handles lists, dicts, JSON strings)
            before_display = _to_display_text(actual_before)
            after_value = ri.get("value", "")
            after_display = _to_display_text(after_value)

            actionability = str(ri.get("actionability", "apply_ready"))
            if actionability not in {"apply_ready", "confirm_required"}:
                actionability = "apply_ready"
            items_for_pipeline.append({
                "section": path.split(".", 1)[0].split("[", 1)[0],
                "path": path, "op": op,
                "current_value": before_display,
                "suggested_value": after_display,
                "current_value_raw": actual_before,
                "suggested_value_raw": after_value,
                "reason": str(ri.get("reason", ""))[:60],
                "refined_text": str(ri.get("value", "")),
                "refined_value_raw": ri.get("value", ""),
                "option_id": "suggested",
                "option_label": {"update": "修改", "upsert": "新增", "delete": "删除"}.get(op, "修改"),
                "actionability": actionability,
                "requires_confirmation": actionability == "confirm_required",
                "confidence": float(ri.get("confidence", 0.8) or 0.8),
                "confidence_reason": "",
                "low_confidence": float(ri.get("confidence", 0.8) or 0.8) < 0.7,
                "task_id": f"fc_{i}",
            })

        merged = _normalize_suggestion_document_obj({"items": items_for_pipeline})
        merged = _expand_two_style_candidates(merged)
        merged = _normalize_suggestions(merged)
        save_session_state(session_id=session_id, suggestion_resume_obj=merged)

        visible = _visible_suggestions(merged, include_confirm_required=False)
        fextracted = _extract_fact_issues(merged)
        # Merge fact_issues from agent + extracted from normalization
        all_fact_issues = fact_issues_from_agent + fextracted if fact_issues_from_agent else fextracted

        agent_data = {
            "result": "ok",
            "target_scope": "global",
            "target_scopes": list({item.get("section", "") for item in items_for_pipeline if item.get("section")}),
            "suggestion_document_obj": visible,
            "full_suggestion_document_obj": merged,
            "fact_issues": all_fact_issues,
            "actionability_summary": _actionability_summary(merged),
            "meta": {"tool": "agent_loop", "items_count": len(items_for_pipeline)},
            "assistant_message": agent_result.get("assistant_message", ""),
            "jd_matches": agent_result.get("jd_matches", []),
            "thinking": agent_result.get("thinking", ""),
            "guide_prompts": guide_prompts_from_agent,
            "direct_error": "",
        }
        ctx.latest_refine_payload = agent_data
        ctx.latest_suggest_payload = agent_data

        extra: Dict[str, Any] = {}
        extra["actionability_summary"] = _actionability_summary(merged)
        extra["thinking"] = agent_result.get("thinking", "")
        yield from _sse.emit_step_succeeded(ctx, step_id, "agent_loop", _duration, **extra)

        # 2. Code-based verdict — no LLM compose call needed
        compose_step_id = "step_compose"
        yield from _sse.emit_plan_updated(ctx, "compose_and_check", "verdict")
        yield from _sse.emit_plan_step(ctx, compose_step_id, "compose_and_check", "verdict")
        yield from _sse.emit_step_started(ctx, compose_step_id, "compose_and_check")
        yield from _sse.emit_selfcheck_started(ctx)
        add_node_event(session_id=session_id, turn_id=turn_id, node_name="tool:compose_and_check", status="running", duration_ms=0, payload={})

        combined = _compose_and_self_check(
            message=ctx.message,
            latest_refine_payload=ctx.latest_refine_payload,
            session_id=ctx.session_id,
        )
        ctx.turn_output_bundle = combined
        ctx.last_self_check = {"result": combined.get("verdict", "pass"), "reason": combined.get("reason", "")}
        ctx.termination_reason = "composed"

        add_node_event(session_id=session_id, turn_id=turn_id, node_name="tool:compose_and_check", status="success", duration_ms=0, payload={"verdict": combined.get("verdict")})
        ctx.selected_steps.append(StepRecord(step_id=compose_step_id, tool="compose_and_check", status="success", duration_ms=0, reason_brief=combined.get("reason", "")))

        assistant_msg = str(combined.get("assistant_message", "")).strip()
        yield from _sse.emit_step_succeeded(ctx, compose_step_id, "compose_and_check", 0,
            verdict=combined.get("verdict"), verdict_reason=str(combined.get("reason", ""))[:200])
        yield from _sse.emit_turn_composed(ctx, assistant_msg)
        yield from _sse.emit_selfcheck_completed(ctx, {"result": combined.get("verdict"), "reason": combined.get("reason")})

        # 3. Finalize
        step_reason_summary = [{"step_id": s.step_id, "tool": s.tool, "reason_brief": s.reason_brief} for s in ctx.selected_steps]
        full_for_bundle = (
            ctx.turn_output_bundle.get("full_suggestion_document_obj", {})
            if isinstance(ctx.turn_output_bundle.get("full_suggestion_document_obj", {}), dict)
            else ctx.turn_output_bundle.get("suggestion_document_obj", {})
            if isinstance(ctx.turn_output_bundle.get("suggestion_document_obj", {}), dict)
            else {"items": []}
        )
        turn_output_bundle = _build_turn_output_bundle(
            assistant_message=assistant_msg or "",
            suggestion_document_obj=full_for_bundle,
            fact_issues=ctx.turn_output_bundle.get("fact_issues", []) if isinstance(ctx.turn_output_bundle.get("fact_issues", []), list) else [],
            step_reason_summary=step_reason_summary,
            self_check_result=ctx.last_self_check,
            planner_decision_trace=ctx.planner_decision_trace,
            thought_summary=ctx.turn_output_bundle.get("thought_summary", []) if isinstance(ctx.turn_output_bundle.get("thought_summary", []), list) else [],
            content_assessment=ctx.turn_output_bundle.get("content_assessment", {}) if isinstance(ctx.turn_output_bundle.get("content_assessment", {}), dict) else {},
            intent_state=ctx.intent_state,
            vague_actions=ctx.turn_output_bundle.get("vague_actions", []) if isinstance(ctx.turn_output_bundle.get("vague_actions", []), list) else [],
            thinking=str(ctx.turn_output_bundle.get("thinking", "")).strip(),
            guide_prompts=ctx.turn_output_bundle.get("guide_prompts", []) if isinstance(ctx.turn_output_bundle.get("guide_prompts", []), list) else [],
            low_confidence_items=ctx.turn_output_bundle.get("low_confidence_items", []) if isinstance(ctx.turn_output_bundle.get("low_confidence_items", []), list) else [],
        )
        ctx.turn_output_bundle = turn_output_bundle
        # Propagate JD matches: always include selected target JD, gate search results behind show_jd_cards
        jd_matches = agent_result.get("jd_matches", [])
        selected = [m for m in jd_matches if m.get("selected")]
        if selected:
            ctx.turn_output_bundle["target_jd"] = selected[0].get("text", "")
        if jd_matches and agent_result.get("show_jd_cards"):
            ctx.turn_output_bundle["jd_matches"] = jd_matches

        # Pass guide_prompts from direct_edit through to turn output
        guide_prompts_raw = ctx.latest_refine_payload.get("guide_prompts", []) if isinstance(ctx.latest_refine_payload.get("guide_prompts", []), list) else []
        if guide_prompts_raw:
            ctx.turn_output_bundle["guide_prompts"] = guide_prompts_raw

        assistant_message = str(turn_output_bundle.get("assistant_message", "")).strip() or ""
        assistant_row = add_message(session_id=session_id, turn_id=turn_id, role="assistant", content=assistant_message)
        finish_turn(turn_id=turn_id, status="completed", assistant_message_id=str(assistant_row.get("id", "")))

        latest_state = get_session_content(session_id=session_id, message_limit=CHAT_WINDOW, event_limit=200).get("state", {})
        latest_state = latest_state if isinstance(latest_state, dict) else {}
        final_payload = _build_turn_payload(
            session_id=session_id,
            session=session,
            turn_id=turn_id,
            selected_steps=[{"step_id": s.step_id, "tool": s.tool, "status": s.status, "duration_ms": s.duration_ms, "reason_brief": s.reason_brief} for s in ctx.selected_steps],
            step_outputs={k: v.data for k, v in ctx.step_outputs.items() if isinstance(v, ToolResult)},
            termination_reason=ctx.termination_reason,
            latest_state=latest_state,
            turn_output_bundle=ctx.turn_output_bundle,
        )
        _sse.record_event(ctx, "turn.completed", {k: v if isinstance(v, (dict, list)) else str(v)[:200]
                                                    for k, v in final_payload.items()
                                                    if k in ("assistant_message", "actionability_summary",
                                                             "termination_reason", "selected_tool_chain")})
        yield from _sse.emit_turn_completed(final_payload)

        _save_compact_turn_log(session_id=session_id, turn_id=turn_id, message=clean_message, final_payload=final_payload, ctx=ctx, agent_dump=agent_result)

        # Background: extract user preferences & key facts for cross-session memory
        from src.utils.context import get_user_id as _uid
        _user = _uid()
        if _user:
            import threading as _thr
            _msg = clean_message
            _bundle = ctx.turn_output_bundle if ctx.turn_output_bundle else {}
            _asst = str(_bundle.get("assistant_message", ""))
            # Collect proposed changes for context
            _suggestions = _bundle.get("suggestion_document_obj", {}) if isinstance(_bundle, dict) else {}
            _items = _suggestions.get("items", []) if isinstance(_suggestions, dict) else []
            _accepted = [i for i in _items if isinstance(i, dict) and i.get("status") == "applied"]
            _rejected = [i for i in _items if isinstance(i, dict) and i.get("status") == "rejected"]
            # Resume summary for context
            _resume_brief = {}
            try:
                _state = (session.get("state", {}) if isinstance(session, dict) else {})
                _refined = (_state.get("refined_document_obj") or _state.get("refined_resume_obj") or {})
                if isinstance(_refined, dict):
                    _resume_brief = {
                        "title": str(_refined.get("personalInfo", {}).get("title", ""))[:60] if isinstance(_refined.get("personalInfo", {}), dict) else "",
                        "summary": str(_refined.get("summary", ""))[:100],
                        "skills": str(_refined.get("additional", {}).get("technicalSkills", ""))[:80] if isinstance(_refined.get("additional", {}), dict) else "",
                    }
            except Exception:
                pass
            def _extract():
                from src.services.content_refinement_v3.memory.extractor import update_memory_after_turn
                n = update_memory_after_turn(
                    user_id=_user, user_message=_msg, assistant_message=_asst,
                    accepted_items=_accepted, rejected_items=_rejected,
                    resume_brief=_resume_brief,
                )
                if n > 0:
                    logger.info("[memory] updated %d items for user=%s", n, _user[:12])
            _thr.Thread(target=_extract, daemon=True).start()

    except Exception as exc:
        logger.exception("[v3][turn.error] session=%s turn=%s error=%s", session_id, turn_id, exc)
        add_node_event(session_id=session_id, turn_id=turn_id, node_name="tool:turn_runner_v3", status="failed", duration_ms=0, payload={}, error=str(exc))
        add_message(session_id=session_id, turn_id=turn_id, role="assistant", content="Sorry, something went wrong while processing your request. Please try again.")
        finish_turn(turn_id=turn_id, status="failed", error_text=str(exc))
        yield _sse_event("step.failed", {"turn_id": turn_id, "error": "Internal error"})
        error_payload = {"session_id": session_id, "turn_id": turn_id, "error": "Internal error", "termination_reason": "error"}
        _save_compact_turn_log(session_id=session_id, turn_id=turn_id, message=clean_message, final_payload=error_payload, ctx=ctx)
        yield _sse_event("turn.completed", error_payload)


def resume_turn_sse(*, session_id: str, turn_id: str,
                    user_response: str = "") -> Generator[str, None, None]:
    """Resume a paused turn. Loads saved LLM context, injects user response,
    continues the agent loop from where it left off."""
    session = get_session(session_id, include_state=True)
    if not session:
        raise ValueError("session not found")

    state = session.get("state", {}) or {}
    review = state.get("review_payload", {}) if isinstance(state.get("review_payload", {}), dict) else {}
    paused_messages = review.get("paused_messages", [])
    if not paused_messages:
        raise ValueError("no paused context found — turn may not be paused")

    # Find the last assistant message with tool_calls — this is the pending call
    last_assistant_idx = None
    for i in range(len(paused_messages) - 1, -1, -1):
        m = paused_messages[i]
        if m.get("role") == "assistant" and m.get("tool_calls"):
            last_assistant_idx = i
            break
    if last_assistant_idx is None:
        raise ValueError("no pending tool calls in paused context")

    # Append user response as a tool result for each pending tool call
    for tc in paused_messages[last_assistant_idx].get("tool_calls", []):
        paused_messages.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "content": user_response or "Confirmed.",
        })

    ctx = TurnContext(
        session_id=session_id,
        turn_id=turn_id,
        message=user_response or "Confirmed.",
        allow_mutation=True,
        max_steps=MAX_STEPS,
    )

    # Re-enter agent loop with saved context — LLM continues naturally
    result = _run_agent_loop(session_id, user_response, ctx,
        resume_messages=paused_messages)

    # Compose and finalize
    if result.get("_paused"):
        yield from _sse.emit_turn_paused(ctx, result.get("fact_issues", []))
        return

    raw_items = result.get("items", []) or []
    session_state = (session.get("state", {}) or {}) if isinstance(session, dict) else {}
    resume_for_diff = (
        session_state.get("refined_document_obj", {}) if isinstance(session_state.get("refined_document_obj", {}), dict)
        else session_state.get("refined_resume_obj", {}) if isinstance(session_state.get("refined_resume_obj", {}), dict)
        else {}
    )
    items_for_pipeline: list[dict[str, Any]] = []
    for i, ri in enumerate(raw_items):
        if not isinstance(ri, dict):
            continue
        path = str(ri.get("path", "") or "")
        if not path:
            continue
        op = str(ri.get("op", "update") or "update")
        actual_before = _get_by_path_local(resume_for_diff, path)
        if actual_before is None or actual_before == "":
            actual_before = ri.get("current_value", "")
        after_value = ri.get("value", "")
        items_for_pipeline.append({
            "section": path.split(".", 1)[0].split("[", 1)[0],
            "path": path,
            "op": op,
            "current_value": _to_display_text(actual_before),
            "suggested_value": _to_display_text(after_value),
            "current_value_raw": actual_before,
            "suggested_value_raw": after_value,
            "reason": str(ri.get("reason", ""))[:60],
            "refined_text": str(after_value),
            "refined_value_raw": after_value,
            "option_id": "confirmed",
            "option_label": "用户确认",
            "actionability": "apply_ready",
            "requires_confirmation": False,
            "user_confirmed": True,
            "confirmation_source": "user",
            "confidence": float(ri.get("confidence", 0.9) or 0.9),
            "confidence_reason": "confirmed_by_user",
            "low_confidence": False,
            "task_id": f"resume_{i}",
        })

    merged = _normalize_suggestion_document_obj({"items": items_for_pipeline})
    merged = _normalize_suggestions(merged)
    if items_for_pipeline:
        save_session_state(session_id=session_id, suggestion_resume_obj=merged)

    visible = _visible_suggestions(merged, include_confirm_required=False)
    assistant_msg = str(result.get("assistant_message", "") or "")
    add_message(session_id=session_id, turn_id=turn_id, role="assistant", content=assistant_msg)
    yield from _sse.emit_turn_composed(ctx, assistant_msg)

    ctx.termination_reason = "composed"
    selected_steps = [{
        "step_id": "step_resume_agent_loop",
        "tool": "agent_loop",
        "status": "success",
        "duration_ms": 0,
        "reason_brief": "resumed_after_confirmation",
    }]
    payload = _build_turn_payload(
        session_id=session_id, session=session, turn_id=turn_id,
        selected_steps=selected_steps, step_outputs={},
        termination_reason=ctx.termination_reason,
        latest_state=get_session_content(session_id=session_id, message_limit=CHAT_WINDOW, event_limit=200).get("state", {}),
        turn_output_bundle={
            "assistant_message": assistant_msg,
            "suggestion_document_obj": visible,
            "full_suggestion_document_obj": merged,
            "actionability_summary": _actionability_summary(merged),
            "fact_issues": [],
            "low_confidence_items": [],
            "step_reason_summary": [{"step_id": "step_resume_agent_loop", "tool": "agent_loop", "reason_brief": "resumed_after_confirmation"}],
            "self_check_result": {"result": "pass", "reason": "resumed"},
            "thought_summary": ["已恢复并继续"],
            "content_assessment": _build_content_assessment(visible, []),
            "intent_state": {},
            "vague_actions": [],
            "thinking": result.get("thinking", ""),
            "guide_prompts": result.get("guide_prompts", []),
        },
    )
    finish_turn(turn_id=turn_id, status="completed")
    _save_compact_turn_log(session_id=session_id, turn_id=turn_id, message=f"[resume] {user_response}", final_payload=payload, ctx=ctx)
    yield from _sse.emit_turn_completed(payload)


def apply_changes(*, session_id: str, human_review_decision: Dict[str, Any] | None = None, suggestion_document_obj: Dict[str, Any] | None = None) -> Dict[str, Any]:
    session, _, snapshot = _session_state_snapshot(session_id)
    if not session:
        raise ValueError("session not found")

    decision = human_review_decision if isinstance(human_review_decision, dict) else {}
    accepted_item_keys = [str(item).strip() for item in (decision.get("accepted_item_keys", []) if isinstance(decision.get("accepted_item_keys", []), list) else []) if str(item).strip()]
    if not accepted_item_keys:
        raise ValueError("accepted_item_keys is required")

    suggestions_source = suggestion_document_obj if isinstance(suggestion_document_obj, dict) and isinstance(suggestion_document_obj.get("items", []), list) else snapshot.get("suggestion_document_obj", {"items": []})
    normalized = _normalize_suggestions(suggestions_source)

    key_to_item: Dict[str, Dict[str, Any]] = {}
    for item in normalized.get("items", []):
        if not isinstance(item, dict):
            continue
        key = str(item.get("item_key", "")).strip()
        if not key:
            continue
        if str(item.get("actionability", "apply_ready")).strip().lower() == "confirm_required":
            continue
        if str(item.get("status", "pending")).strip().lower() != "pending":
            continue
        key_to_item[key] = item

    def _split_item_key(raw_key: str) -> Tuple[str, str]:
        text = str(raw_key or "").strip()
        if not text:
            return "", ""
        if "::" in text:
            path, option = text.split("::", 1)
            return path.strip(), option.strip().lower()
        return text, ""

    def _option_token_from_item(candidate_key: str, candidate_item: Dict[str, Any]) -> str:
        option = str(candidate_item.get("option_id", "")).strip().lower()
        if option:
            return option
        _, key_option = _split_item_key(candidate_key)
        return key_option

    def _option_aliases(option: str) -> List[str]:
        token = str(option or "").strip().lower()
        aliases = [token] if token else []
        if token in {"suggested", "default"}:
            aliases.extend(["default", "suggested", ""])
        elif token in {"refined", "refine", "refine_1"}:
            aliases.extend(["refined", "refine", "refine_1", "default", ""])
        elif token.startswith("refine_"):
            aliases.extend(["refined", "refine", "default", ""])
        elif token == "":
            aliases.extend(["default", "suggested", ""])
        deduped: List[str] = []
        seen_alias = set()
        for alias in aliases:
            if alias in seen_alias:
                continue
            seen_alias.add(alias)
            deduped.append(alias)
        return deduped

    def _value_signature(candidate_item: Dict[str, Any]) -> str:
        value = candidate_item.get("refined_value_raw", candidate_item.get("suggested_value_raw", candidate_item.get("suggested_value")))
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        except Exception:
            return str(value)

    resolved_item_keys: List[str] = []
    missing: List[str] = []
    for raw_key in accepted_item_keys:
        if raw_key in key_to_item:
            resolved_item_keys.append(raw_key)
            continue
        fallback_path, requested_option = _split_item_key(raw_key)
        if not fallback_path:
            missing.append(raw_key)
            continue
        path_candidates: List[Tuple[str, Dict[str, Any]]] = [
            (key, item)
            for key, item in key_to_item.items()
            if str(item.get("path", "")).strip() == fallback_path
        ]
        if requested_option:
            exact_option = [
                (key, item)
                for key, item in path_candidates
                if _option_token_from_item(key, item) == requested_option
            ]
            if len(exact_option) == 1:
                resolved_item_keys.append(exact_option[0][0])
                continue
            alias_tokens = _option_aliases(requested_option)
            alias_matches = [
                (key, item)
                for key, item in path_candidates
                if _option_token_from_item(key, item) in alias_tokens
            ]
            if len(alias_matches) == 1:
                resolved_item_keys.append(alias_matches[0][0])
                continue
            if len(alias_matches) > 1:
                value_signatures = {_value_signature(item) for _, item in alias_matches}
                if len(value_signatures) == 1:
                    resolved_item_keys.append(alias_matches[0][0])
                    continue
        if len(path_candidates) == 1:
            resolved_item_keys.append(path_candidates[0][0])
            continue
        missing.append(raw_key)

    if missing:
        raise ValueError(f"invalid accepted_item_keys: {', '.join(missing)}")

    # Deduplicate while preserving order.
    dedup_seen: set[str] = set()
    resolved_item_keys = [key for key in resolved_item_keys if not (key in dedup_seen or dedup_seen.add(key))]

    refined = deepcopy(snapshot.get("refined_document_obj", {}))
    refined = refined if isinstance(refined, dict) else {}

    turn = create_turn(session_id=session_id)
    turn_id = str(turn.get("id", ""))
    add_node_event(session_id=session_id, turn_id=turn_id, node_name="tool:apply_changes", status="running", duration_ms=0, payload={"accepted_count": len(resolved_item_keys)})
    started = time.perf_counter()

    applied_changes: List[Dict[str, Any]] = []
    failed_changes: List[Dict[str, Any]] = []
    for key in resolved_item_keys:
        item = key_to_item[key]
        op = str(item.get("op", "update")).strip().lower()
        if op not in {"update", "upsert", "delete"}:
            op = "update"
        path = str(item.get("path", "")).strip()
        suggested_value = item.get("refined_value_raw", item.get("suggested_value_raw", item.get("suggested_value")))

        if op == "delete":
            if _delete_by_path(refined, path):
                applied_changes.append({"path": path, "item_key": key, "source": "suggestion", "op": "delete", "status": "applied", "reason": str(item.get("reason", "")).strip()})
                item["status"] = "applied"
            else:
                failed_changes.append({"path": path, "item_key": key, "source": "suggestion", "op": "delete", "status": "failed", "reason": str(item.get("reason", "")).strip(), "error": f"路径 {path} 不存在，无法删除。"})
                item["status"] = "failed"
        else:
            if _set_by_path(refined, path, suggested_value):
                applied_changes.append({"path": path, "item_key": key, "source": "suggestion", "op": op, "status": "applied", "reason": str(item.get("reason", "")).strip()})
                item["status"] = "applied"
            else:
                failed_changes.append({"path": path, "item_key": key, "source": "suggestion", "op": op, "status": "failed", "reason": str(item.get("reason", "")).strip(), "error": f"路径 {path} 无法应用{'新增' if op == 'upsert' else '修改'}，请检查路径是否正确。"})
                item["status"] = "failed"

    overrides = decision.get("overrides", []) if isinstance(decision.get("overrides", []), list) else []
    for override in overrides:
        if not isinstance(override, dict):
            continue
        path = str(override.get("path", "")).strip()
        if not path:
            continue
        if _set_by_path(refined, path, override.get("value")):
            applied_changes.append({"path": path, "item_key": "", "source": "override", "status": "applied", "reason": "manual_override"})
        else:
            failed_changes.append({"path": path, "item_key": "", "source": "override", "status": "failed", "reason": "manual_override", "error": f"路径 {path} 在简历中不存在，无法应用覆盖。"})

    persisted = _normalize_suggestions(normalized)
    existing = (session.get("state", {}) if isinstance(session, dict) else {}).get("review_payload", {}) if isinstance(session.get("state", {}), dict) else {}
    existing = existing if isinstance(existing, dict) else {}
    review_payload = {"items": []}
    if existing.get("paused_messages"):
        review_payload["paused_messages"] = existing["paused_messages"]
        review_payload["turn_id"] = existing.get("turn_id", "")
    save_session_state(session_id=session_id, refined_resume_obj=refined, suggestion_resume_obj=persisted, review_payload=review_payload)
    _record_version(session_id=session_id, refined_document_obj=refined, suggestion_document_obj=persisted, source="apply", turn_id=turn_id, note=f"accepted={len(resolved_item_keys)}")

    duration_ms = int((time.perf_counter() - started) * 1000)
    add_node_event(
        session_id=session_id,
        turn_id=turn_id,
        node_name="tool:apply_changes",
        status="success",
        duration_ms=duration_ms,
        payload={"applied_count": len([item for item in applied_changes if item.get("source") == "suggestion"]), "override_count": len([item for item in applied_changes if item.get("source") == "override"])},
    )

    applied_count = len([item for item in applied_changes if item.get("source") == "suggestion"])
    failed_count = len(failed_changes)
    all_changes = applied_changes + failed_changes
    if failed_count > 0:
        assistant_message = f"已应用 {applied_count} 条候选，{failed_count} 条因路径不存在而失败。"
    else:
        assistant_message = f"已应用 {applied_count} 条候选。"
    assistant_row = add_message(session_id=session_id, turn_id=turn_id, role="assistant", content=assistant_message)
    finish_turn(turn_id=turn_id, status="completed", assistant_message_id=str(assistant_row.get("id", "")))

    # Background: update user profile with accepted/rejected patterns
    return _build_action_turn_payload(session_id=session_id, turn_id=turn_id, assistant_message=assistant_message, refined_document_obj=refined, suggestion_document_obj=persisted, applied_changes=all_changes, termination_reason="applied")


def reject_changes(*, session_id: str, rejected_item_keys: List[str] | None = None, reject_all: bool = False, suggestion_document_obj: Dict[str, Any] | None = None) -> Dict[str, Any]:
    session, _, snapshot = _session_state_snapshot(session_id)
    if not session:
        raise ValueError("session not found")

    suggestions_source = suggestion_document_obj if isinstance(suggestion_document_obj, dict) and isinstance(suggestion_document_obj.get("items", []), list) else snapshot.get("suggestion_document_obj", {"items": []})
    normalized = _normalize_suggestions(suggestions_source)

    pending_apply_ready_keys = [
        str(item.get("item_key", "")).strip()
        for item in normalized.get("items", [])
        if isinstance(item, dict)
        and str(item.get("status", "pending")).strip().lower() == "pending"
        and str(item.get("actionability", "apply_ready")).strip().lower() == "apply_ready"
        and str(item.get("item_key", "")).strip()
    ]
    explicit_keys = [str(key).strip() for key in (rejected_item_keys or []) if str(key).strip()]
    target_keys = set(pending_apply_ready_keys if reject_all else explicit_keys)
    if not target_keys:
        raise ValueError("rejected_item_keys is required when reject_all is false")

    known_keys = {str(item.get("item_key", "")).strip() for item in normalized.get("items", []) if isinstance(item, dict)}
    unknown = [key for key in target_keys if key not in known_keys]
    if unknown:
        raise ValueError(f"invalid rejected_item_keys: {', '.join(sorted(unknown))}")

    turn = create_turn(session_id=session_id)
    turn_id = str(turn.get("id", ""))
    add_node_event(session_id=session_id, turn_id=turn_id, node_name="tool:reject_changes", status="running", duration_ms=0, payload={"rejected_count": len(target_keys)})
    started = time.perf_counter()

    for item in normalized.get("items", []):
        if not isinstance(item, dict):
            continue
        key = str(item.get("item_key", "")).strip()
        if key in target_keys:
            item["status"] = "rejected"

    existing_rp = (session.get("state", {}) if isinstance(session, dict) else {}).get("review_payload", {}) if isinstance(session.get("state", {}), dict) else {}
    existing_rp = existing_rp if isinstance(existing_rp, dict) else {}
    rp = {"items": []}
    if existing_rp.get("paused_messages"):
        rp["paused_messages"] = existing_rp["paused_messages"]
        rp["turn_id"] = existing_rp.get("turn_id", "")
    save_session_state(session_id=session_id, suggestion_resume_obj=normalized, review_payload=rp)
    _record_version(session_id=session_id, refined_document_obj=snapshot.get("refined_document_obj", {}), suggestion_document_obj=normalized, source="reject", turn_id=turn_id, note=f"rejected={len(target_keys)}")

    duration_ms = int((time.perf_counter() - started) * 1000)
    add_node_event(session_id=session_id, turn_id=turn_id, node_name="tool:reject_changes", status="success", duration_ms=duration_ms, payload={"rejected_count": len(target_keys), "reject_all": bool(reject_all)})

    assistant_message = f"已拒绝 {len(target_keys)} 条候选。"
    assistant_row = add_message(session_id=session_id, turn_id=turn_id, role="assistant", content=assistant_message)
    finish_turn(turn_id=turn_id, status="completed", assistant_message_id=str(assistant_row.get("id", "")))
    return _build_action_turn_payload(session_id=session_id, turn_id=turn_id, assistant_message=assistant_message, refined_document_obj=snapshot.get("refined_document_obj", {}), suggestion_document_obj=normalized, applied_changes=[], termination_reason="rejected")


def rollback_changes(*, session_id: str, version_id: str, note: str = "") -> Dict[str, Any]:
    return rollback_to_version(session_id=session_id, version_id=version_id, note=note)
