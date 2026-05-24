"""Turn payload builders."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.services.content_refinement_v3.backends.session import list_node_events
from ._suggestion import _visible_suggestions, _extract_fact_issues, _extract_low_confidence_items, _actionability_summary, _build_content_assessment

def _build_turn_output_bundle(
    *,
    assistant_message: str,
    suggestion_document_obj: Dict[str, Any],
    fact_issues: List[Dict[str, Any]],
    step_reason_summary: List[Dict[str, Any]],
    self_check_result: Dict[str, Any],
    planner_decision_trace: List[Dict[str, Any]] | None = None,
    thought_summary: List[str] | None = None,
    content_assessment: Dict[str, Any] | None = None,
    intent_state: Dict[str, Any] | None = None,
    vague_actions: List[Dict[str, str]] | None = None,
    thinking: str = "",
    guide_prompts: List[Dict[str, str]] | None = None,
    low_confidence_items: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    visible = _visible_suggestions(suggestion_document_obj, include_confirm_required=False)
    return {
        "assistant_message": assistant_message,
        "thinking": thinking,
        "suggestion_document_obj": visible,
        "actionability_summary": _actionability_summary(suggestion_document_obj),
        "fact_issues": fact_issues,
        "low_confidence_items": low_confidence_items or [],
        "guide_prompts": guide_prompts or [],
        "step_reason_summary": step_reason_summary,
        "self_check_result": self_check_result,
        "planner_decision_trace": planner_decision_trace or [],
        "thought_summary": thought_summary or [],
        "content_assessment": content_assessment or {},
        "intent_state": intent_state or {},
        "vague_actions": vague_actions or [],
    }


def _build_turn_payload(*, session_id: str, session: Dict[str, Any], turn_id: str, selected_steps: List[Dict[str, Any]], step_outputs: Dict[str, Any], termination_reason: str, latest_state: Dict[str, Any], turn_output_bundle: Dict[str, Any]) -> Dict[str, Any]:
    refined_document_obj = (
        latest_state.get("refined_document_obj", {})
        if isinstance(latest_state.get("refined_document_obj", {}), dict)
        else latest_state.get("refined_resume_obj", {})
        if isinstance(latest_state.get("refined_resume_obj", {}), dict)
        else {}
    )
    return {
        "session_id": session_id,
        "doc_type": str(session.get("doc_type", "resume")),
        "turn_id": turn_id,
        "selected_steps": selected_steps,
        "selected_tool_chain": [str(item.get("tool", "")) for item in selected_steps],
        "step_outputs_summary": {"count": len(step_outputs), "keys": list(step_outputs.keys())},
        "termination_reason": termination_reason,
        "turn_output_bundle": turn_output_bundle,
        "assistant_message": str(turn_output_bundle.get("assistant_message", "")).strip(),
        "suggestion_document_obj": turn_output_bundle.get("suggestion_document_obj", {"items": []}),
        "actionability_summary": turn_output_bundle.get("actionability_summary", {"total": 0, "apply_ready": 0, "confirm_required": 0}),
        "fact_issues": turn_output_bundle.get("fact_issues", []),
        "step_reason_summary": turn_output_bundle.get("step_reason_summary", []),
        "self_check_result": turn_output_bundle.get("self_check_result", {"result": "pass", "reason": ""}),
        "planner_decision_trace": turn_output_bundle.get("planner_decision_trace", []),
        "thought_summary": turn_output_bundle.get("thought_summary", []),
        "content_assessment": turn_output_bundle.get("content_assessment", {}),
        "intent_state": turn_output_bundle.get("intent_state", {}),
        "vague_actions": turn_output_bundle.get("vague_actions", []),
        "thinking": turn_output_bundle.get("thinking", ""),
        "guide_prompts": turn_output_bundle.get("guide_prompts", []),
        "low_confidence_items": turn_output_bundle.get("low_confidence_items", []),
        "rag_context_by_path": latest_state.get("rag_context_by_path", {}) if isinstance(latest_state.get("rag_context_by_path", {}), dict) else {},
        "refined_document_obj": refined_document_obj,
        "quality_report": latest_state.get("quality_report", {}) if isinstance(latest_state.get("quality_report", {}), dict) else {},
        "section_quality_map": latest_state.get("section_quality_map", {}) if isinstance(latest_state.get("section_quality_map", {}), dict) else {},
        "node_events": list_node_events(session_id=session_id, turn_id=turn_id),
    }


def _build_action_turn_payload(*, session_id: str, turn_id: str, assistant_message: str, refined_document_obj: Dict[str, Any], suggestion_document_obj: Dict[str, Any], applied_changes: List[Dict[str, Any]], termination_reason: str) -> Dict[str, Any]:
    visible = _visible_suggestions(suggestion_document_obj, include_confirm_required=False)
    summary = _actionability_summary(visible)
    turn_output_bundle = {
        "assistant_message": assistant_message,
        "suggestion_document_obj": visible,
        "actionability_summary": summary,
        "fact_issues": _extract_fact_issues(suggestion_document_obj),
        "step_reason_summary": [],
        "self_check_result": {"result": "pass", "reason": "action_endpoint"},
        "planner_decision_trace": [],
        "thought_summary": [],
        "content_assessment": _build_content_assessment(visible, _extract_fact_issues(suggestion_document_obj)),
        "intent_state": {},
    }
    return {
        "session_id": session_id,
        "turn_id": turn_id,
        "assistant_message": assistant_message,
        "document_obj": refined_document_obj,
        "refined_document_obj": refined_document_obj,
        "applied_changes": applied_changes,
        "suggestion_document_obj": visible,
        "actionability_summary": summary,
        "termination_reason": termination_reason,
        "turn_output_bundle": turn_output_bundle,
        "validation_report": {},
        "decision_meta": {},
        "node_events": list_node_events(session_id=session_id, turn_id=turn_id),
    }

