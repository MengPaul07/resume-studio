"""Detailed turn logger — saves complete LLM interaction trace to disk.

Every turn produces a JSON log with:
  - Per-round LLM reasoning + tool calls (full arguments)
  - Per-tool execution results (success/error + return data)
  - Final compose output and suggestions

Format: outputs/manual_logs/{date}/{time}_{sessionId8}_{turnId8}.json
Always on; no config needed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

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
    agent_dump: Dict[str, Any] | None = None,
) -> Path | None:
    """Save a full turn log with LLM interaction details.

    agent_dump should contain the raw agent loop output dict from _run_agent_loop,
    which includes sse_events with tool_call and tool_result entries.
    """
    try:
        out = output_dir or DEFAULT_DIR
        now = datetime.now(timezone.utc)
        date_dir = out / now.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        # ── Build per-round LLM interaction log ──
        rounds: List[Dict[str, Any]] = []
        if agent_dump and agent_dump.get("sse_events"):
            current_round: Dict[str, Any] | None = None
            for kind, data in agent_dump["sse_events"]:
                if kind == "llm_tool_decision":
                    if current_round is None:
                        current_round = {"decisions": [], "executions": []}
                        rounds.append(current_round)
                    current_round.setdefault("decisions", []).append({
                        "tool": data.get("name", "?"),
                        "arguments": data.get("arguments", {}),
                        "round": data.get("round", 0),
                    })
                if kind == "tool_call":
                    if current_round is None:
                        current_round = {"decisions": [], "executions": []}
                        rounds.append(current_round)
                    current_round["decisions"].append({
                        "name": data.get("name", "?"),
                        "arguments": data.get("arguments", {}),
                    })
                elif kind == "tool_result":
                    if current_round is None:
                        current_round = {"decisions": [], "executions": []}
                        rounds.append(current_round)
                    current_round.setdefault("executions", []).append({
                        "tool": data.get("name", "?"),
                        "success": data.get("success", False),
                        "result": _truncate_dict(data.get("data", {}), 800),
                        "error": str(data.get("error", ""))[:200] if data.get("error") else None,
                        "ms": data.get("ms", 0),
                    })
                elif kind == "thinking":
                    if current_round is None:
                        current_round = {"decisions": [], "executions": []}
                        rounds.append(current_round)
                    current_round["thinking"] = str(data)[:500]
                elif kind == "reasoning":
                    if current_round is None:
                        current_round = {"decisions": [], "executions": []}
                        rounds.append(current_round)
                    current_round["reasoning"] = str(data)[:500]
                elif kind == "step_start":
                    current_round = {"decisions": [], "executions": []}
                    rounds.append(current_round)

        # Remove empty rounds
        rounds = [r for r in rounds if r.get("decisions") or r.get("executions")]

        # ── Compact suggestion diffs ──
        suggestion_doc = final_payload.get("suggestion_document_obj", {}) or {}
        items = suggestion_doc.get("items", []) if isinstance(suggestion_doc, dict) else []
        suggestion_diffs = []
        for item in (items or []):
            if not isinstance(item, dict):
                continue
            suggestion_diffs.append({
                "path": str(item.get("path", "")),
                "before": str(item.get("current_value", ""))[:200],
                "after": str(item.get("suggested_value", ""))[:200],
                "actionability": str(item.get("actionability", "")),
                "reason": str(item.get("reason", ""))[:80],
            })

        # ── Compact SSE event timeline ──
        timeline = []
        if sse_trace:
            for ev in sse_trace:
                etype = ev.get("event", "?")
                entry = {"event": etype, "ms": ev.get("elapsed_ms", 0)}
                d = ev.get("data", {})
                if etype == "turn.step_done":
                    entry["tool"] = d.get("tool", "")
                    entry["step"] = d.get("step_id", "")
                    if d.get("status") == "failed":
                        entry["error"] = str(d.get("error", ""))[:200]
                elif etype == "turn.completed":
                    entry["suggestions"] = d.get("actionability_summary", {}).get("total", 0)
                elif etype == "turn.thinking":
                    entry["text"] = str(d.get("text", ""))[:200]
                timeline.append(entry)

        # ── Assemble ──
        selected_tool_chain = final_payload.get("selected_tool_chain", [])
        actionability_summary = final_payload.get("actionability_summary", {})

        log = {
            "timestamp": now.isoformat(timespec="seconds"),
            "session_id": session_id,
            "turn_id": turn_id,
            "user_message": str(message or "")[:500],

            # LLM interaction trace (NEW — the most useful part)
            "rounds": rounds if rounds else None,

            # Tool chain summary
            "tool_names": agent_dump.get("tool_names", []) if agent_dump else [],

            # Agent thinking dump
            "thinking": str(agent_dump.get("thinking", ""))[:1000] if agent_dump else "",

            # Final output
            "assistant_message": str(final_payload.get("assistant_message", ""))[:1000],
            "actionability": actionability_summary,
            "suggestions": suggestion_diffs,
            "fact_issues": final_payload.get("fact_issues", [])[:20],

            # Meta
            "verdict": str(final_payload.get("self_check_result", {}).get("result", "")),
            "termination_reason": str(final_payload.get("termination_reason", "")),
            "intent": final_payload.get("intent_state", {}),
            "low_confidence_count": len(final_payload.get("low_confidence_items", []) or []),

            # Timeline (lightweight SSE view)
            "timeline": timeline if timeline else None,
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


def _truncate_dict(d: Any, max_len: int) -> Any:
    """Truncate long strings in a nested dict/list for log readability."""
    if isinstance(d, str):
        return d if len(d) <= max_len else d[:max_len] + "..."
    if isinstance(d, dict):
        return {k: _truncate_dict(v, max_len) for k, v in d.items()}
    if isinstance(d, list):
        if len(d) > 10:
            return [_truncate_dict(x, max_len) for x in d[:10]] + [f"...({len(d) - 10} more)"]
        return [_truncate_dict(x, max_len) for x in d]
    return d
