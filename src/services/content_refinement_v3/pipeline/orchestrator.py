from typing import Any, Dict
from uuid import uuid4

from .nodes.extract_node import raw_text_categorizer
from .nodes.normalize_node import normalize_resume_json


def json_parse_document(
    *,
    doc_type: str,
    raw_input: str,
    layout_preferences: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    del layout_preferences  # reserved for future use
    if str(doc_type or "resume").strip().lower() != "resume":
        raise ValueError(f"unsupported doc_type: {doc_type}")
    state = {"raw_input": raw_input}
    state = {**state, **raw_text_categorizer(state)}
    state = {**state, **normalize_resume_json(state)}
    return {
        "trace_id": str(uuid4()),
        "doc_type": "resume",
        "raw_document_obj": state.get("raw_resume_obj", {}),
        "normalized_document_obj": state.get("normalized_resume_obj", {}),
    }


def json_parse_resume(raw_input: str, layout_preferences: Dict[str, Any] | None = None) -> Dict[str, Any]:
    result = json_parse_document(doc_type="resume", raw_input=raw_input, layout_preferences=layout_preferences)
    return {
        "trace_id": result.get("trace_id", ""),
        "raw_resume_obj": result.get("raw_document_obj", {}),
        "normalized_resume_obj": result.get("normalized_document_obj", {}),
    }
