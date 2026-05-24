"""Utility: safe JSON parsing for LLM output."""

from __future__ import annotations

import json
from typing import Any


def _safe_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    text = str(value or "").strip()
    if not text:
        return {}
    import re as _re
    text = _re.sub(r"^```(?:json)?\s*\n?", "", text, flags=_re.IGNORECASE)
    text = _re.sub(r"\n?```\s*$", "", text)
    text = text.strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}
