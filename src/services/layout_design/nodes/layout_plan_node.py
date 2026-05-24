from typing import Any, Dict

from ...build_llm import build_llm
from ..prompts import build_layout_planner_prompts
from ..state import LayoutDesignState
from .common import default_layout_plan, extract_json_dict, get_metadata, get_theme, normalize_layout_plan


def generate_layout_plan(state: LayoutDesignState) -> Dict[str, Any]:
    resume_obj = state.get("resume_obj", {})
    preferences = state.get("layout_preferences", {})
    theme = get_theme(preferences)
    metadata = get_metadata(preferences)

    cached = metadata.get("layout_plan")
    if isinstance(cached, dict):
        return {"layout_plan": normalize_layout_plan(cached, theme)}

    fallback = default_layout_plan(theme)

    llm = build_llm()
    system_prompt, user_prompt = build_layout_planner_prompts(
        resume_obj=resume_obj if isinstance(resume_obj, dict) else {},
        preferences=preferences if isinstance(preferences, dict) else {},
        fallback_plan=fallback,
    )
    response = llm.invoke([("system", system_prompt), ("human", user_prompt)])
    plan = extract_json_dict(getattr(response, "content", "") or "")
    return {"layout_plan": normalize_layout_plan(plan, theme)}
