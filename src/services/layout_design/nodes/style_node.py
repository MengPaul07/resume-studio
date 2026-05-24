from typing import Any, Dict, List

from ...build_llm import build_llm
from ..prompts import build_style_designer_prompts
from ..state import LayoutDesignState
from .common import default_style_options, extract_json_dict, get_metadata, get_theme, normalize_style_options


def generate_style_options(state: LayoutDesignState, style_count: int = 4) -> Dict[str, List[Dict[str, Any]]]:
    resume_obj = state.get("resume_obj", {})
    preferences = state.get("layout_preferences", {})
    theme = get_theme(preferences)
    metadata = get_metadata(preferences)

    cached = metadata.get("style_options")
    if isinstance(cached, list) and cached:
        return {"style_options": normalize_style_options(cached, theme)}

    fallback = default_style_options(theme)

    llm = build_llm()
    system_prompt, user_prompt = build_style_designer_prompts(
        resume_obj=resume_obj if isinstance(resume_obj, dict) else {},
        preferences=preferences if isinstance(preferences, dict) else {},
        fallback_styles=fallback,
        style_count=style_count,
    )
    response = llm.invoke([("system", system_prompt), ("human", user_prompt)])
    parsed = extract_json_dict(getattr(response, "content", "") or "")
    styles = normalize_style_options(parsed.get("styles", []), theme)
    return {"style_options": styles}
