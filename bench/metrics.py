"""Metrics computation, aggregation, and report generation for D-Resume eval."""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class IntentMetrics:
    intent_class: str = ""
    total: int = 0
    passed: int = 0
    avg_response_ms: float = 0.0
    avg_suggestions: float = 0.0
    self_check_pass_rate: float = 0.0
    chain_validity: float = 0.0

    @property
    def pass_rate(self) -> float:
        return self.passed / max(1, self.total)


@dataclass
class EvalMetrics:
    total_scenarios: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    pass_rate: float = 0.0
    intent_accuracy: float = 0.0
    chain_validity: float = 0.0
    self_check_pass_rate: float = 0.0
    avg_response_ms: float = 0.0
    p50_response_ms: float = 0.0
    p95_response_ms: float = 0.0
    avg_suggestions_per_turn: float = 0.0
    actionability_distribution: Dict[str, float] = field(default_factory=dict)
    intent_distribution: Dict[str, int] = field(default_factory=dict)
    by_intent: List[IntentMetrics] = field(default_factory=list)
    run_label: str = ""
    log_count: int = 0
    compared_to: Optional[str] = None
    regressions: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)


def load_logs(log_dir: Path) -> List[Dict[str, Any]]:
    """Load JSON eval logs from a directory, recursing into subdirs."""
    logs: List[Dict[str, Any]] = []
    for path in sorted(log_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "scenario" in data:
                logs.append(data)
        except (json.JSONDecodeError, KeyError):
            pass
    for subdir in sorted(log_dir.iterdir()):
        if subdir.is_dir():
            logs.extend(load_logs(subdir))
    return logs


def compute_metrics(logs: List[Dict[str, Any]], run_label: str = "") -> EvalMetrics:
    if not logs:
        return EvalMetrics(run_label=run_label)
    m = EvalMetrics(run_label=run_label, log_count=len(logs))
    total = len(logs)
    passed = sum(1 for l in logs if l.get("all_assertions_passed", False))
    errors = sum(1 for l in logs if l.get("error"))
    m.total_scenarios = total
    m.passed = passed
    m.failed = total - passed - errors
    m.errors = errors
    m.pass_rate = passed / max(1, total)

    # Intent accuracy
    ir = [l["assertions"]["intent_matches_expected"] for l in logs
          if "intent_matches_expected" in l.get("assertions", {})]
    m.intent_accuracy = sum(ir) / max(1, len(ir))

    # Chain validity
    cr = [l["assertions"]["chain_ends_with_compose"] for l in logs
          if "chain_ends_with_compose" in l.get("assertions", {})]
    m.chain_validity = sum(cr) / max(1, len(cr))

    # Self-check
    sc = []
    for l in logs:
        v = l.get("turn", {}).get("self_check", {}).get("verdict", "")
        if v:
            sc.append(1 if v == "pass" else 0)
    m.self_check_pass_rate = sum(sc) / max(1, len(sc))

    # Timing
    durations = sorted([l.get("turn", {}).get("duration_ms", 0) for l in logs
                        if l.get("turn", {}).get("duration_ms", 0) > 0])
    if durations:
        m.avg_response_ms = statistics.mean(durations)
        m.p50_response_ms = durations[len(durations) // 2]
        m.p95_response_ms = durations[min(int(len(durations) * 0.95), len(durations) - 1)]

    # Suggestions
    suggs = [l.get("turn", {}).get("suggestion_count", 0) for l in logs]
    m.avg_suggestions_per_turn = statistics.mean(suggs) if suggs else 0.0

    # Actionability
    apply_c = [l.get("turn", {}).get("actionability_summary", {}).get("apply_ready", 0) for l in logs]
    conf_c = [l.get("turn", {}).get("actionability_summary", {}).get("confirm_required", 0) for l in logs]
    m.actionability_distribution = {
        "avg_apply_ready": statistics.mean(apply_c) if apply_c else 0.0,
        "avg_confirm_required": statistics.mean(conf_c) if conf_c else 0.0,
    }

    # Per-intent
    groups: Dict[str, List[Dict]] = {}
    for l in logs:
        ic = l.get("turn", {}).get("intent_state", {}).get("intent_class", "unknown")
        groups.setdefault(ic, []).append(l)
        m.intent_distribution[ic] = m.intent_distribution.get(ic, 0) + 1
    for ic, group in groups.items():
        im = IntentMetrics(intent_class=ic, total=len(group))
        im.passed = sum(1 for l in group if l.get("all_assertions_passed", False))
        im.avg_response_ms = statistics.mean([l.get("turn", {}).get("duration_ms", 0) for l in group])
        im.avg_suggestions = statistics.mean([l.get("turn", {}).get("suggestion_count", 0) for l in group])
        scv = [1 if l.get("turn", {}).get("self_check", {}).get("verdict", "") == "pass" else 0
               for l in group if l.get("turn", {}).get("self_check", {}).get("verdict", "")]
        im.self_check_pass_rate = sum(scv) / max(1, len(scv))
        im.chain_validity = sum(1 for l in group
                                if l.get("assertions", {}).get("chain_ends_with_compose", False)) / max(1, len(group))
        m.by_intent.append(im)
    return m


def detect_regressions(current: EvalMetrics, baseline: EvalMetrics, threshold: float = 0.05) -> EvalMetrics:
    current.compared_to = baseline.run_label
    delta = baseline.pass_rate - current.pass_rate
    if delta > threshold:
        current.regressions.append(f"Overall pass rate dropped {delta:.1%} ({baseline.pass_rate:.1%} -> {current.pass_rate:.1%})")
    elif delta < -threshold:
        current.improvements.append(f"Overall pass rate improved {abs(delta):.1%} ({baseline.pass_rate:.1%} -> {current.pass_rate:.1%})")

    bl_map = {im.intent_class: im for im in baseline.by_intent}
    for im in current.by_intent:
        bl = bl_map.get(im.intent_class)
        if bl and bl.total > 0:
            d = bl.pass_rate - im.pass_rate
            if d > threshold:
                current.regressions.append(f"{im.intent_class}: {bl.pass_rate:.1%} -> {im.pass_rate:.1%} ({d:+.1%})")
            elif d < -threshold:
                current.improvements.append(f"{im.intent_class}: {bl.pass_rate:.1%} -> {im.pass_rate:.1%} ({d:+.1%})")

    if baseline.avg_response_ms > 0 and current.avg_response_ms > baseline.avg_response_ms * 1.2:
        pct = (current.avg_response_ms - baseline.avg_response_ms) / baseline.avg_response_ms
        current.regressions.append(f"Response time: {baseline.avg_response_ms:.0f}ms -> {current.avg_response_ms:.0f}ms ({pct:+.0%})")
    return current


def load_and_compute(log_dir: Path, run_label: str = "") -> EvalMetrics:
    search = log_dir / "logs" if (log_dir / "logs").exists() else log_dir
    return compute_metrics(load_logs(search), run_label=run_label or str(log_dir.name))


def format_metrics_summary(m: EvalMetrics) -> str:
    lines = [
        f"=== {m.run_label or 'Eval Summary'} ===",
        f"Scenarios: {m.total_scenarios} total | {m.passed} passed | {m.failed} failed | {m.errors} errors",
        f"Pass Rate: {m.pass_rate:.1%}",
        f"Intent Accuracy: {m.intent_accuracy:.1%}  |  Chain Validity: {m.chain_validity:.1%}  |  Self-Check Pass: {m.self_check_pass_rate:.1%}",
        f"Response: avg={m.avg_response_ms:.0f}ms | p50={m.p50_response_ms:.0f}ms | p95={m.p95_response_ms:.0f}ms",
        f"Avg Suggestions/Turn: {m.avg_suggestions_per_turn:.1f}",
        f"Actionability: apply_ready={m.actionability_distribution.get('avg_apply_ready', 0):.1f} | confirm_required={m.actionability_distribution.get('avg_confirm_required', 0):.1f}",
    ]
    if m.regressions:
        lines.append("\n--- REGRESSIONS ---")
        for r in m.regressions:
            lines.append(f"  ! {r}")
    if m.improvements:
        lines.append("\n--- IMPROVEMENTS ---")
        for r in m.improvements:
            lines.append(f"  + {r}")
    if m.by_intent:
        lines.append(f"\n{'Intent':<20} {'Total':>5} {'Pass':>5} {'Rate':>7} {'Avg ms':>8} {'Suggest':>7}")
        for im in sorted(m.by_intent, key=lambda x: x.pass_rate):
            lines.append(f"{im.intent_class:<20} {im.total:>5} {im.passed:>5} {im.pass_rate:>6.0%} {im.avg_response_ms:>7.0f} {im.avg_suggestions:>6.1f}")
    return "\n".join(lines)


def metrics_to_dict(m: EvalMetrics) -> Dict[str, Any]:
    return {
        "run_label": m.run_label, "log_count": m.log_count,
        "total_scenarios": m.total_scenarios, "passed": m.passed, "failed": m.failed, "errors": m.errors,
        "pass_rate": m.pass_rate, "intent_accuracy": m.intent_accuracy, "chain_validity": m.chain_validity,
        "self_check_pass_rate": m.self_check_pass_rate,
        "avg_response_ms": m.avg_response_ms, "p50_response_ms": m.p50_response_ms, "p95_response_ms": m.p95_response_ms,
        "avg_suggestions_per_turn": m.avg_suggestions_per_turn,
        "actionability_distribution": m.actionability_distribution,
        "intent_distribution": m.intent_distribution,
        "by_intent": [{"intent_class": im.intent_class, "total": im.total, "passed": im.passed,
                       "pass_rate": im.pass_rate, "avg_response_ms": im.avg_response_ms,
                       "avg_suggestions": im.avg_suggestions, "self_check_pass_rate": im.self_check_pass_rate}
                      for im in m.by_intent],
        "compared_to": m.compared_to, "regressions": m.regressions, "improvements": m.improvements,
    }


def generate_reports(run_dir: Path, baseline_dir: Optional[Path] = None) -> Dict[str, Path]:
    """Generate summary.json, summary.md, content_diff.json inside run_dir."""
    logs_dir = run_dir / "logs"
    if not logs_dir.exists():
        return {}
    logs = load_logs(logs_dir)
    metrics = compute_metrics(logs, run_label=str(run_dir.name))

    if baseline_dir:
        bl_search = baseline_dir / "logs" if (baseline_dir / "logs").exists() else baseline_dir
        bl = compute_metrics(load_logs(bl_search), run_label=str(baseline_dir.name))
        metrics = detect_regressions(metrics, bl)

    paths = {}
    p = run_dir / "summary.json"
    p.write_text(json.dumps(metrics_to_dict(metrics), ensure_ascii=False, indent=2), encoding="utf-8")
    paths["summary_json"] = p

    md = _build_summary_md(metrics, run_dir)
    p = run_dir / "summary.md"
    p.write_text(md, encoding="utf-8")
    paths["summary_md"] = p

    diff = _collect_diffs(logs)
    p = run_dir / "content_diff.json"
    p.write_text(json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["content_diff"] = p

    return paths


def _collect_diffs(logs: List[Dict]) -> Dict[str, Any]:
    diffs, suggs = [], []
    for l in logs:
        nm = l.get("scenario", {}).get("name", "")
        cd = l.get("content_diff")
        if cd and cd.get("has_changes"):
            diffs.append({"scenario": nm, "sections_changed": cd.get("sections_changed", {}),
                          "total_changed_fields": cd.get("total_changed_fields", 0),
                          "changed_paths": cd.get("changed_paths", [])})
        sd = l.get("suggestion_diff")
        if sd and sd.get("suggestions_with_changes", 0) > 0:
            suggs.append({"scenario": nm, "total_suggestions": sd.get("total_suggestions", 0),
                          "suggestions_with_changes": sd.get("suggestions_with_changes", 0),
                          "items": sd.get("items", [])})
    return {"total_scenarios_with_changes": len(diffs), "scenarios": diffs,
            "total_scenarios_with_suggestions": len(suggs), "suggestion_scenarios": suggs}


def _build_summary_md(m: EvalMetrics, run_dir: Path) -> str:
    lines = [
        f"# D-Resume Eval Summary",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"Source: `{run_dir}`", "",
        "## Overall",
        f"| Metric | Value |", "|--------|-------|",
        f"| Total Scenarios | {m.total_scenarios} |",
        f"| Passed | {m.passed} | | Failed | {m.failed} | | Errors | {m.errors} |",
        f"| **Pass Rate** | **{m.pass_rate:.1%}** |",
        f"| Intent Accuracy | {m.intent_accuracy:.1%} |",
        f"| Chain Validity | {m.chain_validity:.1%} |",
        f"| Self-Check Pass | {m.self_check_pass_rate:.1%} |", "",
        "## Performance",
        f"| Metric | Value |", "|--------|-------|",
        f"| Avg Response | {m.avg_response_ms:.0f}ms |",
        f"| P50 Response | {m.p50_response_ms:.0f}ms |",
        f"| P95 Response | {m.p95_response_ms:.0f}ms |",
        f"| Avg Suggestions/Turn | {m.avg_suggestions_per_turn:.1f} |", "",
    ]
    if m.regressions:
        lines.append("## Regressions")
        for r in m.regressions:
            lines.append(f"- :warning: {r}")
        lines.append("")
    if m.improvements:
        lines.append("## Improvements")
        for r in m.improvements:
            lines.append(f"- :white_check_mark: {r}")
        lines.append("")
    if m.by_intent:
        lines.append("## By Intent Class")
        lines.append("| Intent | Total | Pass | Rate | Avg ms | Avg Sugg |")
        lines.append("|--------|-------|------|------|--------|----------|")
        for im in sorted(m.by_intent, key=lambda x: x.pass_rate):
            lines.append(f"| {im.intent_class} | {im.total} | {im.passed} | {im.pass_rate:.0%} | {im.avg_response_ms:.0f} | {im.avg_suggestions:.1f} |")
        lines.append("")
    return "\n".join(lines)
