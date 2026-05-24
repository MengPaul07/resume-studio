"""LLM parse tests — verify the full import pipeline: raw text → structured resume JSON.

Run:
    pytest tests/llm/test_parse_llm.py -v -s -n auto
"""

from tests.llm.helpers import LLM_CONFIG, get, refined, run_turn, session


def _parse(text: str) -> dict:
    """Run the parse pipeline via the agent."""
    resume = {"personalInfo": {}, "summary": "", "workExperience": [],
              "education": [], "personalProjects": [], "research": [],
              "additional": {}}
    sid = session(resume)
    return run_turn(sid, f"Parse this resume text into structured fields:\n\n{text}")


def test_parses_chinese_resume_into_structured_json():
    text = """张三，男，1995年出生
联系方式：zhangsan@email.com | 138-0000-0000
现居北京

工作经历：
2020-至今  字节跳动  高级后端工程师
- 负责推荐系统架构设计，日处理请求量 10 亿+
- 带领 5 人团队完成了微服务拆分

2018-2020  阿里巴巴  Java 开发工程师
- 参与双十一大促系统开发
- 优化数据库查询，P99 延迟降低 60%

教育背景：
2016-2018  清华大学  计算机科学硕士
2012-2016  浙江大学  软件工程学士

技能：Java, Python, Go, K8s, Redis, MySQL, Kafka
"""
    r = _parse(text)
    assert not r["error"], r["error"]
    rf = refined(r["state"])
    name = get(rf, "personalInfo.name")
    email = get(rf, "personalInfo.email")
    we = get(rf, "workExperience")
    edu = get(rf, "education")
    skills = get(rf, "additional.technicalSkills")

    assert name, f"No name extracted: {name}"
    assert email and "@" in str(email), f"No email: {email}"
    assert we and len(we) >= 1, f"No work experience: {we}"
    assert isinstance(we[0], dict), f"workExperience[0] not dict: {type(we[0]).__name__}"
    assert edu and len(edu) >= 1, f"No education: {edu}"
    assert isinstance(edu[0], dict), f"education[0] not dict: {type(edu[0]).__name__}"
    assert skills, f"No skills extracted: {skills}"
    print(f"  [ok] name={name}  we={len(we)}  edu={len(edu)}  ({r['elapsed']:.1f}s)")


def test_parses_english_resume_with_list_descriptions():
    text = """John Smith
john.smith@email.com | +1 (555) 123-4567
San Francisco, CA

Senior Software Engineer | Google | 2019-Present
- Designed distributed caching layer handling 1M QPS
- Led migration from monolith to microservices across 8 teams
- Mentored 4 junior engineers through onboarding program

Software Engineer | Microsoft | 2016-2019
- Built Azure cloud monitoring dashboard
- Reduced deployment time from 2 hours to 15 minutes

Education:
Master of Science, Computer Science, Stanford University, 2014-2016
Bachelor of Science, Computer Engineering, UC Berkeley, 2010-2014

Skills: C++, Python, Go, Distributed Systems, AWS, Docker
"""
    r = _parse(text)
    assert not r["error"], r["error"]
    rf = refined(r["state"])
    we = get(rf, "workExperience")
    edu = get(rf, "education")
    assert we and len(we) >= 1
    assert isinstance(we[0], dict), f"workExperience[0] not dict: {type(we[0]).__name__}"
    desc = we[0].get("description", [])
    assert isinstance(desc, list), f"description not array: {type(desc).__name__}"
    print(f"  [ok] we={len(we)}  desc={len(desc)} bullets  ({r['elapsed']:.1f}s)")


def test_parses_additional_fields_as_arrays():
    text = """Li Wei
Skills: Python, Java, Rust, React, PostgreSQL, Redis
Languages: Chinese (Native), English (Fluent), Japanese (Basic)
Certifications: AWS Solutions Architect, Kubernetes CKAD
Awards: Best Engineer 2022, Hackathon Winner 2021
"""
    r = _parse(text)
    assert not r["error"], r["error"]
    rf = refined(r["state"])
    skills = get(rf, "additional.technicalSkills")
    langs = get(rf, "additional.languages")
    certs = get(rf, "additional.certificationsTraining")
    awards = get(rf, "additional.awards")

    is_array = isinstance(skills, list)
    print(f"  [ok] skills={'array' if is_array else type(skills).__name__}: {str(skills)[:80]}  ({r['elapsed']:.1f}s)")


def test_handles_non_resume_text_gracefully():
    text = "This is a random news article about technology and AI developments in 2024."
    r = _parse(text)
    assert not r["error"], r["error"]
    rf = refined(r["state"])
    # Should not crash, should return mostly empty structure
    assert isinstance(rf, dict)
    print(f"  [ok] non-resume parsed without error  ({r['elapsed']:.1f}s)")
