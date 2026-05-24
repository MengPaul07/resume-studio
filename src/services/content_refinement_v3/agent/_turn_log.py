"""Lightweight turn logger — saves every manual turn to disk for debugging.

Format is compatible with eval logs so bench tools (explain, compare) work.
Always on; no config needed. Output to outputs/manual_logs/.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_DIR = PROJECT_ROOT / "outputs" / "manual_logs"


def save_turn_log(
    *,
    session_id: str,
    turn_id: str,
    message: str,
    final_payload: Dict[str, Any],
    output_dir: Path | None = None,
    sse_trace: list[dict[str, Any]] | None = None,
) -> Path | None:
    """Save a compact turn log + full SSE trace. Returns the file path or None on failure."""
    try:
        out = output_dir or DEFAULT_DIR
        now = datetime.now(timezone.utc)
        date_dir = out / now.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        selected_tool_chain = final_payload.get("selected_tool_chain", [])
        intent_state = final_payload.get("intent_state", {})
        actionability_summary = final_payload.get("actionability_summary", {})
        assistant_message = str(final_payload.get("assistant_message", "")).strip()
        suggestion_doc = final_payload.get("suggestion_document_obj", {}) or {}

        # Compact suggestion diffs
        items = suggestion_doc.get("items", []) if isinstance(suggestion_doc, dict) else []
        suggestion_diffs = []
        for item in (items or []):
            if not isinstance(item, dict):
                continue
            suggestion_diffs.append({
                "path": str(item.get("path", "")),
                "before": str(item.get("current_value", ""))[:100],
                "after": str(item.get("suggested_value", ""))[:100],
                "actionability": str(item.get("actionability", "")),
            })

        # Compact SSE trace: just event names + key data
        compact_trace = []
        if sse_trace:
            for ev in sse_trace:
                entry = {
                    "seq": ev.get("seq", 0),
                    "event": ev.get("event", "?"),
                    "elapsed_ms": ev.get("elapsed_ms", 0),
                }
                d = ev.get("data", {})
                if ev["event"] == "thinking":
                    entry["text"] = str(d.get("text", ""))[:300]
                elif ev["event"] == "tool.executed":
                    entry["tool"] = d.get("tool_name", "")
                    entry["ok"] = d.get("success", False)
                elif ev["event"] == "step.succeeded":
                    entry["tool"] = d.get("tool", "")
                elif ev["event"] == "turn.completed":
                    entry["suggestions"] = d.get("actionability_summary", {}).get("total", 0)
                    entry["asst"] = str(d.get("assistant_message", ""))[:200]
                compact_trace.append(entry)

        log = {
            "timestamp": now.isoformat(timespec="seconds"),
            "session_id": session_id,
            "turn_id": turn_id,
            "message": str(message or "")[:300],
            "intent": intent_state,
            "chain": selected_tool_chain,
            "actionability": actionability_summary,
            "suggestions": suggestion_diffs,
            "fact_issues": final_payload.get("fact_issues", [])[:10],
            "verdict": str(final_payload.get("self_check_result", {}).get("result", "")),
            "assistant_message": assistant_message[:800],
            "thinking": str(final_payload.get("thinking", ""))[:500],
            "low_confidence_items": len(final_payload.get("low_confidence_items", []) or []),
            "termination_reason": str(final_payload.get("termination_reason", "")),
            "sse_trace": compact_trace if compact_trace else None,
        }

        ts = now.strftime("%H%M%S")
        filename = f"{ts}_{session_id[:8]}_{turn_id[:8]}.json"
        filepath = date_dir / filename
        filepath.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

        return filepath
    except Exception as exc:
        import traceback, logging
        logging.getLogger(__name__).warning("[turn_log] save failed: %s", exc)
        traceback.print_exc()
        return None
