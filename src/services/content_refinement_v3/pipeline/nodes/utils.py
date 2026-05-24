import json
import re
from typing import Any, Dict, List, Tuple

try:
    from ....build_llm import build_llm
except Exception:
    from build_llm import build_llm


def extract_json_dict(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {}

    if raw.startswith("```"):
        lines = raw.splitlines()
        if len(lines) >= 2:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return {}

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def invoke_llm(messages: List[Tuple[str, str]]) -> Any:
    llm = build_llm()
    if llm is None:
        raise RuntimeError("LLM is not initialized. Check your model configuration.")
    return llm.invoke(messages)
