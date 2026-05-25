"""LLM-based LaTeX conversion comparison tests. Requires TEST_API_KEY env var."""
from __future__ import annotations

import difflib
import json
import os
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.latex_gen import render_tex
from src.services.layout_design.nodes.common import render_single_column_template_html

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "resumes"

DEFAULT_GUIDANCE = {
    "pageFormat": "a4",
    "pageCountMode": "single-page",
    "columnMode": "double",
    "headerLayout": "left",
    "contactLayout": "inline",
    "sectionHeadingStyle": "underline",
    "sectionHeadingCase": "uppercase",
    "dateStyle": "muted",
    "bulletStyle": "disc",
    "showHeaderDivider": True,
    "accentColor": "31457f",
    "bodyTextColor": "1d1d1f",
    "metaTextColor": "5f6b7a",
    "headerTextColor": "1d1d1f",
    "headerBgColor": "ffffff",
    "leftSidebarBg": "fafafa",
    "headerDividerColor": "d1d1d1",
    "tagBgColor": "f5f5f5",
    "tagBorderColor": "e5e5e5",
    "bodyFontSizePx": 12,
    "nameFontSizePx": 32,
    "roleFontSizePx": 14,
    "metaFontSizePx": 12,
    "sectionHeadingSizePx": 12,
    "tagFontSizePx": 10,
    "bodyFont": "sans-serif",
    "headerFont": "serif",
    "lineHeightPercent": 155,
    "compactLevel": 0,
    "sectionGapPx": 18,
    "itemGapPx": 10,
    "headingMarginBottomPx": 8,
    "sectionUnderlineGapPx": 4,
    "sectionUnderlineThicknessPx": 1,
    "headerMarginBottomPx": 14,
    "headerPaddingBottomPx": 8,
    "roleMarginTopPx": 6,
    "contactGapPx": 4,
    "pagePaddingPx": 36,
    "bulletIndentPx": 18,
    "bulletListTopGapPx": 3,
    "bulletItemGapPx": 6,
    "tagGapPx": 6,
    "tagPaddingXPx": 8,
    "tagPaddingYPx": 2,
    "tagRadiusPx": 12,
    "tagBorderWidthPx": 1,
    "sidebarPaddingPx": 8,
    "sidebarRadiusPx": 4,
    "columnGapPx": 16,
    "leftWidthPercent": 36,
    "headerDividerThicknessPx": 1,
    "margins": {"top": 12, "right": 12, "bottom": 12, "left": 12},
}

DEFAULT_SECTIONS = [
    {"key": "summary", "title": "Summary", "visible": True, "column": "left"},
    {"key": "technicalSkills", "title": "Skills", "visible": True, "column": "left"},
    {"key": "languages", "title": "Languages", "visible": True, "column": "left"},
    {"key": "certifications", "title": "Certifications", "visible": True, "column": "left"},
    {"key": "awards", "title": "Awards", "visible": True, "column": "left"},
    {"key": "workExperience", "title": "Work Experience", "visible": True, "column": "right"},
    {"key": "education", "title": "Education", "visible": True, "column": "right"},
    {"key": "personalProjects", "title": "Projects", "visible": True, "column": "right"},
]


def load_fixture(name: str) -> dict:
    with open(FIXTURE_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _count_structures(tex: str) -> dict:
    return {
        "sections": len(re.findall(r"\\cvsection\{", tex)),
        "experience_entries": len(re.findall(r"\\expheader\{", tex)),
        "bullet_items": len(re.findall(r"\\item\s", tex)),
        "tags": len(re.findall(r"\\cvtag\{", tex)),
        "total_chars": len(tex),
        "total_lines": len(tex.splitlines()),
    }


def _check_coverage(tex: str, terms: list[str]) -> dict[str, bool]:
    return {term: term.lower() in tex.lower() for term in terms}


@pytest.mark.skipif(
    not os.getenv("TEST_API_KEY") and not os.getenv("API_KEY"),
    reason="No API key available for LLM test",
)
class TestLlmLatexConversion:
    def test_produces_valid_tex(self):
        resume = load_fixture("full_stack_en.json")
        html = render_single_column_template_html(resume, DEFAULT_GUIDANCE, page_count_mode="single-page", target_pages=1)
        client = TestClient(app)
        r = client.post("/api/v1/agent/v3/html-to-latex", json={"html": html})
        assert r.status_code == 200, r.text
        latex = r.json().get("latex", "")
        assert latex
        assert "\\begin{document}" in latex
        assert "\\end{document}" in latex

    def test_preserves_content(self):
        resume = load_fixture("full_stack_en.json")
        html = render_single_column_template_html(resume, DEFAULT_GUIDANCE, page_count_mode="single-page", target_pages=1)
        client = TestClient(app)
        r = client.post("/api/v1/agent/v3/html-to-latex", json={"html": html})
        latex = r.json().get("latex", "")
        assert "Alex Chen" in latex or "Alex" in latex
        assert "section" in latex.lower()

    def test_compare_structure(self):
        resume = load_fixture("full_stack_en.json")
        html = render_single_column_template_html(resume, DEFAULT_GUIDANCE, page_count_mode="single-page", target_pages=1)
        tex_direct = render_tex(resume, DEFAULT_GUIDANCE, DEFAULT_SECTIONS, html_source=html)

        client = TestClient(app)
        r = client.post("/api/v1/agent/v3/html-to-latex", json={"html": html})
        tex_llm = r.json().get("latex", "") if r.status_code == 200 else ""

        direct_stats = _count_structures(tex_direct)
        llm_stats = _count_structures(tex_llm)

        print("\n=== Direct (Jinja2) vs LLM Structure ===")
        print(f"{'Metric':<25} {'Direct':>8} {'LLM':>8}")
        print("-" * 43)
        for key in direct_stats:
            print(f"{key:<25} {direct_stats[key]:>8} {llm_stats.get(key, 0):>8}")

        assert direct_stats["sections"] > 0

    def test_compare_quality(self):
        resume = load_fixture("full_stack_en.json")
        html = render_single_column_template_html(resume, DEFAULT_GUIDANCE, page_count_mode="single-page", target_pages=1)
        tex_direct = render_tex(resume, DEFAULT_GUIDANCE, DEFAULT_SECTIONS, html_source=html)

        client = TestClient(app)
        r = client.post("/api/v1/agent/v3/html-to-latex", json={"html": html})
        tex_llm = r.json().get("latex", "") if r.status_code == 200 else ""

        key_terms = ["Alex Chen", "TechCorp", "Python", "TypeScript", "University of Washington",
                     "FastAPI", "React", "AWS", "PostgreSQL"]
        direct_cov = _check_coverage(tex_direct, key_terms)
        llm_cov = _check_coverage(tex_llm, key_terms)

        print("\n=== Content Coverage ===")
        for term in key_terms:
            print(f"  {term:<30} Direct: {'Y' if direct_cov[term] else 'N'}  LLM: {'Y' if llm_cov[term] else 'N'}")

        diff = difflib.unified_diff(
            tex_direct.splitlines(keepends=True),
            tex_llm.splitlines(keepends=True),
            fromfile="Direct (Jinja2)",
            tofile="LLM",
            n=1,
        )
        diff_text = "".join(list(diff)[:100])
        if diff_text:
            print("\n=== First 100 lines of diff ===")
            print(diff_text)
