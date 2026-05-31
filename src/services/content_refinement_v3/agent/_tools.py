"""Agent tools — registered via @tool decorator.

Each tool = function + JSON Schema. Decorator auto-collects schemas.
Add a new tool by writing a function with the @tool decorator — no other files
need to change (the registry picks up decorated tools automatically).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from ._types import ToolResult


# ── Decorator + auto-registration ───────────────────────────────────────────

@dataclass
class _ToolEntry:
    fn: Callable[..., ToolResult]
    schema: dict  # OpenAI-compatible tool schema
    parallel_safe: bool = False  # True = can run concurrently with other safe tools


_TOOLS: dict[str, _ToolEntry] = {}


def tool(name: str, description: str, parameters: dict | None = None,
         parallel_safe: bool = False):
    """Decorator: register a function as an LLM-callable tool.

    Args:
        name: Tool name exposed to the LLM.
        description: What the tool does.
        parameters: JSON Schema for arguments (auto-generated if None).
        parallel_safe: If True, this tool can execute concurrently with other
            parallel-safe tools in the same LLM round.
    """
    def decorator(fn: Callable[..., ToolResult]):
        schema = {
            "name": name,
            "description": description,
            "parameters": parameters or {"type": "object", "properties": {}, "required": []},
        }
        _TOOLS[name] = _ToolEntry(fn=fn, schema=schema, parallel_safe=parallel_safe)
        return fn
    return decorator


def registered_tools() -> dict[str, _ToolEntry]:
    """Return all decorated tools with their schemas."""
    return dict(_TOOLS)


def schema_list() -> list[dict]:
    """OpenAI-compatible tool schemas for the LLM `tools` parameter."""
    return [{"type": "function", "function": e.schema} for e in _TOOLS.values()]


def _compact_ws(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _jd_card_summary(text: str, metadata: dict[str, Any] | None = None, max_len: int = 260) -> str:
    metadata = metadata or {}
    head = " | ".join(
        part for part in [
            _compact_ws(metadata.get("title")),
            _compact_ws(metadata.get("company")),
            _compact_ws(metadata.get("role_direction")),
            _compact_ws(metadata.get("recruitment_type") or metadata.get("type")),
            _compact_ws(metadata.get("year")),
        ] if part
    )
    lines = [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]
    body = _compact_ws(" ".join(lines[:4]))
    summary = _compact_ws(f"{head}. {body}" if head else body)
    if len(summary) > max_len:
        summary = summary[: max_len - 1].rstrip() + "..."
    return summary


def _save_target_jd_to_session(*, session_id: str, jd_text: str, jd_id: str = "",
                               metadata: dict[str, Any] | None = None,
                               card_summary: str = "") -> None:
    from ..session.service import get_session_content, save_session_state

    snapshot = get_session_content(session_id=session_id, message_limit=1, event_limit=1)
    state = snapshot.get("state", {}) if isinstance(snapshot.get("state", {}), dict) else {}
    rag_context = state.get("rag_context_by_path", {}) if isinstance(state.get("rag_context_by_path", {}), dict) else {}
    text = str(jd_text or "").strip()
    target = {
        "id": str(jd_id or "").strip(),
        "text": text,
        "full_text": text,
        "metadata": metadata if isinstance(metadata, dict) else {},
        "card_summary": card_summary or _jd_card_summary(text, metadata),
    }
    rag_context["target_jd"] = target
    save_session_state(session_id=session_id, rag_context_by_path=rag_context)


# ── Utility ────────────────────────────────────────────────────────────────


def _delete_by_path_inline(obj: Any, path: str) -> bool:
    """Delete a key from a dict or element from a list at the given path."""
    import re as _re
    tokens = []
    for part in str(path or "").split("."):
        if not part:
            continue
        m = _re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)", part)
        if m:
            tokens.append(m.group(1))
        for idx in _re.findall(r"\[(\d+)\]", part):
            tokens.append(int(idx))
    if not tokens or not isinstance(obj, dict):
        return False
    cur = obj
    for token in tokens[:-1]:
        if isinstance(token, str):
            if not isinstance(cur, dict) or token not in cur:
                return False
            cur = cur[token]
        elif isinstance(token, int):
            if not isinstance(cur, list) or token >= len(cur) or token < 0:
                return False
            cur = cur[token]
        else:
            return False
    last = tokens[-1]
    if isinstance(last, str):
        if not isinstance(cur, dict) or last not in cur:
            return False
        del cur[last]
        return True
    if isinstance(last, int):
        if not isinstance(cur, list) or last >= len(cur) or last < 0:
            return False
        del cur[last]
        return True
    return False


# ── Tool implementations ────────────────────────────────────────────────────
# Each tool uses **kwargs to absorb extra arguments (e.g., session_id)
# passed by the ToolRegistry.


@tool("read_resume", "Read the full resume JSON. Use this when you need to see the current state of the resume before editing.", parallel_safe=True)
def tool_read_resume(*, session_id: str, **kwargs: Any) -> ToolResult:
    from ..session.service import get_session_content
    try:
        snapshot = get_session_content(session_id=session_id, message_limit=1, event_limit=1)
        state = snapshot.get("state", {}) if isinstance(snapshot.get("state", {}), dict) else {}
        resume = (
            state.get("refined_document_obj", {}) if isinstance(state.get("refined_document_obj", {}), dict)
            else state.get("refined_resume_obj", {}) if isinstance(state.get("refined_resume_obj", {}), dict)
            else {}
        )
        is_empty = not any(
            resume.get(k) and (isinstance(resume[k], list) and len(resume[k]) > 0 or isinstance(resume[k], str) and resume[k].strip())
            for k in ["workExperience", "education", "personalProjects", "research", "summary"]
        )
        return ToolResult(success=True, tool_name="read_resume",
                          data={"resume": resume, "is_empty": is_empty},
                          meta={"section_count": len(resume)})
    except Exception as exc:
        return ToolResult(success=False, tool_name="read_resume", data={}, error=str(exc))


@tool("read_history",
      "Read recent chat history for this session. Use when you need context from previous turns.",
      {"type": "object", "properties": {"limit": {"type": "integer", "description": "Number of recent messages, default 10"}}, "required": []},
      parallel_safe=True)
def tool_read_history(*, session_id: str, limit: int = 10, **kwargs: Any) -> ToolResult:
    from ..session.service import get_session_content
    try:
        snapshot = get_session_content(session_id=session_id, message_limit=limit, event_limit=50)
        messages = snapshot.get("messages", []) if isinstance(snapshot.get("messages", []), list) else []
        history = []
        for m in messages:
            if isinstance(m, dict) and m.get("content"):
                history.append({
                    "role": str(m.get("role", "user"))[:20],
                    "content": str(m["content"])[:500],
                })
        return ToolResult(success=True, tool_name="read_history",
                          data={"history": history},
                          meta={"message_count": len(history)})
    except Exception as exc:
        return ToolResult(success=False, tool_name="read_history", data={}, error=str(exc))


@tool("search_jd",
      "Search the company recruitment JD library with optional metadata filters. This is NOT web search — it searches a fixed database. Do NOT call for general knowledge questions.",
      {"type": "object", "properties": {
          "query": {"type": "string", "description": "Role keywords e.g. '后端 Python Go'. Use broad terms first, narrow down if too many results."},
          "top_k": {"type": "integer", "description": "How many to return. 5 for targeted, 15-20 for resume comparison. Default 10."},
          "recruitment_type": {"type": "string", "description": "Filter: 'campus' (校招), 'experienced' (社招), 'intern' (实习). Infer from user intent."},
          "company": {"type": "string", "description": "Filter by company name. Infer from user mentioning specific companies."},
          "role_direction": {"type": "string", "description": "Filter: 'backend', 'frontend', 'algorithm', 'product', 'data', 'embedded', etc."},
          "year": {"type": "string", "description": "Recruitment year e.g. '2026'. Only if user specifies."},
      }, "required": []})
def tool_search_jd(*, query: str = "", top_k: int = 10,
                    recruitment_type: str = "", company: str = "",
                    role_direction: str = "", year: str = "", **kwargs: Any) -> ToolResult:
    try:
        from ...rag.jd_repository import JdRepository
        repo = JdRepository()
        k = max(1, min(top_k, 50))
        filters = {}
        for key, val in [("recruitment_type", recruitment_type), ("company", company),
                          ("role_direction", role_direction), ("year", year)]:
            if val and val.strip():
                filters[key] = val.strip().lower()
        results = repo.query(target_role=query or "后端 前端 算法 产品 数据", top_k=k, filters=filters or None)
        if not results:
            return ToolResult(success=True, tool_name="search_jd",
                              data={"matches": [], "hint": "JD library is empty."})
        matches = []
        for r in results:
            metadata = r.get("metadata", {}) if isinstance(r.get("metadata", {}), dict) else {}
            full_text = str(r.get("text", ""))
            matches.append({
                "id": str(r.get("id", "")),
                "text": full_text,
                "full_text": full_text,
                "card_summary": _jd_card_summary(full_text, metadata),
                "metadata": metadata,
                "distance": r.get("distance"),
            })
        return ToolResult(success=True, tool_name="search_jd",
                          data={"matches": matches, "total": len(matches)})
    except Exception as exc:
        return ToolResult(success=False, tool_name="search_jd", data={}, error=str(exc))


@tool("edit_field",
      "Modify a single field in the resume. You can target a leaf field or an entire object entry.",
      {"type": "object", "properties": {
          "path": {"type": "string", "description": "Dot-path with optional array indices. Leaf: 'summary', 'workExperience[0].description[2]'. Object: 'workExperience[0]', 'personalProjects[0]' — when targeting an object, value MUST be a JSON object string with ALL fields of that entry."},
          "value": {"type": "string", "description": "New value. For OBJECT paths (ending with [N]): value='{\"title\":\"SDE\",\"company\":\"Google\",\"years\":\"2020-2024\",\"description\":[\"line1\",\"line2\"]}'. For LEAF paths: plain text. NEVER use pipe-delimited format (|)."},
          "current_value": {"type": "string", "description": "Original value. Omit for upsert."},
          "op": {"type": "string", "enum": ["update", "upsert", "delete"], "description": "update: replace existing. upsert: add new entry or create if missing. delete: remove."},
          "reason": {"type": "string", "description": "Brief reason in Chinese, under 30 chars."},
          "actionability": {"type": "string", "enum": ["apply_ready", "confirm_required"], "description": "confirm_required only for fact-sensitive fields."},
          "confidence": {"type": "number", "description": "Confidence 0.0-1.0."},
      }, "required": ["path", "value"]})
def tool_edit_field(*, session_id: str, path: str, value: Any,
                    op: str = "update", reason: str = "",
                    actionability: str = "apply_ready",
                    confidence: float = 0.8,
                    current_value: str = "", **kwargs: Any) -> ToolResult:
    from ..session.service import get_session_content, _set_by_path_local, _get_by_path_local, save_session_state as _save
    try:
        snapshot = get_session_content(session_id=session_id, message_limit=1, event_limit=1)
        state = snapshot.get("state", {}) if isinstance(snapshot.get("state", {}), dict) else {}
        resume = (
            state.get("refined_document_obj", {}) if isinstance(state.get("refined_document_obj", {}), dict)
            else state.get("refined_resume_obj", {}) if isinstance(state.get("refined_resume_obj", {}), dict)
            else {}
        )
        if not resume:
            return ToolResult(success=False, tool_name="edit_field", data={}, error="No resume loaded — call read_resume first")

        # Auto-parse JSON string values so arrays/objects are stored as native types
        resolved_value = value
        if isinstance(value, str) and value.strip():
            stripped = value.strip()
            if (stripped.startswith("{") and stripped.endswith("}")) or \
               (stripped.startswith("[") and stripped.endswith("]")):
                try:
                    resolved_value = json.loads(stripped)
                except (json.JSONDecodeError, ValueError):
                    pass  # keep as string if not valid JSON

        # For upsert into array sections: append to existing array, don't replace
        written = None
        if op == "upsert" and isinstance(resolved_value, dict) and not path.endswith("]"):
            existing = _get_by_path_local(resume, path)
            if isinstance(existing, list) and len(existing) > 0:
                # Array already has entries — append, don't replace
                existing.append(resolved_value)
                written = resolved_value
            else:
                # Empty or new array — wrap in list and set
                resolved_value = [resolved_value]
                result = _set_by_path_local(resume, path, resolved_value, upsert=True)
                if not result:
                    return ToolResult(success=False, tool_name="edit_field",
                        data={}, error=f"Invalid path: '{path}' — index out of bounds or path does not exist")
                written = _get_by_path_local(resume, path)
        elif op in ("update", "upsert"):
            result = _set_by_path_local(resume, path, resolved_value, upsert=(op == "upsert"))
            if not result:
                return ToolResult(success=False, tool_name="edit_field",
                    data={}, error=f"Invalid path: '{path}' — index out of bounds or path does not exist")
            written = _get_by_path_local(resume, path)
        elif op == "delete":
            _delete_by_path_inline(resume, path)
            written = "(deleted)"
        else:
            return ToolResult(success=False, tool_name="edit_field", data={}, error=f"Unknown op: {op}")

        try:
            _save(session_id=session_id, refined_resume_obj=resume)
        except Exception:
            pass

        return ToolResult(success=True, tool_name="edit_field",
                          data={"path": path, "op": op, "written": written, "reason": reason},
                          meta={"actionability": actionability, "confidence": confidence})
    except Exception as exc:
        return ToolResult(success=False, tool_name="edit_field", data={}, error=str(exc))


@tool("ask_user",
      "Pause and ask the user to confirm fact-sensitive changes. Use for phone, email, dates, names, GPA, institution, or when confidence < 0.4. The user will see a confirmation card with before/after values.",
      {"type": "object", "properties": {
          "items": {"type": "array", "items": {"type": "object", "properties": {
              "path": {"type": "string", "description": "Field path, e.g. 'personalInfo.phone'"},
              "current_value": {"type": "string", "description": "Current value in the resume"},
              "suggested_value": {"type": "string", "description": "New value you suggest"},
              "op": {"type": "string", "enum": ["update", "upsert"]},
              "reason": {"type": "string", "description": "Why this needs user confirmation"},
          }, "required": ["path", "current_value", "suggested_value"]}},
      }, "required": ["items"]})
def tool_ask_user(*, items: list | None = None, **kwargs: Any) -> ToolResult:
    items = items or []
    return ToolResult(
        success=True, tool_name="ask_user",
        data={"items": items},
        meta={"tool": "ask_user", "paused": True, "item_count": len(items)},
    )


# ── Simplified edit tools (preferred over edit_field) ───────────────

def _load_resume(session_id: str) -> tuple[dict, dict]:
    """Load session state and resume dict. Returns (state, resume)."""
    from ..session.service import get_session_content
    snapshot = get_session_content(session_id=session_id, message_limit=1, event_limit=1)
    state = snapshot.get("state", {}) if isinstance(snapshot.get("state", {}), dict) else {}
    resume = (
        state.get("refined_document_obj", {}) if isinstance(state.get("refined_document_obj", {}), dict)
        else state.get("refined_resume_obj", {}) if isinstance(state.get("refined_resume_obj", {}), dict)
        else {}
    )
    return state, resume


def _save_resume(session_id: str, resume: dict) -> None:
    from ..session.service import save_session_state
    from ..backends.session import get_session as _get_sess
    try:
        save_session_state(session_id=session_id, refined_resume_obj=resume)
        # Sync to recent_resumes so Builder preview sees agent edits
        sess = _get_sess(session_id, include_state=False)
        if sess:
            rid = str(sess.get("resume_id", "")).strip()
            if rid:
                from ..storage.recent_resume_store import save_recent_resume, get_recent_resume
                rr = get_recent_resume(rid, include_payload=False)
                if rr:
                    save_recent_resume(
                        resume_id=rid, title=str(rr.get("title", "")), source=str(rr.get("source", "tailor")),
                        tags=list(rr.get("tags", [])) if isinstance(rr.get("tags"), list) else [],
                        resume_obj=resume,
                        output_markdown=str(rr.get("output_markdown", "")),
                        output_html=str(rr.get("output_html", "")),
                        template_name=str(rr.get("template_name", "")),
                        layout_preferences=rr.get("layout_preferences"),
                    )
    except Exception:
        pass


@tool("add_entry",
      "Add a new entry to a resume section. Automatically appends — never overwrites existing entries. "
      "The section MUST be an array field: education, workExperience, personalProjects, research.",
      {"type": "object", "properties": {
          "section": {"type": "string", "enum": ["education", "workExperience", "personalProjects", "research"], "description": "Array section to append to"},
          "value": {"type": "string", "description": "JSON object string with ALL fields. Example: '{\"institution\":\"Tsinghua\",\"degree\":\"Master\",\"years\":\"2024-2026\",\"description\":[\"scholarship\"]}'"},
          "reason": {"type": "string", "description": "Brief reason in Chinese, under 30 chars."},
          "actionability": {"type": "string", "enum": ["apply_ready", "confirm_required"], "description": "confirm_required for fact-sensitive fields (institution, degree, years)."},
          "confidence": {"type": "number", "description": "Confidence 0.0-1.0."},
      }, "required": ["section", "value"]})
def tool_add_entry(*, session_id: str, section: str, value: str = "",
                   reason: str = "", actionability: str = "apply_ready",
                   confidence: float = 0.8, **kwargs: Any) -> ToolResult:
    _, resume = _load_resume(session_id)
    if not resume:
        return ToolResult(success=False, tool_name="add_entry", data={}, error="No resume loaded")

    # Parse JSON value
    entry = value
    if isinstance(value, str) and value.strip():
        stripped = value.strip()
        if stripped.startswith("{"):
            try:
                entry = json.loads(stripped)
            except (json.JSONDecodeError, ValueError):
                return ToolResult(success=False, tool_name="add_entry", data={},
                    error=f"Invalid JSON value. Must be a JSON object string like {{\"title\":\"...\",\"company\":\"...\"}}. Got: {value[:100]}")

    if not isinstance(entry, dict):
        return ToolResult(success=False, tool_name="add_entry", data={},
            error=f"Value must be a JSON object, got {type(entry).__name__}: {str(value)[:100]}")

    # Ensure section array exists
    arr = resume.get(section, [])
    if not isinstance(arr, list):
        arr = []
    arr.append(entry)
    resume[section] = arr
    _save_resume(session_id, resume)

    return ToolResult(success=True, tool_name="add_entry",
                      data={"section": section, "index": len(arr) - 1, "written": entry, "reason": reason},
                      meta={"actionability": actionability, "confidence": confidence})


_ARRAY_FIELD_ROOTS = {
    "additional.technicalSkills",
    "additional.languages",
    "additional.certificationsTraining",
    "additional.awards",
}


def _is_array_root(path: str) -> bool:
    """Check if path targets an array field root WITHOUT an index.
    'additional.technicalSkills' → blocked (would overwrite array with string)
    'additional.technicalSkills[0]' → allowed (edits specific item)
    """
    clean = path.strip().rstrip(".")
    for root in _ARRAY_FIELD_ROOTS:
        if clean == root:
            return True
    return False


@tool("update_field",
      "Update a LEAF field (plain text or simple value). For array fields (additional.technicalSkills etc) use add_entry or edit individual items with index like additional.technicalSkills[0].",
      {"type": "object", "properties": {
          "path": {"type": "string", "description": "Dot-path to a leaf field: 'summary', 'personalInfo.email', 'workExperience[0].description[1]'. NEVER use array roots like 'additional.technicalSkills' — use add_entry or index like 'additional.technicalSkills[0]' instead."},
          "value": {"type": "string", "description": "New text value. Plain text only — NOT a JSON object string."},
          "reason": {"type": "string", "description": "Brief reason in Chinese, under 30 chars."},
          "actionability": {"type": "string", "enum": ["apply_ready", "confirm_required"], "description": "confirm_required for fact-sensitive fields (name, email, phone, dates, gpa)."},
          "confidence": {"type": "number", "description": "Confidence 0.0-1.0."},
      }, "required": ["path", "value"]})
def tool_update_field(*, session_id: str, path: str, value: str = "",
                      reason: str = "", actionability: str = "apply_ready",
                      confidence: float = 0.8, **kwargs: Any) -> ToolResult:
    from ..session.service import _set_by_path_local, _get_by_path_local

    # Block: array root paths must use add_entry or indexed access
    if _is_array_root(path):
        return ToolResult(success=False, tool_name="update_field", data={},
            error=f"Cannot update array root '{path}'. Use add_entry() to append new items, "
                  f"set_entry('{path}[N]') to replace items, or delete_entry('{path}[N]') to remove items. "
                  f"To edit a single item: use '{path}[0]' (with index).")

    _, resume = _load_resume(session_id)
    if not resume:
        return ToolResult(success=False, tool_name="update_field", data={}, error="No resume loaded")

    ok = _set_by_path_local(resume, path, value)
    if not ok:
        return ToolResult(success=False, tool_name="update_field", data={},
            error=f"Invalid path: '{path}' — path does not exist")

    written = _get_by_path_local(resume, path)
    _save_resume(session_id, resume)

    return ToolResult(success=True, tool_name="update_field",
                      data={"path": path, "written": written, "reason": reason},
                      meta={"actionability": actionability, "confidence": confidence})


@tool("set_entry",
      "Replace an entire entry in an array section (identified by index). "
      "For example, replace education[0] or workExperience[1] with a new complete JSON object.",
      {"type": "object", "properties": {
          "path": {"type": "string", "description": "Full path with array index. Examples: 'education[0]', 'workExperience[1]', 'personalProjects[0]'"},
          "value": {"type": "string", "description": "Complete JSON object string with ALL fields of that entry. Example: '{\"institution\":\"MIT\",\"degree\":\"PhD\",\"years\":\"2020-2024\",\"description\":[\"published 3 papers\"]}'"},
          "reason": {"type": "string", "description": "Brief reason in Chinese, under 30 chars."},
          "actionability": {"type": "string", "enum": ["apply_ready", "confirm_required"], "description": "confirm_required for fact-sensitive fields."},
          "confidence": {"type": "number", "description": "Confidence 0.0-1.0."},
      }, "required": ["path", "value"]})
def tool_set_entry(*, session_id: str, path: str, value: str = "",
                   reason: str = "", actionability: str = "apply_ready",
                   confidence: float = 0.8, **kwargs: Any) -> ToolResult:
    from ..session.service import _set_by_path_local, _get_by_path_local
    _, resume = _load_resume(session_id)
    if not resume:
        return ToolResult(success=False, tool_name="set_entry", data={}, error="No resume loaded")

    # Parse JSON value
    entry = value
    if isinstance(value, str) and value.strip():
        stripped = value.strip()
        if stripped.startswith("{"):
            try:
                entry = json.loads(stripped)
            except (json.JSONDecodeError, ValueError):
                return ToolResult(success=False, tool_name="set_entry", data={},
                    error=f"Invalid JSON value: {value[:100]}")

    if not isinstance(entry, dict):
        return ToolResult(success=False, tool_name="set_entry", data={},
            error=f"Value must be a JSON object string, got {type(entry).__name__}: {str(value)[:100]}")

    ok = _set_by_path_local(resume, path, entry)
    if not ok:
        return ToolResult(success=False, tool_name="set_entry", data={},
            error=f"Invalid path: '{path}' — index out of bounds or path does not exist")

    written = _get_by_path_local(resume, path)
    _save_resume(session_id, resume)

    return ToolResult(success=True, tool_name="set_entry",
                      data={"path": path, "written": written, "reason": reason},
                      meta={"actionability": actionability, "confidence": confidence})


@tool("delete_entry",
      "Delete an entry from a resume array section, or clear a leaf field.",
      {"type": "object", "properties": {
          "path": {"type": "string", "description": "Path to delete: 'education[0]' to remove an entry, 'summary' to clear a field"},
          "reason": {"type": "string", "description": "Brief reason in Chinese, under 30 chars."},
      }, "required": ["path"]})
def tool_delete_entry(*, session_id: str, path: str, reason: str = "", **kwargs: Any) -> ToolResult:
    from ..session.service import _get_by_path_local
    _, resume = _load_resume(session_id)
    if not resume:
        return ToolResult(success=False, tool_name="delete_entry", data={}, error="No resume loaded")

    # Find parent array and index for array entries
    import re
    m = re.match(r'^(\w+)\[(\d+)\]$', path)
    if m:
        arr_name, idx_str = m.groups()
        idx = int(idx_str)
        arr = resume.get(arr_name, [])
        if not isinstance(arr, list):
            return ToolResult(success=False, tool_name="delete_entry", data={},
                error=f"'{arr_name}' is not an array")
        if idx >= len(arr):
            return ToolResult(success=False, tool_name="delete_entry", data={},
                error=f"Index {idx} out of bounds for '{arr_name}' (length {len(arr)})")
        arr.pop(idx)
        _save_resume(session_id, resume)
        return ToolResult(success=True, tool_name="delete_entry",
                          data={"path": path, "written": "(deleted)", "reason": reason})

    # Leaf field: just set to empty
    current = _get_by_path_local(resume, path)
    if current is None:
        return ToolResult(success=False, tool_name="delete_entry", data={},
            error=f"Path '{path}' does not exist")
    from ..session.service import _set_by_path_local
    _set_by_path_local(resume, path, "")
    _save_resume(session_id, resume)
    return ToolResult(success=True, tool_name="delete_entry",
                      data={"path": path, "written": "(cleared)", "reason": reason})


@tool("set_target_jd",
      "Set or change the target job description the user is optimizing for. Call this after search_jd when the user picks a JD, or when the user asks to target a specific role/company.",
      {"type": "object", "properties": {
          "jd_text": {"type": "string", "description": "Full JD text to target. From search_jd results or user-provided."},
          "jd_id": {"type": "string", "description": "JD identifier from search_jd results, if applicable."},
          "card_summary": {"type": "string", "description": "Short summary shown on the JD card, if known."},
          "metadata": {"type": "object", "description": "Metadata from search_jd result, if known."},
      }, "required": ["jd_text"]})
def tool_set_target_jd(*, session_id: str, jd_text: str = "", jd_id: str = "",
                       card_summary: str = "", metadata: dict | None = None,
                       **kwargs: Any) -> ToolResult:
    metadata = metadata if isinstance(metadata, dict) else {}
    summary = card_summary or _jd_card_summary(jd_text, metadata)
    if session_id and str(jd_text or "").strip():
        _save_target_jd_to_session(
            session_id=session_id,
            jd_text=jd_text,
            jd_id=jd_id,
            metadata=metadata,
            card_summary=summary,
        )
    return ToolResult(success=True, tool_name="set_target_jd",
                      data={"target_jd": jd_text, "jd_id": jd_id,
                            "metadata": metadata, "card_summary": summary},
                      meta={"tool": "set_target_jd"})


@tool("compose",
      "Finish the turn and compose the final response. ALWAYS call this after editing or when no edits needed.",
      {"type": "object", "properties": {
          "assistant_message": {"type": "string", "description": "Your main response. Put the FULL answer here."},
          "show_jd_cards": {"type": "boolean", "description": "Set true ONLY when user explicitly asked to 'show'/'list'/'display' JD results. Default false."},
          "guide_prompts": {"type": "array", "items": {
              "type": "object", "properties": {
                  "label": {"type": "string"}, "text": {"type": "string"}
              }, "required": ["label", "text"]
          }, "description": "2-3 suggested next actions."},
      }, "required": ["assistant_message"]})
def tool_compose(*, assistant_message: str = "",
                 show_jd_cards: bool = False,
                 guide_prompts: list | None = None, **kwargs: Any) -> ToolResult:
    return ToolResult(success=True, tool_name="compose",
                      data={"assistant_message": assistant_message,
                            "show_jd_cards": show_jd_cards,
                            "guide_prompts": guide_prompts or []},
                      meta={"tool": "compose"})
