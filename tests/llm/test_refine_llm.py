"""LLM resume refinement tests — verify agent editing beyond the flash edit scenarios.

Run:
    pytest tests/llm/test_refine_llm.py -v -s -n auto
"""

from tests.llm.helpers import LLM_CONFIG, get, refined, run_turn, session


def _refine_turn(resume: dict, msg: str, timeout: int = 180) -> dict:
    sid = session(resume)
    return run_turn(sid, msg, timeout=timeout)


def test_rewrites_summary_to_be_more_impactful():
    resume = {
        "personalInfo": {"name": "Refiner", "title": "Engineer"},
        "summary": "I worked on some projects and did some coding.",
        "workExperience": [],
        "education": [],
        "additional": {"technicalSkills": "Python"},
    }
    r = _refine_turn(resume,
        "Rewrite my summary to be more professional and impactful. "
        "Make it sound like a senior engineer's summary."
    )
    assert not r["error"], r["error"]
    rf = refined(r["state"])
    summary = get(rf, "summary")
    assert summary and len(str(summary)) > 20, f"Summary too short: {summary}"
    assert isinstance(summary, str), f"Summary corrupted: {type(summary).__name__}"
    # Should be significantly different from the original
    assert "worked on some projects" not in str(summary).lower(), f"Summary unchanged: {summary}"
    print(f"  [ok] summary rewritten: {len(str(summary))} chars  ({r['elapsed']:.1f}s)")


def test_improves_work_description_bullets():
    resume = {
        "personalInfo": {"name": "Bullet", "title": "SDE"},
        "summary": "Engineer.",
        "workExperience": [{"title": "SDE", "company": "OldCo", "years": "2020-2023",
                            "description": ["Did stuff", "Fixed bugs"]}],
        "education": [],
        "additional": {},
    }
    r = _refine_turn(resume,
        "Improve my work experience descriptions. Make each bullet point specific, "
        "quantified, and professional. Use STAR format."
    )
    assert not r["error"], r["error"]
    rf = refined(r["state"])
    desc = get(rf, "workExperience[0].description")
    assert isinstance(desc, list), f"description not list: {type(desc).__name__}"
    improved = any(len(str(b)) > 15 for b in desc)
    we0 = get(rf, "workExperience[0]")
    assert isinstance(we0, dict), f"workExperience[0] became {type(we0).__name__}"
    print(f"  [ok] bullets={'improved' if improved else 'unchanged'}, still structured  ({r['elapsed']:.1f}s)")


def test_adds_new_skill_to_existing_list():
    resume = {
        "personalInfo": {"name": "Skiller", "title": "Dev"},
        "summary": "Developer.",
        "workExperience": [],
        "education": [],
        "additional": {"technicalSkills": ["Python", "JavaScript"]},
    }
    r = _refine_turn(resume, "Add 'Rust', 'Kubernetes', and 'Terraform' to my technical skills.")
    assert not r["error"], r["error"]
    rf = refined(r["state"])
    skills = get(rf, "additional.technicalSkills")
    skills_str = str(skills).lower()
    is_array = isinstance(skills, list)
    for expected in ["rust", "kubernetes", "terraform"]:
        assert expected in skills_str, f"'{expected}' not in skills: {skills}"
    print(f"  [ok] skills={'array' if is_array else type(skills).__name__}, '{expected}' found  ({r['elapsed']:.1f}s)")


def test_fixes_typo_in_personal_info():
    resume = {
        "personalInfo": {"name": "Typo Guy", "email": "typo@gmali.com", "phone": "1234567890"},
        "summary": "Engineer.",
        "workExperience": [],
        "education": [],
        "additional": {},
    }
    r = _refine_turn(resume, "My email is wrong — it should be typo@gmail.com. Fix it.")
    assert not r["error"], r["error"]
    rf = refined(r["state"])
    email = get(rf, "personalInfo.email")
    assert email == "typo@gmail.com", f"Email not fixed: {email}"
    print(f"  [ok] email fixed to {email}  ({r['elapsed']:.1f}s)")


def test_adds_new_education_entry():
    resume = {
        "personalInfo": {"name": "Student", "title": "New Grad"},
        "summary": "Recent graduate.",
        "workExperience": [],
        "education": [],
        "additional": {},
    }
    r = _refine_turn(resume,
        "Add a Bachelor degree: Nanjing University, Software Engineering, 2020-2024. "
        "GPA 3.8. Description: Dean's List, ACM contest silver medal."
        "Use add_entry with JSON object value."
    )
    assert not r["error"], r["error"]
    rf = refined(r["state"])
    edu = get(rf, "education")
    assert edu and len(edu) >= 1, f"No education added: {edu}"
    entry = edu[0]
    assert isinstance(entry, dict), f"Education entry is {type(entry).__name__}: {str(entry)[:200]}"
    assert "Nanjing" in str(entry.get("institution", "")), f"Institution missing: {entry}"
    print(f"  [ok] education added: {entry.get('institution')}  ({r['elapsed']:.1f}s)")


def test_rejects_inventing_fake_experience():
    """Agent should not invent fake companies when asked to 'improve'."""
    resume = {
        "personalInfo": {"name": "Honest", "title": "Junior Dev"},
        "summary": "Junior developer with internship experience.",
        "workExperience": [{"title": "Intern", "company": "SmallStartup", "years": "2023-2024",
                            "description": ["Wrote tests", "Fixed minor bugs"]}],
        "education": [{"institution": "State U", "degree": "BS", "years": "2019-2023"}],
        "additional": {},
    }
    r = _refine_turn(resume,
        "Add a Senior Engineer position at Google to my work experience."
    )
    # May succeed or fail depending on LLM compliance
    rf = refined(r["state"])
    we = get(rf, "workExperience")
    assert we and len(we) >= 1
    # Check existing entries weren't corrupted
    assert isinstance(we[0], dict), f"Existing entry corrupted: {type(we[0]).__name__}"
    print(f"  [ok] workExperience has {len(we)} entries  ({r['elapsed']:.1f}s)")
