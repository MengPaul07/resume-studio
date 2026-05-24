from typing import Any, Dict, List

from ...domain.types import JsonToolsState

try:
    from ....rag import RagService
except Exception:
    try:
        from rag import RagService  # type: ignore
    except Exception:
        RagService = None  # type: ignore


def retrieve_rag_context(state: JsonToolsState) -> Dict[str, Any]:
    resume_obj = state.get("raw_resume_obj", {})
    if not isinstance(resume_obj, dict) or not resume_obj:
        return {"rag_context_by_path": {}}

    if RagService is None:
        return {"rag_context_by_path": {}}

    preferences = state.get("input", {}).get("layout_preferences", {}) or {}
    target_role = str(
        preferences.get("target", {}).get("role")
        or state.get("target_role", "")
        or ""
    )
    language = str(
        preferences.get("locale", {}).get("language")
        or preferences.get("language")
        or "zh"
    )

    if not target_role.strip():
        return {"rag_context_by_path": {}}

    try:
        rag_service = RagService()
        snippets = rag_service.retrieve_jd_context(
            target_role=target_role,
            language=language,
            top_k=15,
        )
    except Exception:
        return {"rag_context_by_path": {}}

    context_by_path: Dict[str, List[Dict[str, Any]]] = {}
    for snippet in snippets:
        meta = snippet.get("metadata", {}) if isinstance(snippet.get("metadata", {}), dict) else {}
        pk = str(meta.get("path_key", "") or "job_description")
        if pk not in context_by_path:
            context_by_path[pk] = []
        context_by_path[pk].append(snippet)

    return {"rag_context_by_path": context_by_path}
