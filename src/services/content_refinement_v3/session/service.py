import json
from copy import deepcopy
from typing import Any, Dict, List

# (build_scoped_refine_system_prompt removed — dead code cleaned up)
from .queries import (
    get_session_content as _queries_get_session_content,
)
from .store import (
    add_message,
    add_node_event,
    add_session_version,
    create_session,
    create_turn,
    finish_turn,
    get_session,
    get_session_version,
    list_node_events,
    save_session_state,
)

CHAT_MEMORY_LIMIT = 5

# ═══════════════════════════════════════════════════════════════════
# Basic utilities
# ═══════════════════════════════════════════════════════════════════


def _as_dict(value: Any, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {} if default is None else default


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _to_text(value: Any) -> str:
    return str(value or "").strip()


def _to_readable_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        chunks: List[str] = []
        for item in value:
            item_text = _to_readable_text(item)
            if item_text:
                chunks.append(item_text)
        return "\n".join(chunks).strip()
    if isinstance(value, dict):
        preferred_keys = [
            "name", "title", "institution", "degree",
            "company", "years", "description", "summary",
        ]
        used: set[str] = set()
        parts: List[str] = []
        for key in preferred_keys:
            if key in value:
                used.add(key)
                text = _to_readable_text(value.get(key))
                if text:
                    parts.append(text)
        for key, raw in value.items():
            if key in used:
                continue
            text = _to_readable_text(raw)
            if text:
                parts.append(text)
        return " | ".join(parts).strip()
    return str(value).strip()


# ═══════════════════════════════════════════════════════════════════
# Path utilities
# ═══════════════════════════════════════════════════════════════════


def _tokenize_path_local(path: str) -> List[str | int]:
    import re
    tokens: List[str | int] = []
    for part in str(path or "").split("."):
        if not part:
            continue
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)", part)
        if not m:
            continue
        tokens.append(m.group(1))
        for idx in re.findall(r"\[(\d+)\]", part):
            tokens.append(int(idx))
    return tokens


def _get_by_path_local(obj: Any, path: str) -> Any:
    tokens = _tokenize_path_local(path)
    cur = obj
    for token in tokens:
        if isinstance(token, int):
            if not isinstance(cur, list) or token >= len(cur):
                return None
            cur = cur[token]
        else:
            if not isinstance(cur, dict) or token not in cur:
                return None
            cur = cur[token]
    return cur


def _set_by_path_local(obj: Any, path: str, value: Any, upsert: bool = False) -> bool:
    tokens = _tokenize_path_local(path)
    if not tokens:
        return False
    cur = obj
    for token in tokens[:-1]:
        if isinstance(token, int):
            if not isinstance(cur, list) or token >= len(cur):
                return False
            cur = cur[token]
        else:
            if not isinstance(cur, dict) or token not in cur:
                return False
            cur = cur[token]
    last = tokens[-1]
    if isinstance(last, int):
        if not isinstance(cur, list):
            return False
        if last > len(cur) or (last == len(cur) and not upsert):
            return False
        if last == len(cur):
            cur.append(value)
        else:
            cur[last] = value
        return True
    if not isinstance(cur, dict):
        return False
    cur[last] = value
    return True


def _record_version(
    *,
    session_id: str,
    refined_resume_obj: Dict[str, Any] | None,
    suggestion_resume_obj: Dict[str, Any] | None = None,
    source: str = "state",
    turn_id: str = "",
    note: str = "",
) -> Dict[str, Any]:
    safe_refined = refined_resume_obj if isinstance(refined_resume_obj, dict) else {}
    safe_suggestion = suggestion_resume_obj if isinstance(suggestion_resume_obj, dict) else {"items": []}
    return add_session_version(
        session_id=session_id,
        refined_resume_obj=safe_refined,
        suggestion_resume_obj=safe_suggestion,
        source=source,
        turn_id=turn_id,
        note=note,
    )


# ═══════════════════════════════════════════════════════════════════
# Public session API
# ═══════════════════════════════════════════════════════════════════


def start_session(
    *,
    title: str,
    window_size: int,
    raw_resume_obj: Dict[str, Any] | None = None,
    normalized_resume_obj: Dict[str, Any] | None = None,
    refined_resume_obj: Dict[str, Any] | None = None,
    doc_type: str = "resume",
    resume_id: str = "",
) -> Dict[str, Any]:
    session = create_session(
        title=title,
        window_size=window_size,
        raw_resume_obj=raw_resume_obj,
        normalized_resume_obj=normalized_resume_obj,
        refined_resume_obj=refined_resume_obj,
        doc_type=doc_type,
        resume_id=resume_id,
    )
    add_message(
        session_id=str(session.get("id", "")),
        role="system",
        content="Session started.",
    )
    return session


def get_session_content(*, session_id: str, message_limit: int = CHAT_MEMORY_LIMIT, event_limit: int = 200) -> Dict[str, Any]:
    payload = _queries_get_session_content(
        session_id=session_id,
        message_limit=message_limit,
        event_limit=event_limit,
        all_actions_turn_limit=100000,
        all_actions_event_limit_per_turn=1000,
    )
    state = payload.get("state", {}) if isinstance(payload.get("state", {}), dict) else {}
    suggestion_raw = state.get("suggestion_document_obj", {"items": []}) if isinstance(state.get("suggestion_document_obj", {}), dict) else {"items": []}
    normalized = _normalize_suggestion_document_obj(suggestion_raw)
    state["suggestion_document_obj"] = normalized
    payload["state"] = state
    payload["actionability_summary"] = _build_actionability_summary(normalized)
    return payload


def rollback_to_version(*, session_id: str, version_id: str, note: str = "") -> Dict[str, Any]:
    session = get_session(session_id, include_state=True)
    if not session:
        raise ValueError("session not found")
    version = get_session_version(session_id=session_id, version_id=version_id)
    if not version:
        raise ValueError("version not found")
    target_refined = version.get("refined_resume_obj", {}) if isinstance(version.get("refined_resume_obj", {}), dict) else {}
    state = session.get("state", {}) if isinstance(session.get("state", {}), dict) else {}
    save_session_state(
        session_id=session_id,
        raw_resume_obj=_as_dict(state.get("raw_resume_obj")),
        normalized_resume_obj=_as_dict(state.get("normalized_resume_obj")),
        refined_resume_obj=target_refined,
        rag_context_by_path=_as_dict(state.get("rag_context_by_path")),
        suggestion_resume_obj={"items": []},
        review_payload={"items": []},
        quality_report=_as_dict(state.get("quality_report")),
        section_quality_map=_as_dict(state.get("section_quality_map")),
    )
    new_version = _record_version(
        session_id=session_id,
        refined_resume_obj=target_refined,
        suggestion_resume_obj={"items": []},
        source="rollback",
        note=note or f"rollback_to:{version_id}",
    )
    return {
        "session_id": session_id,
        "rolled_back_to_version_id": version_id,
        "new_current_version_id": str(new_version.get("id", "")),
        "refined_document_obj": target_refined,
    }


def get_whole_resume(*, session_id: str) -> Dict[str, Any]:
    session = get_session(session_id, include_state=True)
    if not session:
        raise ValueError("session not found")
    state = session.get("state", {}) if isinstance(session.get("state", {}), dict) else {}
    resume_obj = state.get("refined_resume_obj", {}) if isinstance(state.get("refined_resume_obj", {}), dict) else {}
    if not resume_obj:
        resume_obj = state.get("normalized_resume_obj", {}) if isinstance(state.get("normalized_resume_obj", {}), dict) else {}
    return {
        "session_id": session_id,
        "doc_type": str(session.get("doc_type", "resume")),
        "document_obj": resume_obj,
        "quality_report": state.get("quality_report", {}) if isinstance(state.get("quality_report", {}), dict) else {},
        "section_quality_map": state.get("section_quality_map", {}) if isinstance(state.get("section_quality_map", {}), dict) else {},
    }


# ═══════════════════════════════════════════════════════════════════
# Suggestion normalization
# ═══════════════════════════════════════════════════════════════════


def _safe_json_loads_any(raw: Any) -> Any:
    if isinstance(raw, (dict, list, int, float, bool)) or raw is None:
        return raw
    text = str(raw or "").strip()
    if not text:
        return None
    text = text.replace("﻿", "").replace("“", "\"").replace("”", "\"")
    text = "".join(ch if (ord(ch) >= 32 or ch in "\n\r\t") else " " for ch in text)
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except Exception:
        return None


def _normalize_suggestion_document_obj(suggestion_obj: Dict[str, Any] | None) -> Dict[str, Any]:
    source = suggestion_obj if isinstance(suggestion_obj, dict) else {"items": []}
    items = source.get("items", []) if isinstance(source.get("items", []), list) else []
    normalized_items: List[Dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        actionability = str(raw.get("actionability", "")).strip().lower()
        if actionability not in {"apply_ready", "confirm_required"}:
            actionability = "apply_ready"
        requires_confirmation = bool(raw.get("requires_confirmation", False)) or actionability == "confirm_required"
        normalized_items.append({
            **raw,
            "actionability": actionability,
            "requires_confirmation": requires_confirmation,
            "confirmation_hint": str(raw.get("confirmation_hint", "")).strip(),
        })
    return {"items": normalized_items}


def _build_actionability_summary(suggestion_obj: Dict[str, Any] | None) -> Dict[str, int]:
    suggestion = _normalize_suggestion_document_obj(suggestion_obj)
    items = suggestion.get("items", []) if isinstance(suggestion.get("items", []), list) else []
    apply_ready = 0
    confirm_required = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        tag = str(item.get("actionability", "apply_ready")).strip().lower()
        if tag == "confirm_required":
            confirm_required += 1
        else:
            apply_ready += 1
    return {"total": len(items), "apply_ready": apply_ready, "confirm_required": confirm_required}


# ═══════════════════════════════════════════════════════════════════
# Scope utilities
# ═══════════════════════════════════════════════════════════════════


def _scope_aliases(target_scope: str) -> List[str]:
    scope = str(target_scope or "").strip()
    if not scope:
        return []
    aliases = [scope]
    low = scope.lower()
    if low == "education":
        aliases.extend(["education", "educations", "educationExperience", "edu"])
    elif low in {"workexperience", "experience"}:
        aliases.extend(["workExperience", "experience", "internships"])
    elif low in {"personalprojects", "projects", "project"}:
        aliases.extend(["personalProjects", "projects"])
    elif low == "summary":
        aliases.extend(["summary", "profile"])
    elif low in {"skills", "skill", "additional.technicalskills"}:
        aliases.extend(["additional.technicalSkills", "technicalSkills", "skills"])
    out: List[str] = []
    for item in aliases:
        if item and item not in out:
            out.append(item)
    return out


def _is_in_scope(path: str, target_scope: str) -> bool:
    candidates = _scope_aliases(target_scope)
    if not candidates:
        return True
    p = str(path or "")
    for scope in candidates:
        if p == scope or p.startswith(scope + ".") or p.startswith(scope + "["):
            return True
    return False


def _filter_suggestion_obj_by_scope(suggestion_obj: Dict[str, Any], target_scope: str) -> Dict[str, Any]:
    items = suggestion_obj.get("items", []) if isinstance(suggestion_obj.get("items", []), list) else []
    filtered = [item for item in items if isinstance(item, dict) and _is_in_scope(str(item.get("path", "")), target_scope)]
    return _normalize_suggestion_document_obj({"items": filtered})


def _filter_review_payload_by_scope(review_payload: Dict[str, Any], target_scope: str) -> Dict[str, Any]:
    items = review_payload.get("items", []) if isinstance(review_payload.get("items", []), list) else []
    filtered = [item for item in items if isinstance(item, dict) and _is_in_scope(str(item.get("path", "")), target_scope)]
    return {
        "items": filtered,
        "summary": {
            "total": len(filtered), "pending": len(filtered),
            "accepted": 0, "rejected": 0,
            "scope": str(target_scope or ""),
        },
    }


def _resolve_scope_path(state: Dict[str, Any], target_scope: str) -> str:
    refined = state.get("refined_resume_obj", {}) if isinstance(state.get("refined_resume_obj", {}), dict) else {}
    normalized = state.get("normalized_resume_obj", {}) if isinstance(state.get("normalized_resume_obj", {}), dict) else {}
    raw = state.get("raw_resume_obj", {}) if isinstance(state.get("raw_resume_obj", {}), dict) else {}
    for candidate in _scope_aliases(target_scope):
        if _get_by_path_local(refined, candidate) is not None:
            return candidate
        if _get_by_path_local(normalized, candidate) is not None:
            return candidate
        if _get_by_path_local(raw, candidate) is not None:
            return candidate
    return str(target_scope or "").strip()


# ═══════════════════════════════════════════════════════════════════
# Diff / classification utilities
# ═══════════════════════════════════════════════════════════════════


def _leaf_diffs(before: Any, after: Any, base_path: str) -> List[Dict[str, Any]]:
    diffs: List[Dict[str, Any]] = []
    if isinstance(before, dict) and isinstance(after, dict):
        keys = sorted(set(before.keys()) | set(after.keys()))
        for key in keys:
            child_path = f"{base_path}.{key}" if base_path else str(key)
            diffs.extend(_leaf_diffs(before.get(key), after.get(key), child_path))
        return diffs
    if isinstance(before, list) and isinstance(after, list):
        for idx in range(max(len(before), len(after))):
            b = before[idx] if idx < len(before) else None
            a = after[idx] if idx < len(after) else None
            child_path = f"{base_path}[{idx}]" if base_path else f"[{idx}]"
            diffs.extend(_leaf_diffs(b, a, child_path))
        return diffs
    if before != after:
        diffs.append({
            "path": base_path,
            "current_value": _to_text(before),
            "suggested_value": _to_text(after),
            "current_value_raw": before,
            "suggested_value_raw": after,
        })
    return diffs


def _same_container_type(left: Any, right: Any) -> bool:
    if isinstance(left, dict):
        return isinstance(right, dict)
    if isinstance(left, list):
        return isinstance(right, list)
    return not isinstance(right, (dict, list))


def _coerce_scoped_shape(value: Any, expected_container: Any, resolved_scope: str) -> Any:
    if _same_container_type(expected_container, value):
        return value
    expected_is_scalar = not isinstance(expected_container, (dict, list))
    if expected_is_scalar and isinstance(value, list) and len(value) == 1:
        one = value[0]
        if not isinstance(one, (dict, list)):
            return one
    if not isinstance(value, dict):
        return value
    scope_leaf = str(resolved_scope or "").split(".")[-1].split("[", 1)[0]
    candidate_keys = [scope_leaf, "refined_section", "section_json", "value", "items"]
    for key in candidate_keys:
        candidate = value.get(key)
        if _same_container_type(expected_container, candidate):
            return candidate
        if expected_is_scalar and isinstance(candidate, list) and len(candidate) == 1:
            one = candidate[0]
            if not isinstance(one, (dict, list)):
                return one
    if len(value) == 1:
        only_value = next(iter(value.values()))
        if _same_container_type(expected_container, only_value):
            return only_value
        if expected_is_scalar and isinstance(only_value, list) and len(only_value) == 1:
            one = only_value[0]
            if not isinstance(one, (dict, list)):
                return one
    return value


def _values_equal(left: Any, right: Any) -> bool:
    return left == right


def _extract_numeric_tokens(value: Any) -> List[str]:
    import re
    text = _to_text(value)
    if not text:
        return []
    return re.findall(r"\d+(?:\.\d+)?%?", text)


def _is_core_fact_change(path: str, current_value: Any, suggested_value: Any) -> bool:
    lower_path = str(path or "").lower()
    core_tokens = {
        "name", "phone", "email", "location", "website", "linkedin", "github",
        "company", "institution", "degree", "years", "date", "gpa",
        "award", "awards", "certification", "certifications",
        "language", "languages", "id", "salary",
    }
    if any(token in lower_path for token in core_tokens):
        return True
    left_nums = _extract_numeric_tokens(current_value)
    right_nums = _extract_numeric_tokens(suggested_value)
    return left_nums != right_nums


def _classify_suggestion_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    classified: List[Dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        path = str(raw.get("path", "")).strip()
        current_value = raw.get("current_value_raw", raw.get("current_value", ""))
        suggested_value = raw.get("suggested_value_raw", raw.get("suggested_value", ""))
        requires_confirmation = _is_core_fact_change(path, current_value, suggested_value)
        actionability = "confirm_required" if requires_confirmation else "apply_ready"
        item = {
            **raw,
            "actionability": actionability,
            "requires_confirmation": requires_confirmation,
            "confirmation_hint": (
                str(raw.get("confirmation_hint", "")).strip()
                or ("核心事实修改，请确认后再应用。" if requires_confirmation else "")
            ),
        }
        classified.append(item)
    return classified


def _extract_refined_value(parsed: Any, expected_example: Any) -> Any:
    expected_is_dict = isinstance(expected_example, dict)
    expected_is_list = isinstance(expected_example, list)
    expected_is_scalar = not expected_is_dict and not expected_is_list
    if expected_is_scalar:
        if isinstance(parsed, dict) and "value" in parsed:
            candidate = parsed.get("value")
            if not isinstance(candidate, dict):
                return candidate  # Accept string OR list
        if not isinstance(parsed, dict):
            return parsed  # Accept string OR list
        raise ValueError("refine_output_contract_error: scalar scope must return JSON object with scalar `value`")
    if isinstance(parsed, dict) and "value" in parsed:
        parsed = parsed.get("value")
    if expected_is_dict and isinstance(parsed, dict):
        return parsed
    if expected_is_list:
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, str):
            return parsed  # Accept string when list was expected
    raise ValueError(f"refine_output_contract_error: expected {type(expected_example).__name__}, got {type(parsed).__name__}")


# ═══════════════════════════════════════════════════════════════════
# Review payload formatting (moved from pipeline)
# ═══════════════════════════════════════════════════════════════════


def _json_prepare_review_payload(
    refined_resume_obj: Dict[str, Any],
    suggestion_resume_obj: Dict[str, Any],
) -> Dict[str, Any]:
    items = _as_list(_as_dict(suggestion_resume_obj).get("items", []))
    payload_items: List[Dict[str, Any]] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        payload_items.append({
            "id": idx + 1,
            "section": str(item.get("section", "")),
            "path": str(item.get("path", "")),
            "current_value": str(item.get("current_value", "")),
            "suggested_value": str(item.get("suggested_value", "")),
            "reason": str(item.get("reason", "")),
            "status": "pending",
        })
    return {
        "review_payload": {
            "items": payload_items,
            "summary": {
                "total": len(payload_items),
                "pending": len(payload_items),
                "accepted": 0,
                "rejected": 0,
            },
        },
        "refined_resume_obj": refined_resume_obj,
    }


# ═══════════════════════════════════════════════════════════════════
# Scoped refine / suggest (v3 agent tools)
# ═══════════════════════════════════════════════════════════════════


def partial_refine_content(
    *,
    session_id: str,
    target_scope: str,
    user_feedback: str,
    section_json: Any = None,
    suggestion_document_obj: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    session = get_session(session_id, include_state=True)
    if not session:
        raise ValueError("session not found")

    state = session.get("state", {}) if isinstance(session.get("state", {}), dict) else {}
    resolved_scope = _resolve_scope_path(state, target_scope)
    if not resolved_scope:
        raise ValueError("target_scope is required")

    refined_resume_obj = state.get("refined_resume_obj", {}) if isinstance(state.get("refined_resume_obj", {}), dict) else {}
    if not refined_resume_obj:
        refined_resume_obj = state.get("normalized_resume_obj", {}) if isinstance(state.get("normalized_resume_obj", {}), dict) else {}

    baseline_section = _get_by_path_local(refined_resume_obj, resolved_scope)
    if baseline_section is None:
        baseline_section = _get_by_path_local(
            state.get("normalized_resume_obj", {}) if isinstance(state.get("normalized_resume_obj", {}), dict) else {},
            resolved_scope,
        )
    if baseline_section is None:
        baseline_section = _get_by_path_local(
            state.get("raw_resume_obj", {}) if isinstance(state.get("raw_resume_obj", {}), dict) else {},
            resolved_scope,
        )

    current_section = baseline_section
    if section_json is not None:
        if baseline_section is not None:
            coerced = _coerce_scoped_shape(section_json, baseline_section, resolved_scope)
            if _same_container_type(baseline_section, coerced):
                current_section = coerced
        else:
            current_section = section_json
    if current_section is None:
        raise ValueError("scoped section not found")

    suggestion_input = (
        suggestion_document_obj
        if isinstance(suggestion_document_obj, dict)
        else (
            state.get("suggestion_resume_obj", {})
            if isinstance(state.get("suggestion_resume_obj", {}), dict)
            else {"items": []}
        )
    )
    scoped_items = _filter_suggestion_obj_by_scope(suggestion_input, resolved_scope).get("items", [])
    scoped_items = [item for item in scoped_items if isinstance(item, dict)]
    if scoped_items:
        classified_items = _classify_suggestion_items(scoped_items)
        apply_items = [item for item in classified_items if str(item.get("actionability", "")) == "apply_ready"]
        fact_items = [item for item in classified_items if str(item.get("actionability", "")) == "confirm_required"]

        next_refined = deepcopy(refined_resume_obj)
        apply_suggestion_obj = _normalize_suggestion_document_obj({"items": apply_items})
        review_payload_result = _json_prepare_review_payload(
            refined_resume_obj=next_refined,
            suggestion_resume_obj=apply_suggestion_obj,
        )
        review_payload = (
            review_payload_result.get("review_payload", {})
            if isinstance(review_payload_result.get("review_payload", {}), dict)
            else {"items": []}
        )
        review_payload = _filter_review_payload_by_scope(review_payload, resolved_scope)

        save_session_state(
            session_id=session_id,
            refined_resume_obj=next_refined,
            suggestion_resume_obj=apply_suggestion_obj,
            review_payload=review_payload,
        )
        updated_section = _get_by_path_local(next_refined, resolved_scope)
        fact_issues = [
            {
                "path": str(item.get("path", "")).strip(),
                "reason": str(item.get("reason", "")).strip() or "涉及核心事实修改，请人工确认。",
                "confirmation_hint": str(item.get("confirmation_hint", "")).strip() or "请提供准确事实后再修改。",
            }
            for item in fact_items
            if isinstance(item, dict)
        ]
        return {
            "session_id": session_id,
            "target_scope": str(target_scope or ""),
            "resolved_scope": resolved_scope,
            "section_json": updated_section,
            "section_before": current_section,
            "parse_mode": "classified_apply",
            "refine_changed": False,
            "retry_used": False,
            "retry_changed": False,
            "llm_raw_preview": "",
            "refined_document_obj": next_refined,
            "auto_applied_changes": [],
            "auto_applied_count": 0,
            "suggestion_document_obj": apply_suggestion_obj,
            "review_payload": review_payload,
            "fact_issues": fact_issues,
        }

    from litellm import completion
    from src.services.build_llm import build_llm

    llm = build_llm()
    expected_type = "dict" if isinstance(current_section, dict) else "list" if isinstance(current_section, list) else "scalar"
    prompt = build_scoped_refine_system_prompt(expected_type=expected_type)
    user_prompt = {
        "target_scope": resolved_scope,
        "user_feedback": str(user_feedback or "").strip(),
        "section_json": current_section,
    }

    def _run_refine_once(system_prompt: str, payload: Dict[str, Any], expected_type: str) -> tuple:
        req = {
            "model": llm.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "api_key": llm.api_key or None,
            "api_base": llm.api_base or None,
            "temperature": 0.1,
            "max_tokens": 420 if expected_type == "scalar" else 4096,
            "timeout": 120,
        }
        try:
            resp = completion(**req, response_format={"type": "json_object"})
        except Exception:
            resp = completion(**req)
        raw = getattr(resp.choices[0].message, "content", "")
        return _safe_json_loads_any(raw), str(raw or "")

    parsed_output, raw_content = _run_refine_once(prompt, user_prompt, expected_type)
    parse_mode = "parsed"
    if parsed_output is None:
        parse_mode = "parse_failed"

    retry_used = False
    retry_changed = False
    if parsed_output is None:
        raise ValueError(f"partial_refine_content parse_failed: {str(raw_content or '')[:400]}")
    try:
        refined_section = _extract_refined_value(parsed_output, current_section)
    except Exception as exc:
        parse_mode = "contract_mismatch"
        raise ValueError(f"partial_refine_content {exc}")

    refine_changed = not _values_equal(current_section, refined_section)

    next_refined = deepcopy(refined_resume_obj)
    if not _set_by_path_local(next_refined, resolved_scope, refined_section):
        raise ValueError("failed to set scoped refined section")

    save_session_state(session_id=session_id, refined_resume_obj=next_refined)

    return {
        "session_id": session_id,
        "target_scope": str(target_scope or ""),
        "resolved_scope": resolved_scope,
        "section_json": refined_section,
        "section_before": current_section,
        "parse_mode": parse_mode,
        "refine_changed": refine_changed,
        "retry_used": retry_used,
        "retry_changed": retry_changed,
        "llm_raw_preview": str(raw_content or "")[:600],
        "refined_document_obj": next_refined,
    }


def partial_generate_suggest(
    *,
    session_id: str,
    target_scope: str,
    section_json: Any = None,
    user_feedback: str = "",
    intent_class: str = "",
) -> Dict[str, Any]:
    """Task planner: diagnose issues in a resume section, output discrete RefinementTasks.

    Does NOT generate refined content — only identifies problems and writes instructions.
    """
    session = get_session(session_id, include_state=True)
    if not session:
        raise ValueError("session not found")

    state = session.get("state", {}) if isinstance(session.get("state", {}), dict) else {}
    resolved_scope = _resolve_scope_path(state, target_scope)
    if not resolved_scope:
        raise ValueError("target_scope is required")

    refined_resume_obj = (
        state.get("refined_resume_obj", {}) or state.get("refined_document_obj", {})
    )
    if not isinstance(refined_resume_obj, dict):
        refined_resume_obj = {}
    current_section = section_json if section_json is not None else _get_by_path_local(refined_resume_obj, resolved_scope)
    if current_section is None:
        raise ValueError("scoped section not found")

    from litellm import completion
    from src.services.build_llm import build_llm
    from src.services.content_refinement_v3.prompts.agent import build_task_planner_system_prompt

    llm = build_llm()
    prompt = build_task_planner_system_prompt(intent_class=intent_class)
    user_prompt = {
        "target_scope": resolved_scope,
        "user_feedback": str(user_feedback or "").strip() or "分析此部分内容，找出所有可改进之处。",
        "section_json": current_section,
    }

    req = {
        "model": llm.model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
        ],
        "api_key": llm.api_key or None,
        "api_base": llm.api_base or None,
        "temperature": 0.15,
        "max_tokens": 4096,
        "timeout": 120,
    }
    raw_content = ""
    raw_tasks: list[dict[str, Any]] = []
    suggest_error = ""
    finish_reason = ""
    try:
        resp = completion(**req, response_format={"type": "json_object"})
        raw_content = getattr(resp.choices[0].message, "content", "")
        finish_reason = str(getattr(resp.choices[0], "finish_reason", "unknown"))
        if not raw_content or not str(raw_content).strip():
            logger.warning("[suggest] json_object call returned empty (finish=%s), retrying without json_object", finish_reason)
            resp = completion(**req)
            raw_content = getattr(resp.choices[0].message, "content", "")
            finish_reason = str(getattr(resp.choices[0], "finish_reason", "unknown"))
        parsed = _safe_json_loads_any(raw_content)
        if isinstance(parsed, dict):
            raw_tasks = parsed.get("tasks", []) if isinstance(parsed.get("tasks", []), list) else []
    except Exception as _outer_exc:
        logger.warning("[suggest] LLM call failed: %s | model=%s", _outer_exc, req.get("model", "?"))
        suggest_error = str(_outer_exc)[:200]
        finish_reason = "exception"

    # Validate, normalize, and deduplicate tasks
    seen_paths: set[str] = set()
    tasks: list[dict[str, Any]] = []
    for i, t in enumerate(raw_tasks):
        if not isinstance(t, dict):
            continue
        path = str(t.get("path", "")).strip()
        if not path:
            continue
        # Normalize path: LLM often outputs relative paths
        # Cases: "phone" → "personalInfo.phone", "[0].gpa" → "education[0].gpa"
        if not path.startswith(resolved_scope + ".") and not path.startswith(resolved_scope + "["):
            # Try prepending scope with dot
            candidate_dot = f"{resolved_scope}.{path}"
            if _get_by_path_local(refined_resume_obj, candidate_dot) is not None:
                path = candidate_dot
            else:
                # Try prepending scope directly (for [N].field paths)
                candidate_direct = f"{resolved_scope}{path}"
                if _get_by_path_local(refined_resume_obj, candidate_direct) is not None:
                    path = candidate_direct
        # Validate path resolves. Prefer absolute path in full resume; if only
        # found in current_section, expand to absolute form for the executor.
        if _get_by_path_local(refined_resume_obj, path) is None:
            if _get_by_path_local(current_section, path) is not None:
                # Path is relative to the section — expand to absolute
                expanded = f"{resolved_scope}.{path}" if not path.startswith(resolved_scope) else path
                if _get_by_path_local(refined_resume_obj, expanded) is not None:
                    path = expanded
                elif not path.startswith(resolved_scope):
                    expanded2 = f"{resolved_scope}{path}"
                    if _get_by_path_local(refined_resume_obj, expanded2) is not None:
                        path = expanded2
                    else:
                        continue
                else:
                    continue
            else:
                continue
        # Deduplicate by path (keep highest priority)
        if path in seen_paths:
            continue
        seen_paths.add(path)
        tasks.append({
            "task_id": f"task_{i}",
            "scope": resolved_scope.split(".", 1)[0].split("[", 1)[0],
            "path": path,
            "problem_description": str(t.get("problem_description", "")).strip()[:80],
            "instruction": str(t.get("instruction", "")).strip()[:200] or str(t.get("problem_description", "")).strip()[:200],
            "priority": int(t.get("priority", 0)) if isinstance(t.get("priority", 0), (int, float)) else 0,
            "intent_class": intent_class,
        })

    return {
        "session_id": session_id,
        "target_scope": str(target_scope or ""),
        "resolved_scope": resolved_scope,
        "tasks": tasks,
        "section_json": current_section,
        "llm_raw_preview": str(raw_content or "")[:600],
        "finish_reason": finish_reason,
        "diagnostics": {
            "tasks_count": len(tasks),
        },
        "suggest_error": suggest_error,
    }


def partial_direct_edit(
    *,
    session_id: str,
    target_scope: str,
    section_json: Any = None,
    user_feedback: str = "",
    intent_class: str = "",
) -> Dict[str, Any]:
    """Combined suggest+refine: analyze section and directly output refined suggestion items.

    Replaces the two-step partial_generate_suggest + partial_execute_task pipeline with
    a single LLM call that outputs both current_value and refined_value for each field.
    """
    session = get_session(session_id, include_state=True)
    if not session:
        raise ValueError("session not found")

    state = session.get("state", {}) if isinstance(session.get("state", {}), dict) else {}
    resolved_scope = _resolve_scope_path(state, target_scope)
    if not resolved_scope:
        raise ValueError("target_scope is required")

    refined_resume_obj = (
        state.get("refined_resume_obj", {}) or state.get("refined_document_obj", {})
    )
    if not isinstance(refined_resume_obj, dict):
        refined_resume_obj = {}
    current_section = section_json if section_json is not None else _get_by_path_local(refined_resume_obj, resolved_scope)
    is_new_section = current_section is None
    if is_new_section:
        current_section = {}

    from litellm import completion
    from src.services.build_llm import build_llm
    from src.services.content_refinement_v3.prompts.agent import build_direct_edit_system_prompt

    llm = build_llm()
    prompt = build_direct_edit_system_prompt(intent_class=intent_class)
    user_prompt = {
        "target_scope": resolved_scope,
        "user_feedback": str(user_feedback or "").strip() or "Improve this section.",
        "section_json": current_section,
        "intent_class": intent_class,
    }
    if is_new_section:
        user_prompt["_hint"] = (
            "This section does NOT exist in the resume yet. You need to CREATE it from scratch. "
            "Output items with paths like '<scope>[0].name', '<scope>[0].description' etc. "
            "current_value should be empty string '' since the field doesn't exist."
        )

    req = {
        "model": llm.model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
        ],
        "api_key": llm.api_key or None,
        "api_base": llm.api_base or None,
        "temperature": 0.2,
        "max_tokens": 8192 if is_new_section else 4096,
        "timeout": 120,
    }

    raw_content = ""
    raw_items: list[dict[str, Any]] = []
    direct_assistant_message = ""
    finish_reason = ""
    direct_error = ""
    try:
        resp = completion(**req, response_format={"type": "json_object"})
        raw_content = getattr(resp.choices[0].message, "content", "")
        finish_reason = str(getattr(resp.choices[0], "finish_reason", "unknown"))
        if not raw_content or not str(raw_content).strip():
            resp = completion(**req)
            raw_content = getattr(resp.choices[0].message, "content", "")
            finish_reason = str(getattr(resp.choices[0], "finish_reason", "unknown"))
        parsed = _safe_json_loads_any(raw_content)
        if isinstance(parsed, dict):
            raw_items = parsed.get("items", []) if isinstance(parsed.get("items", []), list) else []
            direct_assistant_message = str(parsed.get("assistant_message", "")).strip()
    except Exception as exc:
        logger.warning("[direct_edit] LLM call failed: %s | model=%s", exc, req.get("model", "?"))
        direct_error = str(exc)[:200]

    # Convert raw LLM items to suggestion items (same format as _tasks_to_suggestion_items output)
    items: list[dict[str, Any]] = []
    for i, ri in enumerate(raw_items):
        if not isinstance(ri, dict):
            continue
        path = str(ri.get("path", "")).strip()
        if not path:
            continue
        # Normalize path (same logic as partial_generate_suggest)
        if not path.startswith(resolved_scope + ".") and not path.startswith(resolved_scope + "["):
            candidate = f"{resolved_scope}.{path}"
            if _get_by_path_local(refined_resume_obj, candidate) is not None:
                path = candidate
            else:
                candidate = f"{resolved_scope}{path}"
                if _get_by_path_local(refined_resume_obj, candidate) is not None:
                    path = candidate
                else:
                    pass  # Use the path as-is; it may be relative to section_json

        current_value = _get_by_path_local(refined_resume_obj, path)
        if current_value is None:
            current_value = ri.get("current_value", "")

        refined_value = ri.get("refined_value") if ri.get("refined_value") is not None else current_value
        reason = str(ri.get("reason", "")).strip()[:60]
        actionability = str(ri.get("actionability", "apply_ready")).strip().lower()
        if actionability not in {"apply_ready", "confirm_required"}:
            actionability = "apply_ready"

        scope = resolved_scope.split(".", 1)[0].split("[", 1)[0]
        items.append({
            "section": scope,
            "path": path,
            "current_value": _to_readable_text(current_value) or _to_text(current_value),
            "suggested_value": _to_readable_text(refined_value) or _to_text(refined_value),
            "current_value_raw": current_value,
            "suggested_value_raw": refined_value,
            "reason": reason,
            "refined_text": _to_readable_text(refined_value) or _to_text(refined_value),
            "refined_value_raw": refined_value,
            "suggestion": "",
            "option_id": "suggested",
            "option_label": "Suggested",
            "actionability": actionability,
            "requires_confirmation": actionability == "confirm_required",
            "confirmation_hint": "涉及事实/数据变更，请确认后再应用。" if actionability == "confirm_required" else "",
            "task_id": f"de_{i}",
        })

    return {
        "session_id": session_id,
        "target_scope": str(target_scope or ""),
        "resolved_scope": resolved_scope,
        "items": items,
        "section_json": current_section,
        "llm_raw_preview": str(raw_content or "")[:600],
        "finish_reason": finish_reason,
        "direct_error": direct_error,
        "assistant_message": direct_assistant_message,
        "diagnostics": {"items_count": len(items)},
    }


def partial_execute_task(
    *,
    session_id: str,
    task: dict[str, Any],
    state: dict[str, Any],
    user_feedback: str = "",
) -> dict[str, Any]:
    """Execute a single RefinementTask: call LLM with focused instruction on one field."""
    from litellm import completion
    from src.services.build_llm import build_llm
    from src.services.content_refinement_v3.prompts.agent import build_task_executor_system_prompt

    path = str(task.get("path", ""))
    instruction = str(task.get("instruction", ""))
    task_id = str(task.get("task_id", "unknown"))

    # Resolve the resume object from state — session stores it as refined_document_obj or refined_resume_obj
    refined_resume_obj = (
        state.get("refined_resume_obj", {}) or state.get("refined_document_obj", {})
    )
    if not isinstance(refined_resume_obj, dict):
        refined_resume_obj = {}
    current_value = _get_by_path_local(refined_resume_obj, path)

    if current_value is None:
        return {
            "task_id": task_id,
            "path": path,
            "success": False,
            "error": f"Path not found in resume: {path}",
            "current_value": None,
            "refined_value": None,
            "reason": "",
        }

    expected_type = "dict" if isinstance(current_value, dict) else "list" if isinstance(current_value, list) else "scalar"

    llm = build_llm()
    prompt = build_task_executor_system_prompt(expected_type=expected_type)
    user_prompt = {
        "task_instruction": instruction,
        "user_request": str(user_feedback or "").strip()[:300],
        "current_value": current_value,
    }

    req = {
        "model": llm.model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
        ],
        "api_key": llm.api_key or None,
        "api_base": llm.api_base or None,
        "temperature": 0.2,
        "max_tokens": 420 if expected_type == "scalar" else 4096,
        "timeout": 120,
    }
    try:
        resp = completion(**req, response_format={"type": "json_object"})
        raw_content = getattr(resp.choices[0].message, "content", "")
        if not raw_content or not str(raw_content).strip():
            resp = completion(**req)
            raw_content = getattr(resp.choices[0].message, "content", "")
    except Exception:
        resp = completion(**req)
        raw_content = getattr(resp.choices[0].message, "content", "")
    try:
        parsed = _safe_json_loads_any(raw_content)
        if isinstance(parsed, dict):
            refined_value = parsed.get("value")
            reason = str(parsed.get("reason", "")).strip()
            return {
                "task_id": task_id,
                "path": path,
                "success": True,
                "current_value": current_value,
                "refined_value": refined_value if refined_value is not None else current_value,
                "reason": reason or instruction[:60],
                "raw_content": raw_content[:600],
            }
    except Exception:
        pass

    return {
        "task_id": task_id,
        "path": path,
        "success": False,
        "error": "LLM call failed",
        "current_value": current_value,
        "refined_value": None,
        "reason": "",
    }


def _tasks_to_suggestion_items(
    tasks: list[dict[str, Any]],
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    """Bridge: convert completed RefinementTasks into suggestion_document_obj items."""
    refined_resume_obj = (
        state.get("refined_resume_obj", {}) or state.get("refined_document_obj", {})
    )
    if not isinstance(refined_resume_obj, dict):
        refined_resume_obj = {}
    items: list[dict[str, Any]] = []
    for task in tasks:
        if task.get("status") != "completed":
            continue
        path = str(task.get("path", ""))
        scope = str(task.get("scope", ""))
        current_value = _get_by_path_local(refined_resume_obj, path)
        refined_value = task.get("result")
        reason = str(task.get("reason", "")).strip() or str(task.get("instruction", ""))[:60]
        items.append({
            "section": scope,
            "path": path,
            "current_value": _to_readable_text(current_value) or _to_text(current_value),
            "suggested_value": _to_readable_text(refined_value) or _to_text(refined_value),
            "current_value_raw": current_value,
            "suggested_value_raw": refined_value,
            "reason": reason,
            "refined_text": _to_readable_text(refined_value) or _to_text(refined_value),
            "refined_value_raw": refined_value,
            "suggestion": "",
            "option_id": "suggested",
            "option_label": "Suggested（待判定）",
            "actionability": "apply_ready",
            "requires_confirmation": False,
            "confirmation_hint": "",
            "task_id": task.get("task_id", ""),
        })
    return items
