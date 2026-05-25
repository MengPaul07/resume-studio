from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.main import app
from src.api.routes_v3 import _build_html_to_latex_messages, _strip_latex_code_fence
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


class TestLatexTexEndpoint:
    def test_with_full_data(self):
        client = TestClient(app)
        r = client.post("/api/v1/latex/tex", json={
            "resume_obj": load_fixture("full_stack_en.json"),
            "guidance": DEFAULT_GUIDANCE,
            "sections": DEFAULT_SECTIONS,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert "tex" in data
        assert len(data["tex"]) > 1000

    def test_with_empty_resume(self):
        client = TestClient(app)
        r = client.post("/api/v1/latex/tex", json={
            "resume_obj": {},
            "guidance": DEFAULT_GUIDANCE,
            "sections": DEFAULT_SECTIONS,
        })
        assert r.status_code == 200, r.text
        assert "tex" in r.json()

    def test_without_resume_obj_uses_default(self):
        client = TestClient(app)
        r = client.post("/api/v1/latex/tex", json={
            "guidance": DEFAULT_GUIDANCE,
            "sections": DEFAULT_SECTIONS,
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_with_html_source(self):
        client = TestClient(app)
        resume = load_fixture("full_stack_en.json")
        html = render_single_column_template_html(resume, DEFAULT_GUIDANCE, page_count_mode="single-page", target_pages=1)
        r = client.post("/api/v1/latex/tex", json={
            "resume_obj": resume,
            "guidance": DEFAULT_GUIDANCE,
            "sections": DEFAULT_SECTIONS,
            "html_source": html,
        })
        assert r.status_code == 200, r.text
        assert r.json()["tex"]


class TestHtmlToLatexEndpoint:
    def test_no_html_returns_error(self):
        client = TestClient(app)
        r = client.post("/api/v1/agent/v3/html-to-latex", json={})
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"

    def test_prompt_includes_style_contract_and_stability_rules(self):
        html = """
        <style>
          :root {
            --r-accent: #123456;
            --r-heading-size: 16px;
            --r-contact-gap: 8px;
          }
        </style>
        <main><h1>Ada Lovelace</h1><section><h2>Summary</h2><p>Builds reliable systems.</p></section></main>
        """
        messages = _build_html_to_latex_messages(
            html,
            {"sectionHeadingStyle": "bar", "dateStyle": "inline", "columnMode": "single"},
        )
        system = messages[0]["content"]

        assert "STYLE_CONTRACT_JSON" in system
        assert '"accent": "123456"' in system
        assert '"style": "bar"' in system
        assert '"date_layout": "title_row_right"' in system
        assert "Do not invent colors" in system
        assert "Preserve every visible resume text string exactly" in system

    def test_strips_markdown_code_fence_from_llm_output(self):
        raw = "```latex\n\\documentclass{article}\n\\begin{document}\nHi\n\\end{document}\n```"
        assert _strip_latex_code_fence(raw).startswith("\\documentclass")
        assert "```" not in _strip_latex_code_fence(raw)


class TestLatexRoundTrip:
    """Verify that render_tex output matches the API endpoint."""

    def test_direct_call_matches_endpoint(self):
        resume = load_fixture("full_stack_en.json")
        tex_direct = render_tex(resume, DEFAULT_GUIDANCE, DEFAULT_SECTIONS)

        client = TestClient(app)
        r = client.post("/api/v1/latex/tex", json={
            "resume_obj": resume,
            "guidance": DEFAULT_GUIDANCE,
            "sections": DEFAULT_SECTIONS,
        })
        tex_api = r.json()["tex"]

        assert tex_direct == tex_api, "Direct render_tex call differs from API response"
