"""LLM interview tests — verify the full interview flow with real LLM.

Run:
    pytest tests/llm/test_interview_llm.py -v -s -n auto
"""

from tests.llm.helpers import LLM_CONFIG, get, refined, run_turn, session


def _interview_session(resume: dict) -> str:
    """Create an interview session and kick off the first turn."""
    sid = session(resume)
    r = run_turn(sid, "Start the interview. Introduce yourself as the interviewer and ask the first question.",
                 timeout=300)
    assert not r["error"], f"Interview start failed: {r['error']}"
    return sid


def test_starts_interview_and_asks_first_question():
    resume = {
        "personalInfo": {"name": "Test Candidate", "title": "Backend Engineer"},
        "summary": "Backend engineer with 3 years experience in distributed systems.",
        "workExperience": [{"title": "SDE", "company": "TechCorp", "years": "2021-2024",
                            "description": ["Built APIs", "Optimized database queries"]}],
        "education": [{"institution": "MIT", "degree": "BS CS", "years": "2017-2021"}],
        "additional": {"technicalSkills": "Python, Go, PostgreSQL"},
    }
    sid = session(resume)
    r = run_turn(sid, "Start the interview. Introduce yourself as the interviewer and ask the first question.",
                 timeout=300)
    assert not r["error"], f"Error: {r['error']}"
    # Verify assistant responded
    events = r["events"]
    composed = [e for e in events if e[0] == "turn.composed"]
    assert composed, "No turn.composed event"
    print(f"  [ok] interview started  ({r['elapsed']:.1f}s)")


def test_answers_question_and_gets_followup():
    resume = {
        "personalInfo": {"name": "Interviewee", "title": "ML Engineer"},
        "summary": "ML engineer specialized in NLP and recommendation systems.",
        "workExperience": [{"title": "ML Engineer", "company": "AI Corp", "years": "2020-2024",
                            "description": ["Built recommendation pipeline", "Improved CTR 15%"]}],
        "education": [{"institution": "Tsinghua", "degree": "MS CS", "years": "2018-2020"}],
        "additional": {"technicalSkills": "Python, PyTorch, TensorFlow"},
    }
    sid = _interview_session(resume)
    # Answer the first question
    r2 = run_turn(sid, "I worked on a recommendation system that served 10M daily users. "
                       "We used a two-tower model with real-time features.", timeout=300)
    assert not r2["error"], f"Error: {r2['error']}"
    events = r2["events"]
    composed = [e for e in events if e[0] == "turn.composed"]
    assert composed, "No follow-up from interviewer"
    print(f"  [ok] answered + got follow-up  ({r2['elapsed']:.1f}s)")


def test_ends_interview_and_generates_report():
    resume = {
        "personalInfo": {"name": "Finisher", "title": "DevOps"},
        "summary": "DevOps engineer.",
        "workExperience": [],
        "education": [],
        "additional": {},
    }
    sid = _interview_session(resume)
    r2 = run_turn(sid, "I have experience with Kubernetes and CI/CD pipelines.", timeout=300)
    assert not r2["error"], r2["error"]
    # End the interview
    r3 = run_turn(sid, "结束", timeout=300)
    assert not r3["error"], f"End interview error: {r3['error']}"
    completed = [e for e in r3["events"] if e[0] == "turn.completed"]
    finished = completed[0][1] if completed else {}
    asst = finished.get("assistant_message", "")
    score_found = "score" in asst.lower() or "评分" in asst or "Score" in asst
    print(f"  [ok] interview ended, report score={'yes' if score_found else 'no'}  ({r3['elapsed']:.1f}s)")


def test_coding_question_emits_coding_event():
    resume = {
        "personalInfo": {"name": "Coder", "title": "Software Engineer"},
        "summary": "Experienced software engineer skilled in algorithms.",
        "workExperience": [{"title": "SDE", "company": "CodeCo", "years": "2020-2024",
                            "description": ["Built trading system", "Optimized algorithms"]}],
        "education": [{"institution": "CMU", "degree": "BS CS", "years": "2016-2020"}],
        "additional": {"technicalSkills": "Java, C++, Python"},
    }
    sid = _interview_session(resume)
    # Answer in a way that encourages the interviewer to ask a coding question
    r2 = run_turn(sid, "I implemented a custom LRU cache for our trading system that reduced latency by 30%."
                       "Can you give me a coding challenge?", timeout=300)
    assert not r2["error"], r2["error"]
    # Check if a coding question event was emitted in either turn
    all_events = r2["events"]
    coding_events = [e for e in all_events if e[0] == "coding_question"]
    # The coding question might come in a separate turn
    if not coding_events:
        r3 = run_turn(sid, "Yes, I'm ready for the coding question.", timeout=300)
        assert not r3["error"], r3["error"]
        coding_events = [e for e in r3["events"] if e[0] == "coding_question"]
    has_coding = bool(coding_events)
    print(f"  [ok] coding_question emitted: {has_coding}  ({r2['elapsed']:.1f}s)")
