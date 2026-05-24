"""Agent eval harness — run scenarios against live v3 agent server.

Core functions: run_eval(), run_one_scenario(), build_log(), run_assertions()
Also: resume bootstrap, content diff computation, SSE event parsing.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import time
import urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from bench.scenarios import Scenario

DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _sha1_json(data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


# ── HTTP helpers ────────────────────────────────────────────────────────

def _req(base_url: str, path: str, method: str = "GET",
         payload: Dict | None = None, timeout: int = 180) -> Tuple[Dict, int]:
    url = f"{base_url.rstrip('/')}{path}"
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url=url, method=method, data=body, headers=headers)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
            elapsed = int((time.perf_counter() - started) * 1000)
            return (json.loads(text), elapsed) if text.strip() else ({}, elapsed)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} -> {exc.code}: {raw}") from exc

def _sse(base_url: str, path: str, payload: Dict, timeout: int = 600) -> Tuple[List[Dict], Dict, int]:
    url = f"{base_url.rstrip('/')}{path}"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url=url, method="POST", data=body,
                                 headers={"Accept": "text/event-stream", "Content-Type": "application/json"})
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    total_ms = int((time.perf_counter() - started) * 1000)
    trace, final = [], {}
    seq = 0
    for chunk in raw.split("\n\n"):
        event_name, data_lines = "message", []
        for line in chunk.splitlines():
            if line.startswith("event:"): event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"): data_lines.append(line.split(":", 1)[1].strip())
        if not data_lines:
            continue
        seq += 1
        try:
            d = json.loads("".join(data_lines))
        except json.JSONDecodeError:
            d = {"_raw": "".join(data_lines)[:500]}
        trace.append({"seq": seq, "event": event_name, "data": d, "elapsed_ms": total_ms})
        if event_name == "turn.completed":
            final = d
    if not final:
        raise RuntimeError("No turn.completed event")
    return trace, final, total_ms


# ── Resume bootstrap ────────────────────────────────────────────────────

def _upload_resume(base_url: str, obj: Dict, title: str) -> str:
    resp, _ = _req(base_url, "/agent/recent-resumes/save", "POST",
                   {"resume_obj": obj, "title": title, "tags": ["eval"], "status": "draft"})
    return str(resp.get("id", "unknown"))

def pick_or_create_resume(base_url: str) -> Tuple[Dict, str]:
    items_resp, _ = _req(base_url, "/agent/recent-resumes?limit=5")
    items = items_resp.get("items", [])
    if items:
        rid = str(items[0].get("id", ""))
        detail, _ = _req(base_url, f"/agent/recent-resumes/{urllib.parse.quote(rid)}")
        obj = detail.get("resume_obj", {})
        if isinstance(obj, dict) and obj:
            return obj, rid
    raise RuntimeError("No recent resumes available — upload one first or use --resume-fixtures")

def load_resume_fixtures(fixtures_dir: Path | None = None) -> List[Tuple[str, Dict]]:
    if fixtures_dir is None:
        fixtures_dir = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "resumes"
    fixtures = []
    if not fixtures_dir.exists():
        return fixtures
    for f in sorted(fixtures_dir.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(d, dict) and "personalInfo" in d:
                fixtures.append((f.stem, d))
        except Exception:
            pass
    return fixtures


# ── Assertions ──────────────────────────────────────────────────────────

def _chain(trace: List[Dict]) -> List[str]:
    tools = []
    for e in trace:
        if e.get("event") == "step.succeeded" and e.get("data", {}).get("tool", "") not in ("self_check_turn",):
            tools.append(str(e["data"]["tool"]))
    return tools

def run_assertions(scenario: Scenario, trace: List[Dict], turn: Dict) -> Dict[str, bool]:
    chain = _chain(trace)
    action = turn.get("actionability_summary", {}) or {}
    istate = turn.get("intent_state", {}) or {}
    asst = str(turn.get("assistant_message", "")).strip()
    res = {}
    for rule in scenario.assertions:
        if rule == "no_mutation":            res[rule] = action.get("total", 0) == 0
        elif rule == "has_confirm_required": res[rule] = action.get("confirm_required", 0) > 0
        elif rule == "has_apply_ready":      res[rule] = action.get("apply_ready", 0) > 0
        elif rule == "chain_has_suggest":    res[rule] = "propose_suggest" in chain or "propose_direct_edit" in chain or "agent_loop" in chain
        elif rule == "chain_has_refine":     res[rule] = "propose_refine" in chain or "propose_direct_edit" in chain or "agent_loop" in chain
        elif rule == "chain_has_analyze":    res[rule] = "analyze_content" in chain
        elif rule == "chain_ends_with_compose": res[rule] = any(
            e.get("event") == "step.succeeded" and e.get("data", {}).get("tool") == "compose_and_check"
            for e in trace
        )
        elif rule == "assistant_not_empty":  res[rule] = len(asst) > 5
        elif rule == "intent_matches_expected": res[rule] = istate.get("intent_class", "") == scenario.expected_intent
        else: res[rule] = False
    return res


# ── Content diff ────────────────────────────────────────────────────────

def _diff(before: Dict, after: Dict) -> Dict:
    def _flat(obj, prefix=""):
        r = {}
        if isinstance(obj, dict):
            for k, v in obj.items(): r.update(_flat(v, f"{prefix}.{k}" if prefix else k))
        elif isinstance(obj, list):
            for i, v in enumerate(obj): r.update(_flat(v, f"{prefix}[{i}]"))
        else:
            r[prefix] = obj
        return r
    def _txt(v):
        if v is None: return ""
        if isinstance(v, str): return v.strip()
        if isinstance(v, (int, float, bool)): return str(v)
        return json.dumps(v, ensure_ascii=False, sort_keys=True)

    fb, fa = _flat(before), _flat(after)
    changed = []
    for k in sorted(set(fb.keys()) | set(fa.keys())):
        bt, at = _txt(fb.get(k)), _txt(fa.get(k))
        if bt != at:
            ct = "added" if not bt else ("removed" if not at else "modified")
            changed.append({"path": k, "before": bt[:500], "after": at[:500], "change_type": ct})
    secs = {}
    for c in changed:
        s = c["path"].split(".")[0].split("[")[0]
        secs[s] = secs.get(s, 0) + 1
    return {"total_changed_fields": len(changed), "sections_changed": secs,
            "changed_paths": changed[:50], "has_changes": len(changed) > 0}


# ── Log builder ─────────────────────────────────────────────────────────

def build_log(scenario: Scenario, trace: List[Dict], turn: Dict, snapshot: Dict,
              assertions: Dict[str, bool], meta: Dict,
              resume_before: Dict | None = None, resume_after: Dict | None = None,
              session_sdo: Dict | None = None) -> Dict:
    chain = _chain(trace)
    istate = turn.get("intent_state", {}) or {}
    action = turn.get("actionability_summary", {}) or {}
    sc = turn.get("self_check_result") or turn.get("self_check", {}) or {}

    # Compact trace
    ct = []
    for e in trace:
        ce = {"seq": e["seq"], "event": e["event"], "elapsed_ms": e.get("elapsed_ms", 0)}
        d = e.get("data", {})
        if e["event"] == "turn.completed":
            ce["data"] = {k: v for k, v in d.items()
                          if k in {"session_id", "turn_id", "assistant_message", "selected_tool_chain",
                                   "actionability_summary", "self_check_result", "intent_state",
                                   "termination_reason", "thought_summary", "content_assessment",
                                   "fact_issues", "step_reason_summary", "planner_decision_trace"}}
            ce["data"]["_full_keys"] = list(d.keys())
        else:
            ce["data"] = d
        ct.append(ce)

    # Content diff
    cd = _diff(resume_before, resume_after) if resume_before and resume_after else None

    # Suggestion diffs
    items = (session_sdo or {}).get("items", []) or []
    items.extend((turn.get("suggestion_document_obj", {}) or {}).get("items", []) or [])
    seen, unique = set(), []
    for it in items:
        if not isinstance(it, dict): continue
        k = str(it.get("item_key") or it.get("path", ""))
        if k and k not in seen:
            seen.add(k); unique.append(it)
    sdiffs = []
    for it in unique:
        bv = str(it.get("current_value_raw") or it.get("current_value") or "").strip()
        av = str(it.get("refined_value_raw") or it.get("suggested_value_raw") or it.get("suggested_value") or "").strip()
        if bv != av:
            sdiffs.append({"item_key": str(it.get("item_key", "")), "path": str(it.get("path", "")),
                           "reason": str(it.get("reason", ""))[:100], "actionability": str(it.get("actionability", "")),
                           "before": bv[:300], "after": av[:300]})

    rb_sum = {"sections": [k for k in (resume_before or {}).keys() if (resume_before or {}).get(k)],
              "we_count": len((resume_before or {}).get("workExperience", []) or [])} if resume_before else None
    ra_sum = {"sections": [k for k in (resume_after or {}).keys() if (resume_after or {}).get(k)],
              "we_count": len((resume_after or {}).get("workExperience", []) or [])} if resume_after else None

    return {
        "meta": meta,
        "scenario": {"name": scenario.name, "message": scenario.message,
                     "expected_intent": scenario.expected_intent, "expected_scope": scenario.expected_scope,
                     "assertions_defined": scenario.assertions, "tags": scenario.tags},
        "content_diff": cd,
        "suggestion_diff": {"total_suggestions": len(unique),
                            "suggestions_with_changes": len(sdiffs), "items": sdiffs[:20]},
        "resume_before": rb_sum, "resume_after": ra_sum,
        "turn": {"tool_chain": chain, "tool_chain_length": len(chain),
                 "intent_state": {"intent_class": istate.get("intent_class", ""),
                                  "active_scope": istate.get("active_scope", ""),
                                  "goal": istate.get("goal", ""), "confidence": istate.get("confidence", 0)},
                 "actionability_summary": action,
                 "self_check": {"verdict": sc.get("result") or sc.get("verdict", "unknown"),
                                "reason": str(sc.get("reason", ""))[:100]},
                 "assistant_message": str(turn.get("assistant_message", "")).strip(),
                 "suggestion_count": len((turn.get("suggestion_document_obj", {}) or {}).get("items", []) or []),
                 "fact_issue_count": len(turn.get("fact_issues", []) or []),
                 "termination_reason": str(turn.get("termination_reason", "")),
                 "duration_ms": trace[-1]["elapsed_ms"] if trace else 0},
        "session_snapshot": {"message_count": len(snapshot.get("messages", []) or []),
                             "state_keys": list((snapshot.get("state", {}) or {}).keys())},
        "trace": ct, "trace_event_count": len(ct),
        "assertions": assertions,
        "assertions_passed": sum(1 for v in assertions.values() if v),
        "assertions_total": len(assertions),
        "all_assertions_passed": all(assertions.values()) if assertions else True,
    }


# ── Scenario runner ─────────────────────────────────────────────────────

def _start_session(base_url: str, resume_obj: Dict) -> str:
    payload = {"doc_type": "resume", "title": f"Eval {_now_iso()}", "window_size": 10,
               "raw_document_obj": resume_obj, "normalized_document_obj": resume_obj,
               "refined_document_obj": resume_obj}
    data, _ = _req(base_url, "/agent/v3/sessions", "POST", payload)
    sid = str(data.get("session_id", ""))
    if not sid:
        raise RuntimeError("No session_id")
    return sid

def run_one_scenario(base_url: str, scenario: Scenario, resume_obj: Dict, resume_id: str,
                     run_started: str, output_dir: Path, do_apply: bool,
                     idx: int, total: int, log_prefix: str = "") -> Dict:
    log_path = output_dir / f"{log_prefix}{scenario.name}.json"
    result = {"name": scenario.name, "idx": idx, "passed": False, "error": None,
              "chain": [], "intent": "", "action": {}, "self_check": "", "duration_ms": 0, "log_path": str(log_path)}
    try:
        sid = _start_session(base_url, resume_obj)
        meta = {"run_at": run_started, "scenario_index": idx, "base_url": base_url,
                "session_id": sid, "resume_id": resume_id, "resume_hash": _sha1_json(resume_obj)[:8]}
        before = dict(resume_obj)

        trace, turn, ms = _sse(base_url,
            f"/agent/v3/sessions/{urllib.parse.quote(sid)}/turns:run",
            {"message": scenario.message, "allow_mutation": True, "llm_config": {}, "layout_preferences": {}})

        snap, _ = _req(base_url, f"/agent/v3/sessions/{urllib.parse.quote(sid)}?message_limit=5&event_limit=200")
        raw_state = snap.get("state", {}) or {}
        after = turn.get("refined_document_obj") or turn.get("document_obj") or \
                raw_state.get("refined_document_obj") or raw_state.get("refined_resume_obj") or dict(resume_obj)
        sdo = raw_state.get("suggestion_document_obj") or raw_state.get("suggestion_resume_obj") or {}

        assertions = run_assertions(scenario, trace, turn)
        log = build_log(scenario, trace, turn, snap, assertions, meta,
                        resume_before=before, resume_after=after if isinstance(after, dict) else None,
                        session_sdo=sdo)
        log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

        chain = log["turn"]["tool_chain"]
        intent = log["turn"]["intent_state"]["intent_class"]
        action = log["turn"]["actionability_summary"]
        sc = log["turn"]["self_check"]["verdict"]
        ok = log["all_assertions_passed"]
        result.update({"passed": ok, "chain": chain, "intent": intent, "action": action,
                       "self_check": sc, "duration_ms": ms, "assertions": assertions})

        # Multi-turn
        if do_apply and scenario.multi_turn:
            sdo_items = (turn.get("suggestion_document_obj", {}) or {}).get("items", []) or []
            if "apply" in scenario.multi_turn and sdo_items:
                keys = [str(i.get("item_key", "")) for i in sdo_items[:2] if str(i.get("item_key", ""))]
                if keys:
                    applied, ams = _req(base_url,
                        f"/agent/v3/sessions/{urllib.parse.quote(sid)}/actions:apply", "POST",
                        {"llm_config": {}, "human_review_decision": {"accepted_item_keys": keys},
                         "suggestion_document_obj": turn.get("suggestion_document_obj")}, timeout=180)
                    result["apply_ms"] = ams
                    result["applied_count"] = len(applied.get("applied_changes", []))
            elif "reject" in scenario.multi_turn and sdo_items:
                keys = [str(i.get("item_key", "")) for i in sdo_items[:2] if str(i.get("item_key", ""))]
                if keys:
                    _, rms = _req(base_url,
                        f"/agent/v3/sessions/{urllib.parse.quote(sid)}/actions:reject", "POST",
                        {"llm_config": {}, "rejected_item_keys": keys, "reject_all": False,
                         "suggestion_document_obj": turn.get("suggestion_document_obj")}, timeout=180)
                    result["reject_ms"] = rms

        status = "PASS" if ok else "FAIL"
        fi = ""
        if not ok:
            fi = " | FAILED: " + str([k for k, v in assertions.items() if not v])
        print(f"  [{idx:02d}/{total}] {status} {scenario.name} | chain={'->'.join(chain)} | "
              f"intent={intent} | sugg={action.get('total',0)} | sc={sc} | {ms}ms{fi}")
    except Exception as exc:
        result["error"] = str(exc)
        print(f"  [{idx:02d}/{total}] ERROR {scenario.name}: {exc}")
        err_log = {"meta": {"run_at": run_started}, "scenario": {"name": scenario.name}, "error": str(exc)}
        log_path.write_text(json.dumps(err_log, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


# ── Main runner ─────────────────────────────────────────────────────────

def run_eval(base_url: str, scenarios: List[Scenario], output_dir: Path,
             do_apply: bool = False, concurrency: int = 1,
             resume_fixtures: List[Tuple[str, Dict]] | None = None) -> Tuple[int, Path, List[Dict]]:
    run_started = _now_iso()
    run_dir = output_dir / run_started.replace(":", "-")
    run_dir.mkdir(parents=True, exist_ok=True)

    if resume_fixtures:
        resumes = resume_fixtures
        print("=" * 60)
        print(f"[bootstrap] {len(resumes)} resume fixtures")
        for name, obj in resumes:
            try:
                rid = _upload_resume(base_url, obj, f"Fixture: {name}")
                print(f"[bootstrap]   {name} -> {rid[:8]}")
            except Exception as exc:
                print(f"[bootstrap]   {name} FAILED: {exc}")
    else:
        print("=" * 60)
        print("[bootstrap] picking resume...")
        obj, rid = pick_or_create_resume(base_url)
        print(f"[bootstrap] resume_id={rid}")
        resumes = [("default", obj)]

    print(f"[bootstrap] concurrency={concurrency}  scenarios={len(scenarios)}  resumes={len(resumes)}")
    print(f"[bootstrap] run_dir={run_dir}")
    print("=" * 60)

    all_results: List[Dict] = []
    for rname, robj in resumes:
        prefix = f"{rname}_" if len(resumes) > 1 else ""
        logs_dir = run_dir / "logs" / rname if len(resumes) > 1 else run_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        if concurrency <= 1:
            for idx, sc in enumerate(scenarios, start=1):
                all_results.append(run_one_scenario(
                    base_url, sc, robj, _sha1_json(robj)[:8],
                    run_started, logs_dir, do_apply, idx, len(scenarios), ""))
        else:
            label = f"[{rname}] " if len(resumes) > 1 else ""
            print(f"\n{label}Running {len(scenarios)} scenarios x{concurrency}...\n")
            futures = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
                for idx, sc in enumerate(scenarios, start=1):
                    f = ex.submit(run_one_scenario, base_url, sc, robj, _sha1_json(robj)[:8],
                                  run_started, logs_dir, do_apply, idx, len(scenarios), "")
                    futures[f] = sc.name
                for f in concurrent.futures.as_completed(futures):
                    try:
                        all_results.append(f.result())
                    except Exception as exc:
                        all_results.append({"name": futures[f], "passed": False, "error": str(exc)})

    all_results.sort(key=lambda r: r.get("idx", 0))
    passed = sum(1 for r in all_results if r.get("passed"))
    failed = [r["name"] for r in all_results if not r.get("passed") and not r.get("error")]
    errs = [f"{r['name']}: {r['error']}" for r in all_results if r.get("error")]

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{len(all_results)} passed"
          + (f" ({len(resumes)} resumes)" if resume_fixtures else ""))
    if failed:
        print(f"FAILED: {', '.join(failed[:10])}{' +'+str(len(failed)-10) if len(failed)>10 else ''}")
    if errs:
        print(f"ERRORS: {', '.join(errs[:5])}")
    print(f"RUN DIR: {run_dir}/")
    print("=" * 60)
    return (0 if passed == len(all_results) else 1), run_dir, all_results
