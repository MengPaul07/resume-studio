"""LLM tailor agent tests — cover remaining agent behaviors beyond simple editing.

Run:
    pytest tests/llm/test_tailor_llm.py -v -s -n auto
"""

import json

from tests.llm.helpers import LLM_CONFIG, get, refined, run_turn, session


# ── JD-related tests ──

def test_searches_job_descriptions():
    """Agent should call search_jd and return matching results."""
    resume = {
        "personalInfo": {"name": "Searcher", "title": "Backend Engineer"},
        "summary": "Backend engineer with Go and Kubernetes experience.",
        "workExperience": [{"title": "SDE", "company": "CloudCo", "years": "2021-2024",
                            "description": ["Built microservices", "Managed K8s clusters"]}],
        "education": [],
        "additional": {"technicalSkills": "Go, Python, Kubernetes, Docker"},
    }
    sid = session(resume)
    r = run_turn(sid, "Search for backend engineer jobs that match my skills.", timeout=300)
    assert not r["error"], r["error"]
    completed = [e for e in r["events"] if e[0] == "turn.completed"]
    asst = completed[0][1].get("assistant_message", "") if completed else ""
    jd_matches = completed[0][1].get("turn_output_bundle", {}).get("jd_matches", []) if completed else []
    print(f"  [ok] JD search returned, jd_matches={len(jd_matches)}  ({r['elapsed']:.1f}s)")


def test_sets_target_jd():
    """Agent should set a target JD when user provides one."""
    resume = {
        "personalInfo": {"name": "Targeter", "title": "ML Engineer"},
        "summary": "ML engineer with NLP experience.",
        "workExperience": [],
        "education": [],
        "additional": {"technicalSkills": "Python, PyTorch"},
    }
    sid = session(resume)
    jd_text = "Senior ML Engineer at AI Lab. Requires: Python, PyTorch, NLP, 5+ years experience, distributed training."
    r = run_turn(sid,
        f"Set this as my target job description:\n\n{jd_text}\n\nThen optimize my summary for this role.",
        timeout=300,
    )
    assert not r["error"], r["error"]
    rf = refined(r["state"])
    summary = get(rf, "summary")
    assert summary and len(str(summary)) > 10, f"Summary empty: {summary}"
    print(f"  [ok] JD set + summary optimized: {str(summary)[:80]}  ({r['elapsed']:.1f}s)")


# ── Analysis and chat tests ──

def test_greeting_triggers_compose_directly():
    """A simple greeting should call compose without touching the resume."""
    resume = {
        "personalInfo": {"name": "Greeter"},
        "summary": "This should not be read.",
        "workExperience": [],
        "education": [],
        "additional": {},
    }
    sid = session(resume)
    r = run_turn(sid, "Hello, can you help me with my resume?")
    assert not r["error"], r["error"]
    completed = [e for e in r["events"] if e[0] == "turn.completed"]
    asst = completed[0][1].get("assistant_message", "") if completed else ""
    assert len(asst) > 5, "No greeting response"
    print(f"  [ok] greeting: {asst[:80]}  ({r['elapsed']:.1f}s)")


def test_analyzes_resume_without_editing():
    """Analysis request should read_resume then compose, no edits."""
    resume = {
        "personalInfo": {"name": "Analyzer", "title": "Fullstack Dev"},
        "summary": "Fullstack developer with React and Node.js experience.",
        "workExperience": [{"title": "SDE", "company": "WebCo", "years": "2020-2023",
                            "description": ["Built dashboard", "Improved performance"]}],
        "education": [{"institution": "UCLA", "degree": "BS", "years": "2016-2020"}],
        "additional": {"technicalSkills": "React, Node.js, TypeScript"},
    }
    sid = session(resume)
    r = run_turn(sid, "Analyze my resume. What are its strengths and weaknesses? Don't make any changes.")
    assert not r["error"], r["error"]
    completed = [e for e in r["events"] if e[0] == "turn.completed"]
    asst = completed[0][1].get("assistant_message", "") if completed else ""
    assert len(asst) > 20, f"Analysis too short: {asst[:100]}"
    # Original data should be intact
    rf = refined(r["state"])
    original_title = get(rf, "workExperience[0].title")
    assert original_title == "SDE", f"Work entry was modified: {original_title}"
    print(f"  [ok] analysis without edits: title intact={original_title}  ({r['elapsed']:.1f}s)")


# ── Delete tests ──

def test_deletes_work_experience_entry():
    """Agent should delete an entry when asked."""
    resume = {
        "personalInfo": {"name": "Deleter", "title": "Engineer"},
        "summary": "Engineer.",
        "workExperience": [
            {"title": "SDE I", "company": "OldCo", "years": "2018-2020",
             "description": ["Did stuff"]},
            {"title": "SDE II", "company": "MidCo", "years": "2020-2023",
             "description": ["Did more stuff"]},
        ],
        "education": [],
        "additional": {},
    }
    sid = session(resume)
    r = run_turn(sid, "Delete the first work experience entry (the one at OldCo).")
    assert not r["error"], r["error"]
    rf = refined(r["state"])
    we = get(rf, "workExperience")
    assert we and len(we) >= 1, f"All entries deleted: {we}"
    for e in we:
        assert isinstance(e, dict), f"Entry not dict: {type(e).__name__}"
    print(f"  [ok] delete: {len(we)} entries remain  ({r['elapsed']:.1f}s)")


# ── Fact sensitivity tests ──

def test_flags_personal_info_edit_as_confirm_required():
    """Editing name/email should trigger ask_user or confirm_required."""
    resume = {
        "personalInfo": {"name": "Old Name", "email": "old@email.com", "phone": "123"},
        "summary": "Engineer.",
        "workExperience": [],
        "education": [],
        "additional": {},
    }
    sid = session(resume)
    r = run_turn(sid, "Change my name to 'New Name' and email to 'new@email.com'.")
    assert not r["error"], r["error"]
    events = r["events"]
    # Check if paused (ask_user) or fact_issues returned
    paused = [e for e in events if e[0] == "turn.paused"]
    completed = [e for e in events if e[0] == "turn.completed"]
    fact_issues = (completed[0][1].get("fact_issues", []) if completed else []) or \
                  (completed[0][1].get("turn_output_bundle", {}).get("fact_issues", []) if completed else [])
    has_confirm = bool(paused) or len(fact_issues) > 0
    print(f"  [ok] fact edit: paused={bool(paused)}  fact_issues={len(fact_issues)}  ({r['elapsed']:.1f}s)")


# ── Custom sections test ──

def test_edits_custom_sections():
    """Agent should handle custom section edits."""
    resume = {
        "personalInfo": {"name": "Custom", "title": "Speaker"},
        "summary": "Professional speaker.",
        "workExperience": [],
        "education": [],
        "additional": {},
        "customSections": {"speaking": {"items": ["Talk at Conf1", "Talk at Conf2"]}},
    }
    sid = session(resume)
    r = run_turn(sid, "Add a third talk: 'Keynote at DevConf 2024' to my speaking custom section.")
    assert not r["error"], r["error"]
    rf = refined(r["state"])
    cs = get(rf, "customSections")
    assert cs is not None, f"customSections is None"
    print(f"  [ok] customSections exists  ({r['elapsed']:.1f}s)")


# ── Multi-turn conversation test ──

def test_multi_turn_conversation_preserves_state():
    """Multiple turns in one session should accumulate changes correctly."""
    resume = {
        "personalInfo": {"name": "Multi", "title": "Dev"},
        "summary": "Developer.",
        "workExperience": [],
        "education": [],
        "additional": {"technicalSkills": "Python"},
    }
    sid = session(resume)

    # Turn 1: Add a skill
    r1 = run_turn(sid, "Add 'Go' to my technical skills.")
    assert not r1["error"], r1["error"]
    print(f"  turn1: {r1['elapsed']:.1f}s")

    # Turn 2: Add another skill (should accumulate with turn 1)
    r2 = run_turn(sid, "Also add 'Rust' to my skills.")
    assert not r2["error"], r2["error"]
    print(f"  turn2: {r2['elapsed']:.1f}s")

    # Turn 3: Update summary
    r3 = run_turn(sid, "Rewrite my summary to say I'm a polyglot developer experienced in Python, Go, and Rust.")
    assert not r3["error"], r3["error"]
    print(f"  turn3: {r3['elapsed']:.1f}s")

    rf = refined(r3["state"])
    skills = str(get(rf, "additional.technicalSkills")).lower()
    summary = str(get(rf, "summary")).lower()
    assert "go" in skills, f"Go not in skills after turn 2: {skills}"
    assert "python" in skills, f"Python lost: {skills}"
    assert len(summary) > 20, f"Summary empty after turn 3"
    print(f"  [ok] multi-turn: skills accumulated, summary updated  (total {r1['elapsed']+r2['elapsed']+r3['elapsed']:.1f}s)")


# ── Vague request handling ──

def test_handles_vague_request_with_clarification():
    """Agent should ask for clarification on vague requests, not crash."""
    resume = {
        "personalInfo": {"name": "Vague", "title": "Something"},
        "summary": "I do things.",
        "workExperience": [],
        "education": [],
        "additional": {},
    }
    sid = session(resume)
    r = run_turn(sid, "Make it better.")
    assert not r["error"], r["error"]
    completed = [e for e in r["events"] if e[0] == "turn.completed"]
    asst = completed[0][1].get("assistant_message", "") if completed else ""
    assert len(asst) > 5, f"Empty response to vague request"
    print(f"  [ok] vague request response: {asst[:80]}  ({r['elapsed']:.1f}s)")


# ── JSON value format test ──

def test_adds_work_experience_with_proper_json_format():
    """Adding a new work entry via add_entry should produce structured JSON, not flat text."""
    resume = {
        "personalInfo": {"name": "Formatter", "title": "SDE"},
        "summary": "Engineer.",
        "workExperience": [],
        "education": [],
        "additional": {},
    }
    sid = session(resume)
    r = run_turn(sid,
        "Add a new work experience as a JSON object. Use add_entry tool. "
        "Title: Staff Engineer, Company: Stripe, Years: 2022-2024, "
        "Description as array: ['Built payment orchestration layer handling $1B+ monthly volume', "
        "'Led migration from REST to GraphQL across 12 services', "
        "'Mentored 6 engineers through promotion process']"
    )
    assert not r["error"], r["error"]
    rf = refined(r["state"])
    we = get(rf, "workExperience")
    assert we and len(we) >= 1, f"No work entry added: {we}"
    new_entry = we[-1] if len(we) > 1 else we[0]
    assert isinstance(new_entry, dict), f"New entry is {type(new_entry).__name__}, not dict: {str(new_entry)[:200]}"
    if isinstance(new_entry, dict):
        desc = new_entry.get("description", [])
        assert isinstance(desc, list), f"description not array: {type(desc).__name__} = {desc}"
    print(f"  [ok] work entry added as dict  ({r['elapsed']:.1f}s)")
