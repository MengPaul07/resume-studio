import json
import os
from typing import Any, Dict

from ...build_llm import build_llm
from ..state import LayoutDesignState
from .common import build_json_block


def generate_markdown(state: LayoutDesignState) -> Dict[str, str]:
    enable_markdown = os.getenv("LAYOUT_ENABLE_MARKDOWN", "false").strip().lower() == "true"
    if not enable_markdown:
        return {"output_markdown": ""}

    resume_obj = state.get("resume_obj", {})

    llm = build_llm()
    system_prompt = "You are a resume markdown writer. Output markdown only."
    user_prompt = (
        "Convert this resume JSON to professional markdown. Keep all sections and all factual details.\n\n"
        f"Resume JSON:\n{json.dumps(resume_obj, ensure_ascii=False)}"
    )
    response = llm.invoke([("system", system_prompt), ("human", user_prompt)])
    markdown_body = (getattr(response, "content", "") or "").strip()
    if not markdown_body:
        raise ValueError("LLM returned empty markdown in layout_design stage.")

    sections = [markdown_body]
    raw_resume_obj = state.get("raw_resume_obj", {})
    suggestion_resume_obj = state.get("suggestion_resume_obj", {})
    refined_resume_obj = state.get("refined_resume_obj", {})

    if isinstance(raw_resume_obj, dict) and raw_resume_obj:
        sections.append(build_json_block("Raw Resume JSON", raw_resume_obj))
    if isinstance(suggestion_resume_obj, dict) and suggestion_resume_obj:
        sections.append(build_json_block("Content Suggestion JSON", suggestion_resume_obj))
    if isinstance(refined_resume_obj, dict) and refined_resume_obj:
        sections.append(build_json_block("Refined Resume JSON", refined_resume_obj))

    return {"output_markdown": "\n\n".join(sections).strip()}
