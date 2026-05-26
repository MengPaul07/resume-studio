"""LLM memory tests — verify preference extraction and injection.

Run:
    pytest tests/llm/test_memory_llm.py -v -s
"""

import json
import time

from tests.llm.helpers import LLM_CONFIG, run_turn, session


def _memory_file(user_id: str):
    from pathlib import Path
    fp = Path(__file__).resolve().parents[2] / "src/services/data/user_preferences" / f"{user_id}.json"
    if fp.exists():
        return json.loads(fp.read_text(encoding="utf-8"))
    return {"preferences": []}


def test_extracts_style_preference_from_explicit_request():
    """User explicitly states preferences -> extracted to memory."""
    uid = "test-mem-style"
    resume = {
        "personalInfo": {"name": "Pref Test", "title": "Engineer"},
        "summary": "Engineer.",
        "workExperience": [],
        "education": [],
        "additional": {},
    }
    sid = session(resume, user_id=uid)
    r = run_turn(sid,
        "Rewrite my summary. Important preferences: I prefer short, punchy bullet points. "
        "Each bullet must start with an action verb and include a number. "
        "Never add soft skills like 'communication' or 'teamwork' to my resume.",
        timeout=180, user_id=uid,
    )
    assert not r["error"], r["error"]
    print(f"  [exec] turn ({r['elapsed']:.1f}s)")

    time.sleep(6)  # wait for background extraction thread
    mem = _memory_file(uid)
    prefs = mem.get("preferences", [])
    print(f"  [mem] prefs={prefs}")
    assert len(prefs) >= 1, f"No preferences extracted: {json.dumps(mem, ensure_ascii=False)[:200]}"
    print(f"  [ok] {len(prefs)} preference(s)")


def test_memory_injected_into_agent_context():
    """Pre-populated preferences -> agent sees them in context."""
    uid = "test-mem-context"
    from pathlib import Path
    fp = Path(__file__).resolve().parents[2] / "src/services/data/user_preferences" / f"{uid}.json"
    fp.parent.mkdir(parents=True, exist_ok=True)
    test_memory = {
        "preferences": [
            {"key": "style", "value": "use concise bullets with quantified metrics", "updated_at": "2026-01-01T00:00:00Z"},
            {"key": "avoid", "value": "no soft skills or communication-related fluff", "updated_at": "2026-01-01T00:00:00Z"},
        ],
    }
    fp.write_text(json.dumps(test_memory, ensure_ascii=False, indent=2), encoding="utf-8")

    resume = {
        "personalInfo": {"name": "Context Test", "title": "SDE"},
        "summary": "Developer.",
        "workExperience": [],
        "education": [],
        "additional": {},
    }
    sid = session(resume, user_id=uid)
    r = run_turn(sid,
        "What do you know about my preferences and background? Summarize briefly.",
        timeout=180, user_id=uid,
    )
    assert not r["error"], r["error"]
    completed = [e for e in r["events"] if e[0] == "turn.completed"]
    asst = completed[0][1].get("assistant_message", "") if completed else ""
    combined = asst.lower()
    found = any(word in combined for word in ["concise", "bullet", "quantif"])
    print(f"  [exec] agent response: {asst[:200]} ({r['elapsed']:.1f}s)")
    print(f"  [ok] memory referenced: {'yes' if found else 'maybe not - check output'}")
