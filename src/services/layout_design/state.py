from typing import Any, Dict, List, TypedDict


class LayoutDesignState(TypedDict, total=False):
    resume_obj: Dict[str, Any]
    layout_preferences: Dict[str, Any]
    raw_resume_obj: Dict[str, Any]
    suggestion_resume_obj: Dict[str, Any]
    refined_resume_obj: Dict[str, Any]

    layout_plan: Dict[str, Any]
    style_options: List[Dict[str, Any]]
    selected_style_id: str
    active_style: Dict[str, Any]
    design_spec: Dict[str, Any]

    output_markdown: str
    output_html: str
