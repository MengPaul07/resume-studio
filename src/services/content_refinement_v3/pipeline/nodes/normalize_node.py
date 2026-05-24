from copy import deepcopy
from typing import Any, Dict, List

from ...domain.types import JsonToolsState


def _ensure_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _ensure_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def normalize_resume_json(state: JsonToolsState) -> Dict[str, Any]:
    raw = deepcopy(state.get("raw_resume_obj", {}))
    if not isinstance(raw, dict):
        raise ValueError("raw_resume_obj is invalid for normalize stage.")

    normalized: Dict[str, Any] = {
        "personalInfo": _ensure_dict(raw.get("personalInfo")),
        "summary": raw.get("summary", "") or "",
        "workExperience": _ensure_list(raw.get("workExperience")),
        "education": _ensure_list(raw.get("education")),
        "personalProjects": _ensure_list(raw.get("personalProjects")),
        "additional": _ensure_dict(raw.get("additional")),
        "customSections": _ensure_dict(raw.get("customSections")),
    }

    normalized["additional"].setdefault("technicalSkills", [])
    normalized["additional"].setdefault("languages", [])
    normalized["additional"].setdefault("certificationsTraining", [])
    normalized["additional"].setdefault("awards", [])

    return {"normalized_resume_obj": normalized}
