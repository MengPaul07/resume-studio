"""LLM-as-Judge for D-Resume output quality evaluation (5 dimensions)."""

from __future__ import annotations

import concurrent.futures
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

JUDGE_SYSTEM_PROMPT = """Role: Resume Optimization Quality Evaluator.

Score the response on 5 dimensions (1-5). Each dimension has anchor examples.

1. relevance — Does the response directly address the user's request?
   5: Perfectly addresses the request, every suggestion targets the user's stated need
   3: Partially addresses it — some parts are relevant, others wander off-topic
   1: Ignores the request entirely, responds to something else

2. tone — Is the language professional, fluent, and appropriate?
   5: Polished professional writing, no awkward phrasing, appropriate tone for the context
   3: Acceptable but has awkward phrasing or minor tone issues
   1: Unprofessional, broken language, or completely inappropriate tone

3. accuracy — Are facts correct? No invented content or hallucinations?
   5: All stated facts about the resume are correct, no fabricated information
   3: Minor inaccuracies or overly generic statements that could apply to any resume
   1: Fabricates resume content, makes claims not present in the original, or gives wrong information

4. actionability — Can the user immediately act on the suggestions?
   5: Suggestions are specific, well-structured, with clear before/after paths
   3: Suggestions are present but vague — user would need to figure out specifics themselves
   1: No actionable output, only generic commentary with no concrete changes proposed

5. conciseness — Is the response the right length?
   5: Exactly the right amount of detail — no fluff, no missing essentials
   3: Slightly too verbose or too terse, but still usable
   1: Excessively long and rambling, OR critically too short (one word)

Output ONLY valid JSON with no markdown fences:
{"relevance":{"score":4,"reason":"brief in English"},"tone":{"score":4,"reason":"brief"},"accuracy":{"score":4,"reason":"brief"},"actionability":{"score":4,"reason":"brief"},"conciseness":{"score":4,"reason":"brief"},"overall":4.0,"summary":"one sentence"}
"""


def _safe_json(text: str) -> Dict[str, Any]:
    text = str(text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:-1] if lines[-1].startswith("```") else lines[1:]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _build_llm():
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.services.build_llm import build_llm
    return build_llm()


def judge_single(*, user_message: str, assistant_response: str, intent_class: str = "",
                 suggestion_diffs: List[Dict] | None = None, llm=None) -> Dict[str, Any]:
    if llm is None:
        llm = _build_llm()

    parts = ["=== USER MESSAGE ===", user_message or "(empty)"]
    if intent_class:
        parts.append(f"\n=== EXPECTED INTENT ===\n{intent_class}")

    if suggestion_diffs:
        parts.append("\n=== SUGGESTION CHANGES (before -> after) ===")
        for item in suggestion_diffs[:10]:
            parts.append(f"  {item.get('path', '')} [{item.get('actionability', '')}]")
            parts.append(f"    - {item.get('before', '')[:150]}")
            parts.append(f"    + {item.get('after', '')[:150]}")
            if item.get('reason'):
                parts.append(f"    reason: {item['reason'][:100]}")

    parts.extend(["\n=== ASSISTANT RESPONSE ===", (assistant_response or "(empty)")[:3000]])
    user_prompt = "\n".join(parts)

    try:
        result = llm.invoke([
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ])
        parsed = _safe_json(result.content or "")
    except Exception as exc:
        return {"error": str(exc)}

    if not parsed:
        return {"error": "Failed to parse judge response"}

    scores = {}
    for dim in ["relevance", "tone", "accuracy", "actionability", "conciseness"]:
        d = parsed.get(dim, {})
        scores[dim] = {"score": int(d.get("score", 0)) if isinstance(d, dict) else 0,
                       "reason": str(d.get("reason", "")) if isinstance(d, dict) else ""}
    overall = float(parsed.get("overall", 0) or 0)
    if overall == 0:
        valid = [s["score"] for s in scores.values() if s["score"] > 0]
        overall = sum(valid) / max(1, len(valid))

    return {"scores": scores, "overall": round(overall, 1),
            "summary": str(parsed.get("summary", "")),
            "judged_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def judge_directory(log_dir: Path, output_dir: Optional[Path] = None, llm=None, limit: int = 0, concurrency: int = 4) -> List[Dict[str, Any]]:
    from bench.metrics import load_logs as _load

    search = log_dir / "logs" if (log_dir / "logs").exists() else log_dir
    logs = _load(search)
    if limit > 0:
        logs = logs[:limit]

    run_dir = search.parent if search.name == "logs" else search
    out_dir = output_dir or (run_dir / "judged")
    out_dir.mkdir(parents=True, exist_ok=True)

    def _judge_one(i: int, log: Dict) -> Dict:
        nm = log.get("scenario", {}).get("name", f"log_{i}")
        user_msg = log.get("scenario", {}).get("message", "")
        asst_msg = log.get("turn", {}).get("assistant_message", "")
        intent = log.get("scenario", {}).get("expected_intent", "")
        sugg_items = (log.get("suggestion_diff") or {}).get("items", [])
        _llm = _build_llm()
        result = judge_single(user_message=user_msg, assistant_response=asst_msg,
                              intent_class=intent, suggestion_diffs=sugg_items if sugg_items else None, llm=_llm)
        log["quality_scores"] = result
        out_path = out_dir / f"judged_{nm}.json"
        out_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        return log

    enhanced = []
    if concurrency <= 1:
        for i, log in enumerate(logs, 1):
            enhanced.append(_judge_one(i, log))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
            futures = {ex.submit(_judge_one, i, log): i for i, log in enumerate(logs, 1)}
            for f in concurrent.futures.as_completed(futures):
                enhanced.append(f.result())
    enhanced.sort(key=lambda l: l.get("meta", {}).get("scenario_index", 0))

    for i, log in enumerate(enhanced, 1):
        nm = log.get("scenario", {}).get("name", f"log_{i}")
        result = log.get("quality_scores", {})
        if "scores" in result:
            sc = " | ".join(f"{d}={result['scores'].get(d, {}).get('score', '?')}"
                            for d in ["relevance", "tone", "accuracy", "actionability", "conciseness"])
            print(f"[{i:02d}/{len(enhanced)}] {nm}  {sc} | overall={result.get('overall', '?')}")
        elif "error" in result:
            print(f"[{i:02d}/{len(enhanced)}] {nm}  ERROR: {result['error']}")

    agg = _aggregate_quality(enhanced)
    (out_dir / "quality_summary.json").write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nQuality summary saved: {out_dir / 'quality_summary.json'}")
    return enhanced


def _aggregate_quality(logs: List[Dict]) -> Dict[str, Any]:
    dims = ["relevance", "tone", "accuracy", "actionability", "conciseness"]
    scores_by_dim: Dict[str, List[float]] = {d: [] for d in dims}
    overalls: List[float] = []
    for l in logs:
        qs = l.get("quality_scores", {})
        if "error" in qs:
            continue
        for d in dims:
            s = qs.get("scores", {}).get(d, {})
            if isinstance(s, dict) and s.get("score", 0) > 0:
                scores_by_dim[d].append(float(s["score"]))
        ov = qs.get("overall", 0)
        if ov > 0:
            overalls.append(float(ov))

    summary: Dict[str, Any] = {
        "judged_count": len([l for l in logs if "error" not in l.get("quality_scores", {})]),
        "error_count": len([l for l in logs if "error" in l.get("quality_scores", {})]),
        "overall_avg": round(statistics_mean(overalls), 2) if overalls else 0,
        "overall_min": round(min(overalls), 2) if overalls else 0,
        "overall_max": round(max(overalls), 2) if overalls else 0,
        "dimensions": {},
    }
    import statistics as _st
    for d in dims:
        vals = scores_by_dim[d]
        if vals:
            summary["dimensions"][d] = {"avg": round(_st.mean(vals), 2), "min": min(vals), "max": max(vals), "count": len(vals)}
    return summary


def statistics_mean(vals: List[float]) -> float:
    import statistics as _st
    return _st.mean(vals) if vals else 0.0
