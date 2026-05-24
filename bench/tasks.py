"""Generate AGENT_TASKS.md — machine-readable fix list for Coding Agent self-iteration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from bench.metrics import load_logs, compute_metrics


# Mapping: failed_rule → fix suggestion
RULE_TO_FIX: Dict[str, Dict[str, str]] = {
    "intent_matches_expected": {
        "file": "src/services/content_refinement_v3/agent/_planner.py",
        "func": "INTENT_RESOLVER_SYSTEM_PROMPT or _fallback_llm_call (~L63, L154)",
        "description": "IntentResolver misclassifying this input. Adjust the system prompt to clarify intent boundaries. Or strengthen the fallback LLM call with more examples.",
    },
    "chain_has_refine": {
        "file": "src/services/content_refinement_v3/agent/_planner.py or turn_runner.py",
        "func": "IntentResolver prompt (~L63) or _resolve_target_scopes",
        "description": "Chain missing propose_refine. Either (a) intent classified wrong → fix IntentResolver prompt, or (b) propose_suggest returned 0 items causing refine skip → fix _resolve_target_scopes in turn_runner.py.",
    },
    "chain_has_suggest": {
        "file": "src/services/content_refinement_v3/agent/_planner.py",
        "func": "INTENT_RESOLVER_SYSTEM_PROMPT (~L63)",
        "description": "Chain missing propose_suggest. Intent likely misclassified — check the system prompt.",
    },
    "has_confirm_required": {
        "file": "src/services/content_refinement_v3/agent/turn_runner.py",
        "func": "_is_fact_sensitive_change (~L285) or _normalize_suggestions (~L624)",
        "description": "Suggestion not marked confirm_required when it should be. Expand _is_fact_sensitive_change detection patterns (names, addresses, etc.).",
    },
    "has_apply_ready": {
        "file": "src/services/content_refinement_v3/agent/turn_runner.py",
        "func": "_visible_suggestions (~L679) or _is_format_only_candidate (~L273)",
        "description": "0 apply-ready suggestions produced. Either all filtered as format-only or all marked confirm_required. Check _is_format_only_candidate and _normalize_suggestions.",
    },
    "assistant_not_empty": {
        "file": "src/services/content_refinement_v3/agent/turn_runner.py",
        "func": "_compose_assistant_message_with_llm (~L836) or _compose_general_chat_message (~L807)",
        "description": "Assistant message empty. LLM may have returned empty or compose step failed. Check the compose functions.",
    },
    "no_mutation": {
        "file": "src/services/content_refinement_v3/agent/_planner.py",
        "func": "ChainPlanner.plan() (~L201)",
        "description": "Mutation tools present in analysis_only/general_chat. Check ChainPlanner's allow_mutation=False path.",
    },
    "chain_ends_with_compose": {
        "file": "src/services/content_refinement_v3/agent/turn_runner.py",
        "func": "run_turn_sse auto-compose fallback (~L1550)",
        "description": "Chain did not end with compose. Auto-compose should have fired — check the fallback logic.",
    },
}


def generate_tasks(run_dir: Path, output_path: Path | None = None) -> Path:
    """Read eval logs, produce TASKS.md with prioritized fix items. Returns path to TASKS.md."""
    logs_dir = run_dir / "logs" if (run_dir / "logs").exists() else run_dir
    logs = load_logs(logs_dir)
    metrics = compute_metrics(logs, run_label=str(run_dir.name))

    # Collect failures grouped by intent
    failures_by_intent: Dict[str, List[Dict]] = {}
    for l in logs:
        if l.get("all_assertions_passed"):
            continue
        ic = l.get("turn", {}).get("intent_state", {}).get("intent_class", "unknown")
        failures_by_intent.setdefault(ic, []).append(l)

    # Collect quality issues (overall < 3.5)
    quality_issues = []
    for l in logs:
        qs = l.get("quality_scores", {})
        if qs.get("overall", 5) < 3.5 and "error" not in qs:
            quality_issues.append({
                "name": l.get("scenario", {}).get("name", ""),
                "overall": qs.get("overall", 0),
                "lowest_dim": min(
                    [(d, s.get("score", 5)) for d, s in qs.get("scores", {}).items()],
                    key=lambda x: x[1],
                ) if qs.get("scores") else ("?", 0),
            })

    # Build TASKS.md
    lines = [
        "# Fix Tasks — D-Resume Benchmark",
        f"Generated: {run_dir.name}",
        f"Summary: {metrics.passed}/{metrics.total_scenarios} passed ({metrics.pass_rate:.1%})",
    ]
    if quality_issues:
        avg_q = sum(i["overall"] for i in quality_issues) / max(1, len(quality_issues))
        lines.append(f"Quality: avg {metrics_to_avg_quality(logs):.1f}/5.0 | {len(quality_issues)} scenarios below 3.5")
    lines.append("")

    task_id = 0
    for intent, items in sorted(failures_by_intent.items(), key=lambda x: len(x[1]), reverse=True):
        intent_total = sum(1 for l in logs if l.get("turn", {}).get("intent_state", {}).get("intent_class", "") == intent)
        impact = len(items) / max(1, metrics.total_scenarios)
        lines.append(f"## T{task_id + 1}: Fix {intent} failures [{impact:.0%} impact]")
        lines.append(f"Passing: {intent_total - len(items)}/{intent_total} | Scenarios affected: {', '.join(l.get('scenario', {}).get('name', '')[:40] for l in items[:5])}")
        lines.append("")

        # Aggregate failed rules across items
        rule_counts: Dict[str, int] = {}
        for item in items:
            for rule in [k for k, v in item.get("assertions", {}).items() if not v]:
                rule_counts[rule] = rule_counts.get(rule, 0) + 1

        top_rule = max(rule_counts, key=rule_counts.get) if rule_counts else ""
        fix = RULE_TO_FIX.get(top_rule, {"file": "unknown", "func": "unknown", "description": "Analyze logs manually"})
        lines.append(f"- **File**: `{fix['file']}`")
        lines.append(f"- **Function**: `{fix['func']}`")
        lines.append(f"- **Fix**: {fix['description']}")
        lines.append("")

        for item in items[:3]:
            nm = item.get("scenario", {}).get("name", "")
            msg = item.get("scenario", {}).get("message", "")[:60]
            failed = [k for k, v in item.get("assertions", {}).items() if not v]
            chain = "->".join(item.get("turn", {}).get("tool_chain", []))
            lines.append(f"  - `{nm}`: \"{msg}\" — failed {failed} — chain: {chain}")
        lines.append("")

        verify = _suggest_verify(top_rule, items[0] if items else {})
        if verify:
            lines.append(f"- **Verify**: `{verify}`")
            lines.append("")
        task_id += 1

    if quality_issues:
        lines.append(f"## T{task_id + 1}: Fix low quality responses")
        lines.append(f"Scenarios with quality < 3.5: {len(quality_issues)}")
        lines.append("")
        lines.append("- **File**: `src/services/content_refinement_v3/prompts/agent.py` or `_planner.py`")
        lines.append("- **Fix**: Improve responder prompt quality. Check if the agent provides enough detail, relevant suggestions, and concise output.")
        lines.append("")
        for qi in quality_issues[:10]:
            lines.append(f"  - `{qi['name']}`: overall={qi['overall']}, lowest={qi['lowest_dim']}")
        lines.append("")

    out = output_path or (run_dir / "TASKS.md")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def _suggest_verify(rule: str, item: Dict) -> str:
    nm = item.get("scenario", {}).get("name", "")
    if rule in ("intent_matches_expected", "chain_has_refine", "chain_has_suggest"):
        return f"PYTHONPATH=. python bench/cli.py eval --scenario {nm}"
    if rule in ("has_confirm_required", "has_apply_ready"):
        return f"pytest tests/test_suggestion_ops.py -v -k fact_sensitive"
    if rule == "assistant_not_empty":
        return f"PYTHONPATH=. python bench/cli.py eval --scenario {nm}"
    return f"PYTHONPATH=. python bench/cli.py eval --quick"


def metrics_to_avg_quality(logs: List[Dict]) -> float:
    vals = [l.get("quality_scores", {}).get("overall", 0) for l in logs
            if l.get("quality_scores", {}).get("overall", 0) > 0]
    return sum(vals) / max(1, len(vals))
