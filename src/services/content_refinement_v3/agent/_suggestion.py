"""Suggestion normalization, extraction, visibility, scope resolution."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from ._utils import (_to_display_text, _canonical_semantic_text, _is_format_only_candidate,
    _is_fact_sensitive_change, _make_item_key, _build_diff_payload, _tokenize_path,
    _infer_scope_from_message, _is_global_edit_intent, _is_edit_intent)

GLOBAL_SCOPES = ["summary", "workExperience", "education", "personalProjects", "research", "additional", "personalInfo"]


def _expand_two_style_candidates(suggestion_obj: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_suggestions(suggestion_obj)
    items = normalized.get("items", [])
    if not isinstance(items, list):
        return normalized
    expanded: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        expanded.append(item)
        if str(item.get("actionability", "apply_ready")).strip().lower() != "apply_ready":
            continue
        if str(item.get("status", "pending")).strip().lower() != "pending":
            continue
        if str(item.get("style_variant", "")).strip().lower() == "impact":
            continue
        impact_item = dict(item)
        impact_item["style_variant"] = "impact"
        impact_item["option_label"] = str(item.get("option_label", "")).strip() or "Impact version"
        base_option = str(item.get("option_id", "")).strip() or "default"
        impact_item["option_id"] = f"{base_option}_impact"
        impact_item["item_key"] = _make_item_key(impact_item)
        refined_text = _to_display_text(
            impact_item.get("refined_text", impact_item.get("refined_value_raw", impact_item.get("suggested_value_raw", impact_item.get("suggested_value"))))
        ).strip()
        if refined_text:
            if not refined_text.endswith("."):
                refined_text += "."
            impact_item["refined_text"] = refined_text
            impact_item["suggested_value"] = refined_text
            impact_item["suggested_value_raw"] = refined_text
            impact_item["refined_value_raw"] = refined_text
        impact_item["reason"] = "Alternative version with stronger outcome framing."
        impact_item["reason_meta"] = {"change_type": "focus", "expected_effect": "Increase impact framing"}
        expanded.append(impact_item)

        conservative_item = dict(item)
        conservative_item["style_variant"] = str(item.get("style_variant", "")).strip() or "conservative"
        conservative_item["option_label"] = str(item.get("option_label", "")).strip() or "Conservative version"
        conservative_item["reason_meta"] = conservative_item.get("reason_meta", {"change_type": "content", "expected_effect": "Preserve meaning and improve wording"})
        expanded[-2] = conservative_item

    return _normalize_suggestions(
        {
            "items": expanded,
            "suggestion_status_by_key": normalized.get("suggestion_status_by_key", {}),
        }
    )


def _build_content_assessment(visible_suggestions: Dict[str, Any], fact_issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    items = visible_suggestions.get("items", []) if isinstance(visible_suggestions.get("items", []), list) else []
    changed_items = 0
    material_items = 0
    style_variants = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        before_text = _to_display_text(item.get("current_value_raw", item.get("current_value")))
        after_text = _to_display_text(
            item.get("refined_text", item.get("refined_value_raw", item.get("suggested_value_raw", item.get("suggested_value"))))
        )
        if before_text != after_text:
            changed_items += 1
        if _canonical_semantic_text(before_text) != _canonical_semantic_text(after_text):
            material_items += 1
        variant = str(item.get("style_variant", "")).strip().lower()
        if variant:
            style_variants.add(variant)
    return {
        "candidate_count": len(items),
        "changed_count": changed_items,
        "material_change_count": material_items,
        "fact_issue_count": len(fact_issues or []),
        "style_variants": sorted(style_variants),
    }



def _normalize_suggestions(source: Dict[str, Any] | None) -> Dict[str, Any]:
    raw = source if isinstance(source, dict) else {"items": []}
    raw_items = raw.get("items", []) if isinstance(raw.get("items", []), list) else []
    status_by_key = raw.get("suggestion_status_by_key", {}) if isinstance(raw.get("suggestion_status_by_key", {}), dict) else {}
    normalized_items: List[Dict[str, Any]] = []
    filtered_format_only = 0
    converted_confirm_required = 0

    for item in raw_items:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip()
        if not path:
            continue
        fact_paths = [
            r"personalinfo\.name", r"personalinfo\.email", r"personalinfo\.phone",
            r"personalinfo\.location", r"personalinfo\.linkedin", r"personalinfo\.github",
            r"\.years$", r"\.gpa", r"\.institution", r"\.degree",
        ]
        is_fact_field = any(re.search(p, str(item.get("path", "")).strip().lower()) for p in fact_paths)

        if _is_format_only_candidate(item):
            # Fact-sensitive fields must NOT be silently dropped even when
            # before == after 鈥?the user needs a confirmation, not silence.
            if not is_fact_field:
                filtered_format_only += 1
                continue
            # Force confirm_required for fact items with no material change
            item["actionability"] = "confirm_required"

        actionability = str(item.get("actionability", "apply_ready")).strip().lower()
        if actionability not in {"apply_ready", "confirm_required"}:
            actionability = "apply_ready"
        user_confirmed = item.get("user_confirmed") is True or str(item.get("confirmation_source", "")).strip() == "user"
        # Upgrade: fact-sensitive + very low confidence (<0.4) 鈫?confirm_required
        try:
            _conf = float(item.get("confidence", 1.0) if item.get("confidence") is not None else 1.0)
        except (ValueError, TypeError):
            _conf = 1.0
        if user_confirmed:
            actionability = "apply_ready"
        elif is_fact_field and _conf < 0.4 and actionability == "apply_ready":
            actionability = "confirm_required"
            item["confidence_reason"] = str(item.get("confidence_reason", "")).strip() or "Low confidence on a fact-sensitive field"
            converted_confirm_required += 1
        elif actionability == "apply_ready" and _is_fact_sensitive_change(item):
            actionability = "confirm_required"
            converted_confirm_required += 1
        item_key = str(item.get("item_key", "")).strip() or _make_item_key(item)
        status = str(item.get("status", "")).strip().lower() or str(status_by_key.get(item_key, "")).strip().lower() or "pending"
        if status not in {"pending", "applied", "rejected"}:
            status = "pending"
        status_by_key[item_key] = status
        normalized_items.append(
            {
                **item,
                "item_key": item_key,
                "actionability": actionability,
                "requires_confirmation": bool(item.get("requires_confirmation", False)) or actionability == "confirm_required",
                "status": status,
                "diff_payload": item.get("diff_payload", _build_diff_payload(item)),
                "style_variant": str(item.get("style_variant", "")).strip() or "conservative",
                "reason_meta": item.get("reason_meta", {"change_type": "content", "expected_effect": ""}),
                "confirmation_hint": (
                    str(item.get("confirmation_hint", "")).strip()
                    or ("Fact-sensitive change; please confirm before applying." if actionability == "confirm_required" else "")
                ),
            }
        )

    return {
        "items": normalized_items,
        "suggestion_status_by_key": status_by_key,
        "meta": {
            "filtered_format_only": filtered_format_only,
            "converted_confirm_required": converted_confirm_required,
        },
    }


def _visible_suggestions(suggestions: Dict[str, Any], *, include_confirm_required: bool) -> Dict[str, Any]:
    normalized = _normalize_suggestions(suggestions)
    visible: List[Dict[str, Any]] = []
    for item in normalized.get("items", []):
        if not isinstance(item, dict):
            continue
        if str(item.get("status", "pending")).strip().lower() != "pending":
            continue
        actionability = str(item.get("actionability", "apply_ready")).strip().lower()
        if actionability == "apply_ready":
            visible.append(item)
        elif include_confirm_required:
            visible.append(item)
    return {"items": visible}


def _extract_fact_issues(suggestions: Dict[str, Any]) -> List[Dict[str, Any]]:
    normalized = _normalize_suggestions(suggestions)
    out: List[Dict[str, Any]] = []
    for item in normalized.get("items", []):
        if not isinstance(item, dict):
            continue
        if str(item.get("status", "pending")).strip().lower() != "pending":
            continue
        if str(item.get("actionability", "apply_ready")).strip().lower() != "confirm_required":
            continue
        out.append(
            {
                "path": str(item.get("path", "")).strip(),
                "item_key": str(item.get("item_key", "")).strip(),
                "current_value": str(item.get("current_value", "")).strip(),
                "suggested_value": str(item.get("suggested_value", "")).strip(),
                "op": str(item.get("op", "update")).strip(),
                "confirmation_hint": str(item.get("confirmation_hint", "")).strip(),
                "reason": str(item.get("reason", "")).strip(),
            }
        )
    return out


def _extract_low_confidence_items(suggestions: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Collect items marked low_confidence that are still apply_ready."""
    normalized = _normalize_suggestions(suggestions)
    out: List[Dict[str, Any]] = []
    for item in normalized.get("items", []):
        if not isinstance(item, dict):
            continue
        if str(item.get("status", "pending")).strip().lower() != "pending":
            continue
        if not item.get("low_confidence"):
            continue
        if str(item.get("actionability", "apply_ready")).strip().lower() == "confirm_required":
            continue
        out.append({
            "path": str(item.get("path", "")).strip(),
            "item_key": str(item.get("item_key", "")).strip(),
            "confidence": float(item.get("confidence", 1.0)) if isinstance(item.get("confidence"), (int, float)) else 1.0,
            "confidence_reason": str(item.get("confidence_reason", "")).strip(),
            "reason": str(item.get("reason", "")).strip(),
            "refined_text": str(item.get("refined_text", "")).strip(),
        })
    return out


def _actionability_summary(suggestion_obj: Dict[str, Any] | None) -> Dict[str, int]:
    source = suggestion_obj if isinstance(suggestion_obj, dict) else {"items": []}
    items = source.get("items", []) if isinstance(source.get("items", []), list) else []
    apply_ready = 0
    confirm_required = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("actionability", "apply_ready")).strip().lower() == "confirm_required":
            confirm_required += 1
        else:
            apply_ready += 1
    return {"total": apply_ready + confirm_required, "apply_ready": apply_ready, "confirm_required": confirm_required}


def _scope_content_from_state(state: Dict[str, Any], target_scope: str) -> Any:
    if not target_scope:
        return None
    refined = (
        state.get("refined_document_obj", {})
        if isinstance(state.get("refined_document_obj", {}), dict)
        else state.get("refined_resume_obj", {})
        if isinstance(state.get("refined_resume_obj", {}), dict)
        else {}
    )
    value: Any = refined
    for part in target_scope.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
        if value is None:
            return None
    return value


def _resolve_target_scopes(message: str, observed: Dict[str, Any]) -> List[str]:
    intent_state = observed.get("intent_state", {}) if isinstance(observed.get("intent_state", {}), dict) else {}
    state_scope = str(intent_state.get("active_scope", "")).strip()
    confidence = float(intent_state.get("confidence", 0) or 0)
    # Normalize: LLM sometimes outputs "workExperience[0],workExperience[1]" 鈥?extract base scope
    if "," in state_scope:
        first = state_scope.split(",")[0].strip()
        state_scope = first.split("[")[0] if "[" in first else first
    if state_scope == "global":
        return GLOBAL_SCOPES
    if state_scope and confidence >= 0.5:
        return [state_scope]

    observed_scope = str(observed.get("target_scope", "")).strip()
    if observed_scope and not _is_global_edit_intent(message):
        return [observed_scope]
    if _is_global_edit_intent(message):
        return GLOBAL_SCOPES
    inferred = _infer_scope_from_message(message)
    if inferred:
        return [inferred]
    if _is_edit_intent(message):
        return ["summary", "workExperience", "education", "personalProjects", "research"]
    return ["summary"]


def _merge_suggestion_documents(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    base_norm = _normalize_suggestions(base)
    incoming_norm = _normalize_suggestions(incoming)
    merged_map: Dict[str, Dict[str, Any]] = {}
    for item in base_norm.get("items", []):
        if not isinstance(item, dict):
            continue
        key = str(item.get("item_key", "")).strip() or _make_item_key(item)
        if key:
            merged_map[key] = item
    for item in incoming_norm.get("items", []):
        if not isinstance(item, dict):
            continue
        key = str(item.get("item_key", "")).strip() or _make_item_key(item)
        if key:
            merged_map[key] = item
    merged = {"items": list(merged_map.values())}
    return _normalize_suggestions(merged)


