from typing import Any, Dict, List, TypedDict


class JsonToolsState(TypedDict):
    doc_type: str
    raw_input: str
    user_feedback: str
    raw_document_obj: Dict[str, Any]
    normalized_document_obj: Dict[str, Any]
    refined_document_obj: Dict[str, Any]
    suggestion_document_obj: Dict[str, Any]
    raw_resume_obj: Dict[str, Any]
    normalized_resume_obj: Dict[str, Any]
    rag_context_by_path: Dict[str, Any]
    content_plan: Dict[str, Any]
    section_refinements: Dict[str, Any]
    section_quality_map: Dict[str, Any]
    quality_report: Dict[str, Any]
    applied_changes: List[Dict[str, Any]]
    suggestion_resume_obj: Dict[str, Any]
    refined_resume_obj: Dict[str, Any]
    review_payload: Dict[str, Any]
    human_review_decision: Dict[str, Any]
    validation_report: Dict[str, Any]
    resume_obj: Dict[str, Any]
    document_obj: Dict[str, Any]
    input: Dict[str, Any]


# Backward-compatible alias for legacy node annotations.
LayoutAgentState = JsonToolsState
