from typing import Any, Dict

from ...prompts.agent import build_parse_prompt
from ...domain.types import JsonToolsState
from .utils import extract_json_dict, invoke_llm


def raw_text_categorizer(state: JsonToolsState) -> Dict[str, Any]:
    raw_text = state.get("raw_input", "")
    system_prompt = "You are a strict resume parser that outputs only valid JSON."
    user_prompt = build_parse_prompt(raw_text)

    response = invoke_llm(
        [("system", system_prompt), ("human", user_prompt)],
        response_format={"type": "json_object"},
    )
    content = getattr(response, "content", "") or ""
    data = extract_json_dict(content)

    # Retry once without json_object if the first attempt returned nothing
    if not data:
        response = invoke_llm(
            [("system", system_prompt), ("human", user_prompt)],
        )
        content = getattr(response, "content", "") or ""
        data = extract_json_dict(content)

    is_empty = not data or (isinstance(data, dict) and len(data) == 0)
    return {
        "raw_resume_obj": data,
        "resume_obj": data,
        "parse_warning": "No resume structure detected in the imported file. The content may not be a resume." if is_empty else "",
    }
