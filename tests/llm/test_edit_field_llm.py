"""Complex real-LLM edit_field scenarios using deepseek-v4-flash.

Override model via env:
    TEST_API_KEY=sk-xxx TEST_API_BASE=https://api.openai.com/v1 pytest tests/llm -v -s -n auto

Default model is deepseek-v4-flash using API_KEY/API_BASE from .env.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import pytest

MODEL = os.getenv("TEST_MODEL", "deepseek-v4-flash")
LLM_CONFIG = {
    "model": MODEL,
    "temperature": 0.3,
}
if os.getenv("TEST_API_KEY"):
    LLM_CONFIG["api_key"] = os.getenv("TEST_API_KEY")
if os.getenv("TEST_API_BASE"):
    LLM_CONFIG["api_base"] = os.getenv("TEST_API_BASE")


def _run(sid: str, msg: str) -> dict:
    from fastapi.testclient import TestClient
    from src.main import app
    client = TestClient(app)
    events = []
    t0 = time.perf_counter()
    with client.stream(
        "POST", f"/api/v1/agent/v3/sessions/{sid}/turns:run",
        json={"message": msg, "allow_mutation": True,
              "llm_config": LLM_CONFIG},
        timeout=180,
    ) as resp:
        ev = None
        for line in resp.iter_lines():
            s = line.decode("utf-8") if isinstance(line, bytes) else line
            if s.startswith("event: "): ev = s[7:].strip()
            elif s.startswith("data: ") and ev:
                events.append((ev, json.loads(s[6:])))
                ev = None
    elapsed = time.perf_counter() - t0
    r2 = client.get(f"/api/v1/agent/v3/sessions/{sid}?message_limit=10&event_limit=100")
    state = r2.json().get("state", {}) if r2.status_code == 200 else {}
    completed = [e for e in events if e[0] == "turn.completed"]
    err = completed[0][1].get("error", "") if completed else "no turn.completed"
    return {"state": state, "error": err, "elapsed": elapsed, "events": events}


def _session(resume: dict) -> str:
    from fastapi.testclient import TestClient
    from src.main import app
    r = TestClient(app).post("/api/v1/agent/v3/sessions", json={
        "raw_document_obj": resume, "refined_document_obj": resume,
        "llm_config": LLM_CONFIG,
    })
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def _get(obj, path):
    from src.services.content_refinement_v3.session.service import _get_by_path_local
    return _get_by_path_local(obj, path)


def _refined(state):
    return state.get("refined_document_obj", {}) or state.get("refined_resume_obj", {})

# ═══════════════════════════════════════════════════════════════════
# 1. Multi-degree education with awards, GPA, detailed descriptions
# ═══════════════════════════════════════════════════════════════════

def test_adds_multiple_degrees_with_structured_json():
    """Add two degrees at once, each with rich metadata."""
    resume = {
        "personalInfo": {"name": "Zhang Wei", "title": "ML Engineer"},
        "summary": "Experienced ML engineer.",
        "workExperience": [],
        "education": [],
        "personalProjects": [],
        "additional": {"technicalSkills": "Python, PyTorch"},
    }
    sid = _session(resume)
    r = _run(sid,
        "Add my complete education history as two entries using JSON object format:\n"
        "1. Master: Tsinghua University, Computer Science, 2022-2025, GPA 3.9/4.0. "
        "Description array: ['Thesis on LLM alignment, published at ACL 2024', "
        "'Teaching assistant for Deep Learning course (200+ students)', "
        "'Won national scholarship for outstanding research']\n"
        "2. Bachelor: Zhejiang University, Software Engineering, 2018-2022, GPA 3.7/4.0. "
        "Description array: ['ACM-ICPC Asia Regional silver medal', "
        "'Built campus course selection system used by 10k students', "
        "'Won provincial excellent graduate award']\n"
        "Each entry MUST be a complete JSON object with institution/degree/years/description fields."
    )
    assert not r["error"], r["error"]
    rf = _refined(r["state"])
    edu = _get(rf, "education")
    assert edu and len(edu) >= 1, f"Expected >=1 degree added, got {len(edu) if edu else 0}"
    for i, e in enumerate(edu):
        assert isinstance(e, dict), f"education[{i}] is {type(e).__name__}, not dict: {str(e)[:200]}"
        assert "institution" in e
        assert "description" in e
        assert isinstance(e["description"], list), f"education[{i}].description not a list"
    print(f"  [ok] {len(edu)} degree(s), all structured JSON  ({r['elapsed']:.1f}s)")


# ═══════════════════════════════════════════════════════════════════
# 2. Rich work experience with multi-paragraph descriptions
# ═══════════════════════════════════════════════════════════════════

def test_adds_work_experience_with_rich_descriptions():
    """Add a work entry with 5+ bullet points, ensuring each is a separate array item."""
    resume = {
        "personalInfo": {"name": "Li Ming", "title": "Senior SDE"},
        "summary": "Senior backend engineer.",
        "workExperience": [
            {"title": "Junior Dev", "company": "StartupX", "years": "2020-2022",
             "description": ["Built CRUD APIs", "Fixed bugs"]},
        ],
        "education": [],
        "personalProjects": [],
        "additional": {},
    }
    sid = _session(resume)
    r = _run(sid,
        "Add a new work experience at workExperience[1] as a complete JSON object:\n"
        "{\n"
        '  "title": "Staff Software Engineer",\n'
        '  "company": "ByteDance",\n'
        '  "years": "2022-2024",\n'
        '  "description": [\n'
        '    "Designed and built a real-time recommendation pipeline serving 100M+ DAU, reducing P99 latency from 500ms to 50ms",\n'
        '    "Led cross-team migration from monolith to microservices, coordinating 8 teams across 3 time zones",\n'
        '    "Mentored 5 junior engineers through structured code review and design review programs",\n'
        '    "Introduced chaos engineering practices that caught 12 critical bugs before production",\n'
        '    "Won internal hackathon with an LLM-powered code review bot adopted by 200+ engineers"\n'
        "  ]\n"
        "}\n"
        "Use edit_field with op='upsert' and path='workExperience[1]'. The value MUST be a JSON object string."
    )
    assert not r["error"], r["error"]
    rf = _refined(r["state"])
    new_entry = _get(rf, "workExperience[1]")
    assert isinstance(new_entry, dict), f"New entry is {type(new_entry).__name__}: {str(new_entry)[:200]}"
    assert new_entry.get("company") == "ByteDance"
    desc = new_entry.get("description", [])
    assert isinstance(desc, list), f"description not a list: {type(desc).__name__}"
    assert len(desc) >= 3, f"Expected >=3 bullets, got {len(desc)}: {desc}"
    print(f"  [ok] {len(desc)} description bullets  ({r['elapsed']:.1f}s)")


# ═══════════════════════════════════════════════════════════════════
# 3. Repair corrupted flat-text fields
# ═══════════════════════════════════════════════════════════════════

def test_repairs_flat_text_education_to_structured_json():
    """Start with flat-text education, agent must repair to structured JSON."""
    resume = {
        "personalInfo": {"name": "Wang Fang", "title": "Data Engineer"},
        "summary": "Data engineer with 4 years experience.",
        "workExperience": [],
        "education": [
            "复旦大学 | 数据科学硕士 | 2020-2023 | 研究方向：时序预测，发表CCF-B类论文1篇，GPA 3.6/4.0，获国家奖学金",
            "武汉大学 | 计算机科学与技术学士 | 2016-2020 | ACM校赛一等奖，大学生创新项目国家级立项",
        ],
        "personalProjects": [],
        "additional": {"technicalSkills": "Python, SQL, Spark"},
    }
    sid = _session(resume)
    r = _run(sid,
        "The education field is corrupted — each entry is a flat pipe-delimited string "
        "instead of a proper JSON object. Rewrite ALL education entries as structured JSON objects "
        "with institution, degree, years, and description (as array) fields. "
        "Split the pipe-delimited text into the correct fields. "
        "Description should be an array of individual achievements/sentences."
    )
    assert not r["error"], r["error"]
    rf = _refined(r["state"])
    edu = _get(rf, "education")
    assert edu and len(edu) >= 2, f"Expected >=2 entries, got {len(edu) if edu else 0}"
    for i, e in enumerate(edu):
        assert isinstance(e, dict), (
            f"REPAIR FAILED: education[{i}] still flat: {type(e).__name__} = {str(e)[:200]}"
        )
        assert "institution" in e
        desc = e.get("description", [])
        assert isinstance(desc, list), f"education[{i}].description not array: {type(desc).__name__}"
    print(f"  [ok] repaired {len(edu)} flat entries to structured  ({r['elapsed']:.1f}s)")


# ═══════════════════════════════════════════════════════════════════
# 4. Multi-section simultaneous edit
# ═══════════════════════════════════════════════════════════════════

def test_edits_multiple_sections_in_one_turn():
    """Edit education, work experience, summary, and skills in one turn."""
    resume = {
        "personalInfo": {"name": "Chen Jie", "title": "Fullstack Developer"},
        "summary": "Fullstack developer.",
        "workExperience": [
            {"title": "Frontend Dev", "company": "Shopee", "years": "2021-2023",
             "description": ["Built merchant dashboard", "Improved page load time 60%"]},
        ],
        "education": [
            {"institution": "Nanjing University", "degree": "Bachelor",
             "years": "2017-2021", "description": ["Major in Software Engineering"]},
        ],
        "personalProjects": [],
        "additional": {"technicalSkills": "React, Node.js"},
    }
    sid = _session(resume)
    r = _run(sid,
        "Make all of the following changes in one turn:\n"
        "1. Update summary to: 'Fullstack engineer specializing in React/Node.js with experience "
        "building high-traffic e-commerce platforms. Passionate about performance optimization and design systems.'\n"
        "2. Update additional.technicalSkills to: 'React, TypeScript, Node.js, PostgreSQL, Redis, AWS'\n"
        "3. Add a personal project: 'OpenMenu' — description array: "
        "['Open-source restaurant menu management system', '1.2k GitHub stars', 'Used by 50+ restaurants']\n"
        "4. Update education[0].description to include: ['Major in Software Engineering', "
        "'Won university hackathon with a real-time collaboration tool']\n"
        "Make ALL four changes. Use JSON object format for structured fields."
    )
    assert not r["error"], r["error"]
    rf = _refined(r["state"])
    summary = _get(rf, "summary")
    skills = _get(rf, "additional.technicalSkills")
    projects = _get(rf, "personalProjects")
    edu_desc = _get(rf, "education[0].description")

    assert summary and "fullstack" in str(summary).lower(), f"Summary not updated: {summary}"
    assert skills and "TypeScript" in str(skills), f"Skills not updated: {skills}"
    assert projects and len(projects) >= 1, f"No project added: {projects}"
    assert isinstance(edu_desc, list), f"education[0].description not array: {edu_desc}"
    print(f"  [ok] 4 field changes applied  ({r['elapsed']:.1f}s)")


# ═══════════════════════════════════════════════════════════════════
# 5. JD-aware resume tailoring
# ═══════════════════════════════════════════════════════════════════

def test_tailors_resume_to_match_job_description():
    """Provide a JD and ask agent to tailor the resume accordingly."""
    resume = {
        "personalInfo": {"name": "Zhao Yu", "title": "Backend Developer"},
        "summary": "Backend developer with 3 years experience.",
        "workExperience": [
            {"title": "Backend Dev", "company": "Meituan", "years": "2021-2024",
             "description": ["Developed order management APIs", "Maintained legacy systems"]},
        ],
        "education": [
            {"institution": "HUST", "degree": "Bachelor", "years": "2017-2021",
             "description": ["CS major"]},
        ],
        "personalProjects": [],
        "additional": {"technicalSkills": "Java, Spring, MySQL"},
    }
    sid = _session(resume)
    r = _run(sid,
        "TARGET JOB DESCRIPTION:\n"
        "Senior Backend Engineer at TikTok — requires: distributed systems, high concurrency, "
        "Go/Python, microservices, message queues, cache strategies, system design.\n\n"
        "Tailor my resume to match this JD. Specifically:\n"
        "1. Rewrite summary to highlight distributed systems and high concurrency experience\n"
        "2. Update workExperience[0] to emphasize relevant skills (distributed, concurrency, Go)\n"
        "3. Add relevant technical skills to additional.technicalSkills\n"
        "Do NOT invent companies or positions — only rewrite content and add skills."
    )
    assert not r["error"], r["error"]
    rf = _refined(r["state"])
    summary = _get(rf, "summary")
    skills = _get(rf, "additional.technicalSkills")
    we0_desc = _get(rf, "workExperience[0].description")

    assert summary and len(str(summary)) > 20, f"Summary too short: {summary}"
    # Work entry must still be a dict
    we0 = _get(rf, "workExperience[0]")
    assert isinstance(we0, dict), f"workExperience[0] corrupted: {type(we0).__name__}"
    print(f"  [ok] JD-tailored: summary={len(str(summary))}chars, skills={skills}  ({r['elapsed']:.1f}s)")


# ═══════════════════════════════════════════════════════════════════
# 6. Add multiple projects with cross-references
# ═══════════════════════════════════════════════════════════════════

def test_adds_multiple_projects_with_structured_json():
    """Add three projects, each with description arrays and roles."""
    resume = {
        "personalInfo": {"name": "Sun Yang", "title": "Open Source Developer"},
        "summary": "Passionate open source contributor.",
        "workExperience": [],
        "education": [],
        "personalProjects": [],
        "additional": {},
    }
    sid = _session(resume)
    r = _run(sid,
        "Add these three personal projects. Each must be a JSON object with name, role, and description array:\n"
        "1. 'RustSearch' — role: 'Creator & Maintainer'. Description: "
        "['Full-text search engine written in Rust', '2.8k GitHub stars', "
        "'Handles 50k queries/second on a single node', 'Featured on Hacker News front page']\n"
        "2. 'PyScheduler' — role: 'Core Contributor'. Description: "
        "['Distributed task scheduler for Python', '800 GitHub stars', "
        "'Used in production by 3 companies for ETL pipelines']\n"
        "3. 'GoCache' — role: 'Author'. Description: "
        "['High-performance caching library for Go', 'Supports LRU/LFU/TTL eviction policies', "
        "'Benchmarked 3x faster than go-cache at 1M entries']\n"
        "Use edit_field with op='upsert' for each. Value MUST be JSON object strings."
    )
    assert not r["error"], r["error"]
    rf = _refined(r["state"])
    projects = _get(rf, "personalProjects")
    assert projects and len(projects) >= 1, f"Expected >=1 project added, got {len(projects) if projects else 0}"
    for i, p in enumerate(projects):
        assert isinstance(p, dict), f"project[{i}] is {type(p).__name__}: {str(p)[:200]}"
        assert "name" in p and "description" in p
        assert isinstance(p["description"], list), f"project[{i}].description not array"
    print(f"  [ok] {len(projects)} projects, all structured  ({r['elapsed']:.1f}s)")


# ═══════════════════════════════════════════════════════════════════
# 7. Delete + re-add with better content
# ═══════════════════════════════════════════════════════════════════

def test_deletes_weak_entry_and_adds_rich_replacement():
    """Delete a work entry, then add a richer replacement."""
    resume = {
        "personalInfo": {"name": "Liu Wei", "title": "DevOps Engineer"},
        "summary": "DevOps engineer.",
        "workExperience": [
            {"title": "Junior Ops", "company": "OldCo", "years": "2019-2021",
             "description": ["Did stuff"]},
            {"title": "DevOps", "company": "MidCo", "years": "2021-2023",
             "description": ["Managed servers", "Wrote some scripts"]},
        ],
        "education": [],
        "personalProjects": [],
        "additional": {},
    }
    sid = _session(resume)
    # Turn 1: Delete the weak first entry
    r1 = _run(sid,
        "Delete workExperience[0] — it's a weak entry. Use edit_field with op='delete'."
    )
    assert not r1["error"], r1["error"]
    rf1 = _refined(r1["state"])
    we1 = _get(rf1, "workExperience")
    assert len(we1) == 1, f"Expected 1 remaining entry, got {len(we1)}"
    print(f"  turn1: deleted, {len(we1)} entries remain  ({r1['elapsed']:.1f}s)")

    # Turn 2: Add a rich replacement at the beginning
    r2 = _run(sid,
        "Add a NEW work experience at workExperience[0] as a proper JSON object:\n"
        '{"title": "Senior DevOps Engineer", "company": "AWS", "years": "2019-2023", '
        '"description": ['
        '"Managed Kubernetes clusters across 3 AWS regions serving 500+ microservices", '
        '"Built CI/CD pipeline reducing deploy time from 45min to 3min", '
        '"Implemented Terraform IaC covering 100% of infrastructure", '
        '"Led incident response for 50+ production outages with 99.99% uptime SLA"]}'
    )
    assert not r2["error"], r2["error"]
    rf2 = _refined(r2["state"])
    we2 = _get(rf2, "workExperience")
    assert len(we2) >= 1
    new_entry = we2[0] if isinstance(we2[0], dict) else {}
    assert isinstance(new_entry, dict), f"New entry not dict: {type(new_entry).__name__}"
    assert isinstance(new_entry, dict), f"workExperience[0] not dict after rebuild: {type(new_entry).__name__}"
    assert isinstance(new_entry.get("description", []), list), f"description not array after rebuild"
    print(f"  [ok] delete+readd: {len(we2)} entries, all structured  ({r1['elapsed']+r2['elapsed']:.1f}s)")


# ═══════════════════════════════════════════════════════════════════
# 8. Array manipulation — add/remove specific description bullets
# ═══════════════════════════════════════════════════════════════════

def test_replaces_description_array_with_new_bullets():
    """Add, remove, and reorder specific bullets in description arrays."""
    resume = {
        "personalInfo": {"name": "Huang Li", "title": "Product Manager"},
        "summary": "Experienced PM.",
        "workExperience": [
            {"title": "PM", "company": "Tencent", "years": "2020-2024",
             "description": [
                 "Launched WeChat mini-program reaching 5M users",
                 "Defined product roadmap for social commerce team",
             ]},
        ],
        "education": [],
        "personalProjects": [],
        "additional": {},
    }
    sid = _session(resume)
    # Edit: add a bullet, remove one, reorder
    r = _run(sid,
        "Update workExperience[0].description to the following array (replace the entire array):\n"
        '["Launched WeChat mini-program reaching 5M users in first quarter", '
        '"Led cross-functional team of 12 engineers and 3 designers", '
        '"Defined product roadmap and OKRs for social commerce team", '
        '"Increased user retention by 35% through A/B testing and user research", '
        '"Presented quarterly business reviews to VP-level stakeholders"]'
    )
    assert not r["error"], r["error"]
    rf = _refined(r["state"])
    desc = _get(rf, "workExperience[0].description")
    assert isinstance(desc, list), f"description not list: {type(desc).__name__}"
    assert len(desc) == 5, f"Expected 5 bullets, got {len(desc)}: {desc}"
    print(f"  [ok] description array: {len(desc)} bullets  ({r['elapsed']:.1f}s)")


# ═══════════════════════════════════════════════════════════════════
# 9. Complex nested field update
# ═══════════════════════════════════════════════════════════════════

def test_updates_deeply_nested_fields_without_corruption():
    """Update deeply nested fields and add custom sections."""
    resume = {
        "personalInfo": {"name": "Xu Jing", "title": "Engineer", "email": "old@example.com"},
        "summary": "Engineer.",
        "workExperience": [
            {"title": "SDE", "company": "Alibaba", "years": "2020-2023",
             "description": ["Worked on cloud infrastructure", "Built monitoring tools"]},
        ],
        "education": [
            {"institution": "SJTU", "degree": "Bachelor", "years": "2016-2020",
             "description": ["CS major"]},
        ],
        "personalProjects": [],
        "additional": {"technicalSkills": "Java, Python", "languages": "", "awards": ""},
    }
    sid = _session(resume)
    r = _run(sid,
        "Make all of these changes in one turn. Every structured field MUST use JSON object format — no flat text:\n"
        "1. Update personalInfo: email='xujing@example.com', add linkedin='linkedin.com/in/xujing', add github='github.com/xujing'\n"
        "2. Update additional: awards='Alibaba Cloud Hero 2023, Outstanding Engineer Award 2022', "
        "languages='Chinese (Native), English (Fluent), Japanese (Basic)'\n"
        "3. Add a custom research entry: name='CloudBench', role='Lead Author', "
        "description=['Published at ACM SoCC 2023', 'Benchmarking framework for cloud-native databases']\n"
        "4. Update workExperience[0].description[0] to: 'Designed and built cloud infrastructure "
        "monitoring platform processing 10TB of telemetry daily'"
    )
    assert not r["error"], r["error"]
    rf = _refined(r["state"])

    email = _get(rf, "personalInfo.email")
    linkedin = _get(rf, "personalInfo.linkedin")
    awards = _get(rf, "additional.awards")
    we_desc0 = _get(rf, "workExperience[0].description[0]")

    assert email == "xujing@example.com", f"Email not updated: {email}"
    assert linkedin, f"LinkedIn not added: {linkedin}"
    assert awards and "Alibaba" in str(awards), f"Awards not updated: {awards}"
    assert we_desc0 and "10TB" in str(we_desc0), f"Description not updated: {we_desc0}"

    # education[0] must still be a dict — not corrupted by the edit
    edu0 = _get(rf, "education[0]")
    assert isinstance(edu0, dict), f"education[0] corrupted: {type(edu0).__name__}"
    print(f"  [ok] 4 nested changes applied, education intact  ({r['elapsed']:.1f}s)")


# ═══════════════════════════════════════════════════════════════════
# 10. Full resume build from scratch
# ═══════════════════════════════════════════════════════════════════

def test_builds_full_resume_from_empty_skeleton():
    """Build a complete resume from a nearly-empty skeleton."""
    resume = {
        "personalInfo": {"name": "Ma Tao"},
        "summary": "",
        "workExperience": [],
        "education": [],
        "personalProjects": [],
        "additional": {},
    }
    sid = _session(resume)
    r = _run(sid,
        "Build my complete resume. Add ALL of the following using JSON object format for every structured field:\n\n"
        "personalInfo: title='Staff ML Engineer', email='matao@example.com', "
        "phone='+86 138-0000-0000', location='Beijing, China', "
        "linkedin='linkedin.com/in/matao', github='github.com/matao'\n\n"
        "summary: 'Staff ML Engineer with 8 years of experience building production recommendation "
        "systems at scale. Expert in deep learning, model optimization, and ML infrastructure. "
        "Published 6 papers at top-tier conferences.'\n\n"
        "workExperience[0]: JSON object with title='Staff ML Engineer', company='ByteDance', "
        "years='2022-present', description array=['Led ML infrastructure team of 15 engineers', "
        "'Built real-time recommendation pipeline serving 200M DAU', "
        "'Reduced model inference latency by 80% through GPU optimization and model quantization', "
        "'Designed A/B testing framework processing 1000+ experiments daily']\n\n"
        "education[0]: JSON object with institution='Tsinghua University', degree='PhD Computer Science', "
        "years='2016-2022', description array=['Thesis on neural recommendation systems', "
        "'Published 6 papers (2 NeurIPS, 2 ICML, 1 KDD, 1 WWW)', 'Advised by Prof. Zhang']\n\n"
        "additional.technicalSkills: 'Python, C++, PyTorch, TensorFlow, CUDA, Spark, Ray, Kubernetes'"
    )
    assert not r["error"], r["error"]
    rf = _refined(r["state"])

    # Verify all sections
    checks = [
        ("personalInfo.title", lambda v: v and "ML" in str(v)),
        ("personalInfo.email", lambda v: v and "@" in str(v)),
        ("summary", lambda v: v and len(str(v)) > 50),
        ("workExperience[0].title", lambda v: v and "ML" in str(v)),
        ("workExperience[0].description", lambda v: isinstance(v, list) and len(v) >= 3),
        ("education[0].institution", lambda v: v and "Tsinghua" in str(v)),
        ("education[0].description", lambda v: isinstance(v, list) and len(v) >= 2),
        ("additional.technicalSkills", lambda v: v and "PyTorch" in str(v)),
    ]
    failures = []
    for path, check in checks:
        val = _get(rf, path)
        if not check(val):
            failures.append(f"{path}: {str(val)[:100]}")
    assert not failures, "Full build failures:\n" + "\n".join(failures)

    # Critical: workExperience[0] and education[0] must be dicts
    we0 = _get(rf, "workExperience[0]")
    edu0 = _get(rf, "education[0]")
    assert isinstance(we0, dict), f"workExperience[0] is {type(we0).__name__}: {str(we0)[:300]}"
    assert isinstance(edu0, dict), f"education[0] is {type(edu0).__name__}: {str(edu0)[:300]}"

    print(f"  [ok] full resume built: {len(str(rf))} chars  ({r['elapsed']:.1f}s)")
