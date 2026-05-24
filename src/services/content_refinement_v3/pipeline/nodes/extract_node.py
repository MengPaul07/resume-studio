from typing import Any, Dict

from ...prompts.agent import build_parse_prompt
from ...domain.types import JsonToolsState
from .utils import extract_json_dict, invoke_llm


def raw_text_categorizer(state: JsonToolsState) -> Dict[str, Any]:
    raw_text = state.get("raw_input", "")
    system_prompt = "You are a strict resume parser. Return only valid JSON."
    user_prompt = build_parse_prompt(raw_text)

    response = invoke_llm([("system", system_prompt), ("human", user_prompt)])
    content = getattr(response, "content", "") or ""
    data = extract_json_dict(content)
    if not data:
        raise ValueError("LLM returned invalid resume JSON in extract stage.")
    return {
        "raw_resume_obj": data,
        "resume_obj": data,
    }
