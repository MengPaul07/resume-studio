#!/usr/bin/env python3
"""D-Resume Bench CLI — interactive-first eval + iterate entry point.

Run without arguments for interactive mode.
Use flags (--quick, --intent, etc.) for scripting / CI.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import List, Tuple, Dict, Optional

from bench.term import (
    PASS, FAIL, WARN, INFO, ARROW,
    bold, dim, green, red, yellow, cyan, blue, gray, white,
    tag, header, divider, confirm, select, multi_select,
    input_text, LiveCounter, box, table, strip_ansi,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EVAL_DIR = PROJECT_ROOT / "outputs" / "agent_eval"
DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/v1"


# ── Arg parser (non-interactive / CI mode) ──────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="D-Resume Benchmark CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Commands:
  bench                  Interactive mode (default)
  bench eval             Run benchmark (interactive if no flags)
  bench list             List fixtures, scenarios, intents
  bench status           Check server health
  bench compare R1 R2    Compare two runs
  bench explain [name]   Explain a scenario (interactive if no name)
  bench tasks [dir]      Re-generate TASKS.md
  bench serve [dir]      Start HTTP dashboard for a run""")
    sub = p.add_subparsers(dest="cmd", help="Commands")

    ev = sub.add_parser("eval", help="Run benchmark suite")
    ev.add_argument("--quick", action="store_true", help="Regression scenarios only")
    ev.add_argument("--resume", default="", help="Single resume fixture name")
    ev.add_argument("--resume-fixtures", action="store_true", help="Use ALL resume fixtures (cross-resume)")
    ev.add_argument("--sample", type=int, default=0, metavar="N", help="Randomly sample N resumes")
    ev.add_argument("--intent", default="", help="Specific intent class filter")
    ev.add_argument("--scenario", default="", help="Single scenario name")
    ev.add_argument("--skip-judge", action="store_true", help="Skip LLM quality judge")
    ev.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    ev.add_argument("-j", "--concurrency", type=int, default=4)
    ev.add_argument("--output-dir", default=str(DEFAULT_EVAL_DIR), help="Output root")

    sub.add_parser("list", help="List fixtures, scenarios, intents")

    sub.add_parser("status", help="Check server health")

    cmp = sub.add_parser("compare", help="Compare two eval runs")
    cmp.add_argument("run1", nargs="?", default="")
    cmp.add_argument("run2", nargs="?", default="")

    exp = sub.add_parser("explain", help="Explain a failure")
    exp.add_argument("scenario", nargs="?", default="")

    tsk = sub.add_parser("tasks", help="Re-generate TASKS.md")
    tsk.add_argument("run_dir", nargs="?", default="")

    srv = sub.add_parser("serve", help="Start HTTP dashboard for a run")
    srv.add_argument("run_dir", nargs="?", default="")
    srv.add_argument("--port", type=int, default=8080)
    return p


# ── Main dispatcher ──────────────────────────────────────────────────────────

def main(argv: list[str] | None = None):
    args = build_parser().parse_args(argv)

    if args.cmd is None:
        return _interactive_main_menu()
    elif args.cmd == "eval":
        return _cmd_eval(args)
    elif args.cmd == "list":
        return _cmd_list()
    elif args.cmd == "status":
        return _cmd_status(args)
    elif args.cmd == "compare":
        return _cmd_compare(args)
    elif args.cmd == "explain":
        return _cmd_explain(args)
    elif args.cmd == "tasks":
        return _cmd_tasks(args)
    elif args.cmd == "serve":
        return _cmd_serve(args)
    return 0


# ── Interactive main menu ────────────────────────────────────────────────────

def _interactive_main_menu() -> int:
    print(header("D-Resume Benchmark"))
    print(f"\n  {bold('bench')} — AI resume agent evaluation toolkit")
    print(f"  {dim('Run without arguments for interactive mode')}")
    print()

    choices = [
        f"{green('▶')} Run evaluation",
        f"{blue('📋')} List fixtures & scenarios",
        f"{blue('🔍')} Explain a scenario",
        f"{blue('📊')} Compare two runs",
        f"{blue('📝')} View tasks (TASKS.md)",
        f"{blue('🌐')} Start dashboard server",
        f"{dim('⚙')}  Check server status",
    ]

    while True:
        idx = select("What would you like to do?", choices, default=0)
        if idx == 0:
            return _interactive_eval()
        elif idx == 1:
            _cmd_list()
        elif idx == 2:
            _interactive_explain()
        elif idx == 3:
            _interactive_compare()
        elif idx == 4:
            _cmd_tasks_from_latest()
        elif idx == 5:
            _interactive_serve()
        elif idx == 6:
            _cmd_status(None)
        # Loop back to menu


# ── Interactive eval ─────────────────────────────────────────────────────────

def _interactive_eval(base_url: str | None = None) -> int:
    from bench.scenarios import SCENARIOS, filter_by_intent, filter_by_tag, get_by_name, filter_regression
    from bench.harness import run_eval, load_resume_fixtures
    from bench.metrics import generate_reports

    if base_url is None:
        base_url = DEFAULT_BASE_URL

    # Step 1: scenario selection
    scenario_mode = select("Select scenarios:", [
        f"All scenarios ({len(SCENARIOS)} total)",
        "Quick regression (19 scenarios)",
        "Filter by intent class",
        "Single scenario",
    ], default=0)

    if scenario_mode == 0:
        scenarios = list(SCENARIOS)
    elif scenario_mode == 1:
        scenarios = filter_regression()
    elif scenario_mode == 2:
        intents = _available_intents()
        idx = select("Which intent class?", intents)
        scenarios = filter_by_intent(intents[idx].split()[0])
        if not scenarios:
            print(f"  {red('No scenarios found')}")
            return 2
    else:
        names = sorted([s.name for s in SCENARIOS])
        choices = [f"{s.name}  {dim('─')} {dim(s.message[:60])}" for s in sorted(SCENARIOS, key=lambda x: x.name)]
        idx = select("Which scenario?", choices)
        scenarios = [sorted(SCENARIOS, key=lambda x: x.name)[idx]]

    print(f"\n  {green(str(len(scenarios)))} scenario(s) selected")

    # Step 2: resume selection
    all_fixtures = load_resume_fixtures()
    resume_mode = select("Resume mode:", [
        "Default (use built-in fallback resume)",
        "Single fixture",
        f"All fixtures ({len(all_fixtures)} total)",
        f"Random sample N from {len(all_fixtures)} fixtures",
    ], default=0)

    fixtures: Optional[List[Tuple[str, Dict]]] = None
    fixture_label = "default"

    if resume_mode == 1:
        names = [f"{name}  {dim('─')} {dim(obj.get('description','')[:55])}" for name, obj in all_fixtures]
        idx = select("Which resume fixture?", names)
        fixtures = [all_fixtures[idx]]
        fixture_label = all_fixtures[idx][0]
    elif resume_mode == 2:
        fixtures = all_fixtures
        fixture_label = f"{len(fixtures)} fixtures"
    elif resume_mode == 3:
        n_str = input_text("Sample how many?", default="3",
                           validate=lambda x: None if x.isdigit() and 1 <= int(x) <= len(all_fixtures)
                           else f"Enter 1-{len(all_fixtures)}")
        n = int(n_str)
        fixtures = random.sample(all_fixtures, n)
        fixture_label = f"{n} sampled"
        print(f"  {green('Sampled:')} {', '.join(name for name,_ in fixtures)}")

    # Step 3: concurrency
    j_str = input_text("Concurrency?", default="4",
                       validate=lambda x: None if x.isdigit() and 1 <= int(x) <= 16 else "Enter 1-16")
    concurrency = int(j_str)

    # Step 4: judge
    do_judge = len(scenarios) > 5 and not (scenario_mode == 3)
    if do_judge:
        do_judge = confirm("Run LLM quality judge after eval?", default=True)

    # Step 5: preview & confirm
    total = len(scenarios) * (len(fixtures) if fixtures else 1)
    preview = [
        f"{bold('Scenarios:')}  {len(scenarios)}",
        f"{bold('Resumes:')}    {fixture_label}",
        f"{bold('Total runs:')} {total}",
        f"{bold('Server:')}     {base_url}",
        f"{bold('Concurrency:')} {concurrency}",
        f"{bold('LLM Judge:')}  {'yes' if do_judge else 'no'}",
    ]
    print(box(preview, title="Preview"))

    if not confirm("Proceed?", default=True):
        print(f"  {dim('Cancelled')}")
        return 0

    # Step 6: run
    print(header("Running"))
    print()

    # We'll patch the harness print to use stderr for progress, stdout for results
    start_time = time.time()
    exit_code, run_dir, results = run_eval(
        base_url=base_url, scenarios=scenarios,
        output_dir=Path(DEFAULT_EVAL_DIR),
        concurrency=concurrency,
        resume_fixtures=fixtures,
    )

    elapsed = time.time() - start_time
    print(f"\n  {dim(f'Completed in {elapsed:.0f}s')}")

    # Step 7: reports
    generate_reports(run_dir)
    from bench.tasks import generate_tasks
    tasks_path = generate_tasks(run_dir)

    # Step 8: summary
    _print_run_summary(run_dir, results)

    # Step 9: judge
    if do_judge:
        print(header("LLM Quality Judge"))
        from bench.judge import judge_directory
        judge_directory(run_dir)

    print(f"\n  {INFO} Run: {dim(str(run_dir))}")
    print(f"  {INFO} Tasks: {dim(str(tasks_path))}")
    return exit_code


def _print_run_summary(run_dir: Path, results: List[Dict]) -> None:
    from bench.metrics import load_logs, compute_metrics, format_metrics_summary
    logs = load_logs(run_dir / "logs" if (run_dir / "logs").exists() else run_dir)
    if logs:
        m = compute_metrics(logs, run_label=str(run_dir.name))
        passed = m.passed
        total = m.total_scenarios
        rate = m.pass_rate
        color = green if rate >= 0.95 else yellow if rate >= 0.85 else red
        lines = [
            f"{bold('Pass Rate:')}  {color(f'{rate:.1%}')}  ({passed}/{total})",
            f"{bold('Chain:')}     {m.chain_validity:.1%}",
            f"{bold('Self-Check:')} {m.self_check_pass_rate:.1%}",
            f"{bold('Avg Time:')}  {m.avg_response_ms:.0f}ms",
            f"{bold('Suggestions:')} {m.avg_suggestions_per_turn:.1f}/turn",
        ]
        if m.failed > 0:
            lines.append(f"{bold('Failed:')}   {red(str(m.failed))}")
        print(box(lines, title="Results"))


# ── List command ─────────────────────────────────────────────────────────────

def _cmd_list() -> int:
    from bench.harness import load_resume_fixtures
    from bench.scenarios import SCENARIOS

    print(header("Resume Fixtures"))
    fixtures = load_resume_fixtures()
    rows = []
    for name, obj in fixtures:
        diff = obj.get("difficulty", "?")
        color = red if diff == "hard" else yellow if diff == "medium" else green
        rows.append([f"  {cyan(name)}", color(diff), dim(obj.get("description", "")[:55])])
    print(table(["Name", "Difficulty", "Description"], rows))
    print(f"\n  {dim(f'{len(fixtures)} fixtures in tests/fixtures/resumes/')}")

    print(header("Scenarios"))
    intents = {}
    for s in SCENARIOS:
        intents.setdefault(s.expected_intent, []).append(s)
    for ic in sorted(intents):
        print(f"\n  {bold(ic)} ({len(intents[ic])})")
        for s in sorted(intents[ic], key=lambda x: x.name):
            print(f"    {dim('•')} {cyan(s.name):30s} {dim(s.message[:55])}")

    print(f"\n  {dim(f'{len(SCENARIOS)} scenarios total')}")
    return 0


def _available_intents() -> List[str]:
    from bench.scenarios import SCENARIOS
    counts: Dict[str, int] = {}
    for s in SCENARIOS:
        counts[s.expected_intent] = counts.get(s.expected_intent, 0) + 1
    return [f"{ic}  {dim(f'({n} scenarios)')}" for ic, n in sorted(counts.items())]


# ── Status command ───────────────────────────────────────────────────────────

def _cmd_status(args) -> int:
    import urllib.request
    import urllib.error

    base_url = getattr(args, 'base_url', DEFAULT_BASE_URL) if args else DEFAULT_BASE_URL
    health_url = f"{base_url}/health"

    print(header("Server Status"))
    print(f"  URL: {dim(base_url)}")

    try:
        req = urllib.request.Request(health_url)
        urllib.request.urlopen(req, timeout=5)
        print(f"  Status: {green('reachable')} {PASS}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # /health might not exist, try the root
            try:
                req = urllib.request.Request(f"{base_url}/docs")
                urllib.request.urlopen(req, timeout=5)
                print(f"  Status: {green('reachable')} {PASS}  {dim('(/health 404 but /docs ok)')}")
            except Exception:
                print(f"  Status: {yellow('partially reachable')} {WARN}  ({e})")
        else:
            print(f"  Status: {red('error')} {FAIL}  (HTTP {e.code})")
    except Exception as e:
        print(f"  Status: {red('unreachable')} {FAIL}")
        print(f"  {dim(str(e))}")
        print(f"\n  {INFO} Start the server:")
        print(f"    {cyan('.venv/Scripts/python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000')}")
        return 1
    return 0


# ── Compare command ──────────────────────────────────────────────────────────

def _interactive_compare() -> int:
    runs = _list_runs()
    if len(runs) < 2:
        print(f"  {yellow('Need at least 2 runs to compare')}")
        return 1

    print(header("Compare Runs"))
    idx1 = select("Baseline (old):", [f"{r.name}  {dim(_run_stats(r))}" for r in runs])
    idx2 = select("Current (new):", [f"{r.name}  {dim(_run_stats(r))}" for r in runs],
                  default=len(runs) - 1)

    return _do_compare(runs[idx1], runs[idx2])


def _cmd_compare(args) -> int:
    from bench.metrics import load_logs, compute_metrics, detect_regressions, format_metrics_summary

    if not args.run1:
        return _interactive_compare()

    r1, r2 = Path(args.run1), Path(args.run2)
    if not r1.exists():
        print(f"{red('Not found:')} {r1}")
        return 1
    if not r2.exists():
        print(f"{red('Not found:')} {r2}")
        return 1
    return _do_compare(r1, r2)


def _do_compare(r1: Path, r2: Path) -> int:
    from bench.metrics import load_logs, compute_metrics, detect_regressions, format_metrics_summary

    m1 = compute_metrics(load_logs(r1 / "logs" if (r1 / "logs").exists() else r1), run_label=r1.name)
    m2 = compute_metrics(load_logs(r2 / "logs" if (r2 / "logs").exists() else r2), run_label=r2.name)
    m2 = detect_regressions(m2, m1)

    print(header(f"Baseline: {r1.name}"))
    print(format_metrics_summary(m1))
    print(header(f"Current: {r2.name}"))
    print(format_metrics_summary(m2))

    if m2.regressions:
        print(f"\n  {red('▼ REGRESSIONS:')}")
        for r in m2.regressions:
            print(f"    {FAIL} {r}")
    if m2.improvements:
        print(f"\n  {green('▲ IMPROVEMENTS:')}")
        for r in m2.improvements:
            print(f"    {PASS} {r}")
    if not m2.regressions and not m2.improvements:
        print(f"\n  {dim('No significant change')}")

    comp = {"run1": {"label": m1.run_label, "pass_rate": m1.pass_rate},
            "run2": {"label": m2.run_label, "pass_rate": m2.pass_rate},
            "regressions": m2.regressions, "improvements": m2.improvements}
    cp = r2 / "compare.json"
    cp.write_text(json.dumps(comp, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if not m2.regressions else 1


# ── Explain command ──────────────────────────────────────────────────────────

def _interactive_explain() -> int:
    from bench.scenarios import SCENARIOS

    run = _pick_run("Select a run:")
    if not run:
        return 1

    # Find failed scenarios in this run
    from bench.metrics import load_logs
    logs = load_logs(run / "logs" if (run / "logs").exists() else run)
    failed = [l for l in logs if not l.get("all_assertions_passed") and not l.get("error")]
    choices = []
    for l in (failed or logs):
        name = l.get("scenario", {}).get("name", l.get("name", "?"))
        pf = FAIL if not l.get("all_assertions_passed") else PASS
        choices.append(f"{pf} {cyan(name)}")
    idx = select("Which scenario?", choices)
    return _do_explain(run, (failed or logs)[idx].get("scenario", {}).get("name", ""))


def _cmd_explain(args) -> int:
    if not args.scenario:
        return _interactive_explain()
    return _do_explain(_latest_run(), args.scenario)


def _do_explain(run_dir: Path, scenario: str) -> int:
    from bench.iterate import cmd_explain
    import os
    # Temporarily override _latest_run to return our chosen dir
    old_fn = None
    try:
        from bench import iterate
        old_fn = iterate._latest_run
        iterate._latest_run = lambda evals_dir=None: run_dir
    except Exception:
        pass

    try:
        return cmd_explain(scenario)
    finally:
        if old_fn:
            try:
                from bench import iterate
                iterate._latest_run = old_fn
            except Exception:
                pass


# ── Tasks command ────────────────────────────────────────────────────────────

def _cmd_tasks(args) -> int:
    from bench.tasks import generate_tasks
    rd = Path(args.run_dir) if args.run_dir else _latest_run()
    if not rd:
        print(f"  {red('No run found.')}")
        return 1
    path = generate_tasks(rd)
    print(f"  {PASS} TASKS.md: {dim(str(path))}")
    return 0


def _cmd_tasks_from_latest() -> int:
    from bench.tasks import generate_tasks
    rd = _latest_run()
    if not rd:
        print(f"  {red('No run found. Run eval first.')}")
        return 1
    path = generate_tasks(rd)
    print(f"  {PASS} TASKS.md: {dim(str(path))}")
    return 0


# ── Serve command ────────────────────────────────────────────────────────────

def _interactive_serve() -> int:
    run = _pick_run("Select a run to serve:")
    if not run:
        return 1
    port = input_text("Port?", default="8080",
                      validate=lambda x: None if x.isdigit() and 1024 <= int(x) <= 65535 else "Enter 1024-65535")
    return _cmd_serve_impl(run, int(port))


def _cmd_serve(args) -> int:
    rd = Path(args.run_dir) if args.run_dir else _latest_run()
    if not rd:
        print(f"  {red('No run found.')}")
        return 1
    return _cmd_serve_impl(rd, args.port)


def _cmd_serve_impl(run_dir: Path, port: int) -> int:
    import http.server
    import socketserver
    import webbrowser
    import os

    os.chdir(str(run_dir))
    handler = http.server.SimpleHTTPRequestHandler

    print(f"\n  {INFO} Serving: {dim(str(run_dir))}")
    print(f"  {INFO} Dashboard: {cyan(f'http://127.0.0.1:{port}/dashboard.html')}")
    print(f"  {INFO} Summary: {cyan(f'http://127.0.0.1:{port}/summary.md')}")
    print(f"  {dim('Press Ctrl+C to stop')}")

    try:
        webbrowser.open(f"http://127.0.0.1:{port}/dashboard.html")
    except Exception:
        pass

    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n  {dim('Stopped')}")
    return 0


# ── Non-interactive eval (flag mode) ─────────────────────────────────────────

def _cmd_eval(args) -> int:
    from bench.scenarios import SCENARIOS, filter_by_intent, filter_by_tag, get_by_name, filter_regression
    from bench.harness import run_eval, load_resume_fixtures
    from bench.metrics import generate_reports

    # Detect if this is a scripted/non-interactive call
    has_flags = args.quick or args.intent or args.scenario or args.resume or args.resume_fixtures

    if not has_flags:
        return _interactive_eval(base_url=args.base_url)

    # Non-interactive / CI mode
    if args.scenario:
        s = get_by_name(args.scenario)
        if not s:
            all_names = [sc.name for sc in SCENARIOS]
            close = _closest_match(args.scenario, all_names)
            hint = f" Did you mean '{close}'?" if close else ""
            print(f"{red('Unknown:')} {args.scenario}.{hint}")
            print(f"  Available: {', '.join(sorted(all_names)[:20])}")
            return 2
        scenarios = [s]
    elif args.quick:
        scenarios = filter_regression()
        print(f"Quick mode: {len(scenarios)} regression scenarios")
    elif args.intent:
        scenarios = filter_by_intent(args.intent)
        if not scenarios:
            intents = _available_intents()
            print(f"{red('No intent:')} {args.intent}")
            print(f"  Available: {', '.join(i.split()[0] for i in intents)}")
            return 2
        print(f"Intent filter: {args.intent} -> {len(scenarios)} scenarios")
    else:
        scenarios = list(SCENARIOS)

    fixtures = None
    if args.resume:
        all_fixtures = load_resume_fixtures()
        fixtures = [(n, o) for n, o in all_fixtures if n == args.resume]
        if not fixtures:
            names = [n for n, _ in all_fixtures]
            close = _closest_match(args.resume, names)
            hint = f" Did you mean '{close}'?" if close else ""
            print(f"{red('Not found:')} {args.resume}.{hint}")
            print(f"  Available: {', '.join(names)}")
            return 2
    elif args.resume_fixtures:
        fixtures = load_resume_fixtures()
        if args.sample > 0 and args.sample < len(fixtures):
            fixtures = random.sample(fixtures, args.sample)
            print(f"Sampled {args.sample}/{len(load_resume_fixtures())} fixture(s): {', '.join(n for n,_ in fixtures)}")
        else:
            print(f"Loaded {len(fixtures)} resume fixture(s)")

    label = (f" x resume={args.resume}" if args.resume else
             f" x {len(fixtures)} resumes" if fixtures else "")
    print(f"Running {len(scenarios)} scenario(s){label}")

    exit_code, run_dir, results = run_eval(
        base_url=args.base_url, scenarios=scenarios,
        output_dir=Path(args.output_dir),
        concurrency=args.concurrency,
        resume_fixtures=fixtures,
    )

    generate_reports(run_dir)
    from bench.tasks import generate_tasks
    generate_tasks(run_dir)

    if not args.skip_judge and not args.quick:
        print("\n=== LLM Quality Judge ===")
        from bench.judge import judge_directory
        judge_directory(run_dir)

    return exit_code


# ── Helpers ──────────────────────────────────────────────────────────────────

def _latest_run() -> Path | None:
    d = DEFAULT_EVAL_DIR
    if not d.exists():
        return None
    runs = sorted([x for x in d.iterdir() if x.is_dir() and (x / "logs").exists()],
                  key=lambda x: x.stat().st_mtime, reverse=True)
    return runs[0] if runs else None


def _list_runs() -> List[Path]:
    d = DEFAULT_EVAL_DIR
    if not d.exists():
        return []
    return sorted([x for x in d.iterdir() if x.is_dir() and (x / "logs").exists()],
                  key=lambda x: x.stat().st_mtime, reverse=True)


def _pick_run(prompt: str = "Select a run:") -> Path | None:
    runs = _list_runs()
    if not runs:
        print(f"  {yellow('No eval runs found')}")
        return None
    choices = [f"{r.name}  {dim(_run_stats(r))}" for r in runs]
    idx = select(prompt, choices, default=0)
    return runs[idx]


def _run_stats(run_dir: Path) -> str:
    """Quick stats string for a run."""
    from bench.metrics import load_logs, compute_metrics
    try:
        logs = load_logs(run_dir / "logs" if (run_dir / "logs").exists() else run_dir)
        if logs:
            m = compute_metrics(logs)
            return f"{m.pass_rate:.0%} ({m.passed}/{m.total_scenarios})  {m.avg_response_ms:.0f}ms"
    except Exception:
        pass
    return "?"


def _closest_match(name: str, candidates: List[str]) -> str | None:
    """Simple edit-distance fuzzy match."""
    best, best_dist = None, 999
    for c in candidates:
        d = _levenshtein(name, c)
        if d < best_dist and d <= 3:
            best, best_dist = c, d
    return best


def _levenshtein(a: str, b: str) -> int:
    m, n = len(a), len(b)
    if m == 0: return n
    if n == 0: return m
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            tmp = dp[j]
            dp[j] = prev if a[i-1] == b[j-1] else 1 + min(dp[j], dp[j-1], prev)
            prev = tmp
    return dp[n]


if __name__ == "__main__":
    sys.exit(main())
