"""Self-iterate workflow: baseline -> diagnose -> verify."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from bench.metrics import load_logs, compute_metrics, detect_regressions, format_metrics_summary
from bench.tasks import generate_tasks

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ITER_LOG = PROJECT_ROOT / "outputs" / "iterations" / "iteration_log.json"


def _load_iteration_log() -> Dict[str, Any]:
    if ITER_LOG.exists():
        return json.loads(ITER_LOG.read_text(encoding="utf-8"))
    return {"iterations": [], "last_baseline": None}


def _save(log: Dict[str, Any]) -> None:
    ITER_LOG.parent.mkdir(parents=True, exist_ok=True)
    ITER_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


def _latest_run(evals_dir: Path | None = None) -> Path | None:
    d = evals_dir or (PROJECT_ROOT / "outputs" / "agent_eval")
    if not d.exists():
        return None
    runs = sorted([x for x in d.iterdir() if x.is_dir() and (x / "logs").exists()],
                  key=lambda x: x.stat().st_mtime, reverse=True)
    return runs[0] if runs else None


def _run_agent(args: List[str]) -> int:
    cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "agent_eval.py")] + args
    return subprocess.call(cmd, cwd=str(PROJECT_ROOT))


def cmd_baseline(base_url: str, concurrency: int = 4) -> int:
    print("[iterate] Establishing baseline...")
    rc = _run_agent(["--base-url", base_url, "-j", str(concurrency), "--output-format", "json"])
    if rc not in (0, 1):
        return rc
    latest = _latest_run()
    if not latest:
        return 1
    ilog = _load_iteration_log()
    ilog["last_baseline"] = str(latest)
    _save(ilog)
    _print_scorecard(latest)
    print(f"\n[iterate] Baseline: {latest}")
    return 0


def cmd_diagnose() -> int:
    latest = _latest_run()
    if not latest:
        print("[iterate] No eval runs. Run 'bench eval' first.")
        return 1
    print(f"[iterate] Diagnosing: {latest}")
    _print_scorecard(latest)
    tasks_path = generate_tasks(latest)
    print(f"\n[iterate] Fix tasks: {tasks_path}")
    return 0


def cmd_verify(base_url: str, concurrency: int = 4, regression: bool = False, resume_fixtures: bool = False) -> int:
    ilog = _load_iteration_log()
    bl_path = ilog.get("last_baseline")
    if not bl_path:
        print("[iterate] No baseline. Run 'bench eval' first.")
        return 1
    bl_dir = Path(bl_path)
    if not bl_dir.exists():
        print(f"[iterate] Baseline not found: {bl_dir}")
        return 1

    print(f"[iterate] Baseline: {bl_dir}")
    bl_logs = load_logs(bl_dir / "logs" if (bl_dir / "logs").exists() else bl_dir)
    bl_metrics = compute_metrics(bl_logs, run_label="baseline")
    print(f"  Pass Rate: {bl_metrics.pass_rate:.1%} ({bl_metrics.passed}/{bl_metrics.total_scenarios})")

    agent_args = ["--base-url", base_url, "-j", str(concurrency), "--output-format", "json"]
    if regression:
        agent_args.append("--regression")
    if resume_fixtures:
        agent_args.append("--resume-fixtures")
    rc = _run_agent(agent_args)
    if rc not in (0, 1):
        return rc

    latest = _latest_run()
    if not latest:
        return 1
    cur_search = latest / "logs" if (latest / "logs").exists() else latest
    cur_logs = load_logs(cur_search)
    cur_metrics = compute_metrics(cur_logs, run_label="current")
    cur_metrics = detect_regressions(cur_metrics, bl_metrics)

    print("\n" + format_metrics_summary(cur_metrics))
    print(f"\nRun: {latest}\nBaseline: {bl_dir}")

    iteration = {"iteration": len(ilog["iterations"]) + 1,
                 "timestamp": str(latest.name),
                 "baseline_pass_rate": bl_metrics.pass_rate, "new_pass_rate": cur_metrics.pass_rate,
                 "regressions": cur_metrics.regressions, "improvements": cur_metrics.improvements,
                 "baseline_dir": str(bl_dir), "verify_dir": str(latest)}
    ilog["iterations"].append(iteration)
    _save(ilog)
    generate_tasks(latest)

    if cur_metrics.pass_rate < bl_metrics.pass_rate - 0.05:
        print("\n[iterate] VERDICT: REGRESSION")
        return 1
    elif cur_metrics.pass_rate > bl_metrics.pass_rate + 0.02:
        print("\n[iterate] VERDICT: IMPROVED. New baseline.")
        ilog["last_baseline"] = str(latest)
        _save(ilog)
        return 0
    print("\n[iterate] VERDICT: No significant change")
    return 0


def cmd_explain(scenario: str) -> int:
    latest = _latest_run()
    if not latest:
        return 1
    matches = list((latest / "logs").rglob(f"*{scenario}*.json"))
    if not matches:
        print(f"[iterate] No log for '{scenario}'")
        return 1

    log = json.loads(matches[0].read_text(encoding="utf-8"))
    sd = log.get("scenario", {})
    turn = log.get("turn", {})
    assertions = log.get("assertions", {})
    passed = log.get("all_assertions_passed", False)

    print(f"\n{'PASS' if passed else 'FAIL'}: {sd.get('name', matches[0].stem)}")
    print("=" * 60)
    print(f"Message:  {sd.get('message', '')}")
    print(f"Expected: intent={sd.get('expected_intent', '')}, scope={sd.get('expected_scope', '') or '(any)'}")
    print(f"Actual:   intent={turn.get('intent_state', {}).get('intent_class', '?')}, "
          f"chain={'->'.join(turn.get('tool_chain', []))}")
    print(f"Self-check: {turn.get('self_check', {}).get('verdict', '?')}")
    print(f"Suggestions: {turn.get('suggestion_count', 0)} total, "
          f"{turn.get('actionability_summary', {}).get('apply_ready', 0)} apply_ready, "
          f"{turn.get('actionability_summary', {}).get('confirm_required', 0)} confirm_required")

    if not passed:
        print(f"\nFailed:")
        for rule, val in assertions.items():
            if not val:
                print(f"  X {rule}")

    sugg = log.get("suggestion_diff", {})
    if sugg.get("items"):
        print(f"\nSuggestion diff ({len(sugg['items'])} items):")
        for item in sugg["items"][:3]:
            print(f"  [{item['actionability']}] {item['path']}")
            print(f"    - {item['before'][:100]}")
            print(f"    + {item['after'][:100]}")
    return 0


def _print_scorecard(run_dir: Path) -> None:
    search = run_dir / "logs" if (run_dir / "logs").exists() else run_dir
    logs = load_logs(search)
    if logs:
        print(format_metrics_summary(compute_metrics(logs, run_label=str(run_dir.name))))
