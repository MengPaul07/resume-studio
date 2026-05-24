"""User Profile — persistent persona built from resume + conversation history.

Extracts a compact profile from the resume JSON and persists it to disk.
Injected into the LLM prompt for personalized editing guidance.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROFILES_DIR = Path(__file__).resolve().parents[2] / "data" / "user_profiles"
PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def _profile_path(resume: dict[str, Any]) -> Path:
    """Derive a stable profile path from resume content hash."""
    raw = json.dumps(resume, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:12]
    return PROFILES_DIR / f"{digest}.json"


# ── Extraction ────────────────────────────────────────────────────────────


def extract_profile(resume: dict[str, Any]) -> dict[str, Any]:
    """Build or update a user profile from resume JSON data."""
    profile: dict[str, Any] = {
        "target_roles": _extract_roles(resume),
        "industries": _extract_industries(resume),
        "years_of_experience": _extract_years(resume),
        "education_summary": _extract_education(resume),
        "skill_set": _extract_skills(resume),
        "language": "zh-CN",
        "style_notes": [],
    }
    return profile


def _extract_roles(resume: dict[str, Any]) -> list[str]:
    roles: list[str] = []
    for entry in resume.get("workExperience", []) or []:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title", "")).strip()
        if title and title not in roles:
            roles.append(title)
    return roles[:10]


def _extract_industries(resume: dict[str, Any]) -> list[str]:
    industries: list[str] = []
    for entry in resume.get("workExperience", []) or []:
        if not isinstance(entry, dict):
            continue
        company = str(entry.get("company", "")).strip()
        if company and company not in industries:
            industries.append(company)
    # Also check summary for industry keywords
    summary = str(resume.get("summary", "")).strip()
    industry_keywords = [
        "金融", "Fintech", "电商", "E-commerce", "云", "Cloud", "SaaS",
        "AI", "人工智能", "医疗", "Healthcare", "教育", "游戏", "Gaming",
        "广告", "AdTech", "物流", "供应链", "制造", "汽车",
    ]
    for kw in industry_keywords:
        if kw.lower() in summary.lower():
            industries.append(kw)
    return industries[:10]


def _extract_years(resume: dict[str, Any]) -> int:
    """Estimate total years of experience from work history."""
    years_texts: list[str] = []
    for entry in resume.get("workExperience", []) or []:
        if not isinstance(entry, dict):
            continue
        y = str(entry.get("years", "")).strip()
        if y:
            years_texts.append(y)

    import re
    all_years: list[int] = []
    for text in years_texts:
        nums = re.findall(r"\b(19\d{2}|20\d{2})\b", text)
        if len(nums) >= 2:
            all_years.append(int(nums[0]))
            all_years.append(int(nums[-1]))

    if len(all_years) >= 2:
        return max(all_years) - min(all_years)
    if all_years:
        return 2026 - min(all_years)
    return 0


def _extract_education(resume: dict[str, Any]) -> str:
    entries = resume.get("education", []) or []
    if not entries:
        return ""
    first = entries[0] if isinstance(entries[0], dict) else {}
    parts = [
        str(first.get("degree", "")).strip(),
        str(first.get("institution", "")).strip(),
    ]
    return "，".join(p for p in parts if p)


def _extract_skills(resume: dict[str, Any]) -> list[str]:
    additional = resume.get("additional", {}) or {}
    if not isinstance(additional, dict):
        return []
    skills = additional.get("technicalSkills", [])
    if isinstance(skills, str):
        return [s.strip() for s in skills.split(",") if s.strip()]
    if isinstance(skills, list):
        return [str(s).strip() for s in skills if str(s).strip()]
    return []


# ── Persistence ────────────────────────────────────────────────────────────


def load_profile(resume: dict[str, Any]) -> dict[str, Any] | None:
    """Load a previously saved profile for this resume."""
    path = _profile_path(resume)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_profile(resume: dict[str, Any], profile: dict[str, Any]) -> None:
    """Persist the profile to disk."""
    path = _profile_path(resume)
    try:
        path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("[profile] saved %s", path.name)
    except Exception as exc:
        logger.warning("[profile] save failed: %s", exc)


# ── Background update ───────────────────────────────────────────────────────


def update_profile_background(
    resume: dict[str, Any],
    accepted_items: list[dict[str, Any]] | None = None,
    rejected_items: list[dict[str, Any]] | None = None,
) -> None:
    """Fire-and-forget profile update — spawns a thread, returns immediately."""
    import threading

    def _run() -> None:
        try:
            profile = load_profile(resume)
            if profile is None:
                profile = extract_profile(resume)
            style_notes: list[str] = profile.get("style_notes", [])
            if accepted_items:
                for item in accepted_items:
                    path = str(item.get("path", ""))
                    reason = str(item.get("reason", ""))
                    if reason:
                        style_notes.append(f"accepted: {path} — {reason}")
            if rejected_items:
                for item in rejected_items:
                    path = str(item.get("path", ""))
                    reason = str(item.get("reason", ""))
                    if reason:
                        style_notes.append(f"rejected: {path} — {reason}")
            # Keep last 20 notes
            profile["style_notes"] = style_notes[-20:]
            save_profile(resume, profile)
        except Exception as exc:
            logger.warning("[profile] background update failed: %s", exc)

    t = threading.Thread(target=_run, daemon=True)
    t.start()


# ── Prompt injection ───────────────────────────────────────────────────────


def profile_to_prompt_text(profile: dict[str, Any]) -> str:
    """Format the profile as a compact text block for the LLM prompt."""
    if not profile or not any(profile.values()):
        return ""

    lines: list[str] = []
    roles = profile.get("target_roles", [])
    if roles:
        lines.append(f"目标岗位: {' / '.join(roles[:5])}")

    industries = profile.get("industries", [])
    if industries:
        lines.append(f"行业背景: {' / '.join(industries[:5])}")

    years = profile.get("years_of_experience", 0)
    if years:
        lines.append(f"工作年限: 约 {years} 年")

    edu = profile.get("education_summary", "")
    if edu:
        lines.append(f"教育: {edu}")

    skills = profile.get("skill_set", [])
    if skills:
        lines.append(f"技能: {', '.join(skills[:12])}")

    style_notes = profile.get("style_notes", [])
    if style_notes:
        lines.append(f"编辑偏好: {'; '.join(style_notes[-5:])}")

    return "\n".join(lines)


def ensure_profile(resume: dict[str, Any]) -> dict[str, Any]:
    """Load existing profile or build a new one from scratch."""
    existing = load_profile(resume)
    if existing:
        return existing
    profile = extract_profile(resume)
    save_profile(resume, profile)
    return profile
