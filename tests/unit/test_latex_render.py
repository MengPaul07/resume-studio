from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.services.latex_gen import build_latex_style_context, render_tex
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


# ── existing tests ──────────────────────────────────────────────────


def test_render_tex_matches_css_html_mode_with_full_stack_fixture():
    resume_obj = json.loads(
        (Path(__file__).parent.parent / "fixtures/resumes/full_stack_en.json").read_text(encoding="utf-8")
    )
    guidance = {
        "pageFormat": "A4",
        "columnMode": "double",
        "headerFont": "serif",
        "bodyFont": "sans-serif",
        "headerLayout": "left",
        "nameFontSizePx": 32,
        "roleFontSizePx": 14,
        "metaFontSizePx": 12,
        "leftWidthPercent": 36,
        "sectionGapPx": 10,
        "bodyFontSizePx": 13,
        "lineHeightPercent": 136,
        "sectionHeadingSizePx": 12,
        "sectionHeadingStyle": "underline",
        "sectionHeadingCase": "uppercase",
        "bulletStyle": "disc",
        "dateStyle": "bottom-inline",
        "columnGapPx": 9,
        "itemGapPx": 6,
        "showHeaderDivider": True,
        "tagFontSizePx": 10,
        "headingMarginBottomPx": 4,
        "sectionUnderlineGapPx": 4,
        "sectionUnderlineThicknessPx": 1,
        "contactGapPx": 2,
        "accentColor": "#31457f",
        "headerDividerColor": "#d1d1d1",
        "headerDividerThicknessPx": 1,
        "headerMarginBottomPx": 8,
        "headerPaddingBottomPx": 4,
        "roleMarginTopPx": 3,
        "bulletIndentPx": 18,
        "bulletListTopGapPx": 3,
        "bulletItemGapPx": 3,
        "tagGapPx": 3,
        "tagPaddingXPx": 8,
        "tagPaddingYPx": 2,
        "tagRadiusPx": 12,
        "tagBorderWidthPx": 1,
        "tagBorderColor": "#e5e5e5",
        "tagBgColor": "#f5f5f5",
        "sidebarPaddingPx": 8,
        "sidebarRadiusPx": 4,
        "leftSidebarBg": "#fafafa",
        "headerBgColor": "#ffffff",
        "headerTextColor": "#1d1d1f",
        "bodyTextColor": "#1d1d1f",
        "metaTextColor": "#5f6b7a",
        "nameFontWeight": 700,
        "contactLayout": "inline",
        "compactLevel": 0,
        "margins": {"top": 12, "bottom": 12, "left": 12, "right": 12},
    }
    sections = [
        {"id": "summary", "key": "summary", "title": "Summary", "visible": True, "column": "left"},
        {"id": "technicalSkills", "key": "technicalSkills", "title": "Skills", "visible": True, "column": "left"},
        {"id": "languages", "key": "languages", "title": "Languages", "visible": True, "column": "left"},
        {"id": "certifications", "key": "certifications", "title": "Certifications", "visible": True, "column": "left"},
        {"id": "awards", "key": "awards", "title": "Awards", "visible": True, "column": "left"},
        {"id": "workExperience", "key": "workExperience", "title": "Work Experience", "visible": True, "column": "right"},
        {"id": "education", "key": "education", "title": "Education", "visible": True, "column": "right"},
        {"id": "personalProjects", "key": "personalProjects", "title": "Projects", "visible": True, "column": "right"},
    ]
    html_source = """
    <style>
      :root {
        --r-page-padding: 45px;
        --r-body-font: "Inter", "Segoe UI", sans-serif;
        --r-header-font: Georgia, serif;
        --r-body-color: #1d1d1f;
        --r-meta-color: #5f6b7a;
        --r-accent: #31457f;
        --r-accent-muted: #e5e5e5;
        --r-header-bg: #ffffff;
        --r-header-color: #1d1d1f;
        --r-sidebar-bg: #fafafa;
        --r-divider-color: #d1d1d1;
        --r-divider-thick: 1px;
        --r-tag-border: #e5e5e5;
        --r-tag-bg: #f5f5f5;
        --r-name-size: 32px;
        --r-role-size: 14px;
        --r-meta-size: 12px;
        --r-body-size: 13px;
        --r-line-height: 1.36;
        --r-section-gap: 10px;
        --r-item-gap: 6px;
        --r-heading-size: 12px;
        --r-heading-margin: 4px;
        --r-heading-rule-gap: 4px;
        --r-heading-rule-thick: 1px;
        --r-header-margin: 8px;
        --r-header-pad: 4px;
        --r-role-mt: 3px;
        --r-contact-gap: 2px;
        --r-col-gap: 9px;
        --r-left-basis: 248px;
        --r-bullet-top-gap: 3px;
        --r-bullet-gap: 3px;
        --r-bullet-indent: 18px;
        --r-tag-gap: 3px;
        --r-tag-size: 10px;
        --r-tag-pad-x: 8px;
        --r-tag-pad-y: 2px;
        --r-tag-radius: 12px;
        --r-tag-border-width: 1px;
        --r-sidebar-pad: 8px;
      }
    </style>
    """

    tex = render_tex(resume_obj, guidance, sections, html_source=html_source)

    assert "\\definecolor{sidebarbg}{HTML}{ FAFAFA }" in tex
    assert "\\usepackage[hmargin=11.91mm,vmargin=11.91mm]{geometry}" in tex
    assert "\\setmainfont{ TeX Gyre Heros }[Scale=MatchLowercase]" in tex
    assert "\\setmainfontTeX" not in tex
    assert "\\colorbox{sidebarbg}{" in tex
    assert "\\begin{minipage}[t]{ \\dimexpr" in tex
    assert "\\fontsize{ 9.75 }{ 13.3 }\\selectfont" in tex
    assert "\\fontsize{ 24.0 }{ 28.8 }\\selectfont" in tex
    assert "itemsep= 1.125 pt" in tex
    assert "\\rule{\\linewidth}{0.75pt}" in tex
    assert "arc=9.0pt" in tex
    assert "left=6.0pt" in tex
    assert "\\vspace{ 6.0 pt}" in tex
    assert "Alex Chen" in tex
    assert "Senior Software Engineer" in tex
    assert "\\cvtag{ Python }" in tex


def test_render_tex_honors_section_order_field_when_input_is_shuffled():
    resume_obj = json.loads(
        (Path(__file__).parent.parent / "fixtures/resumes/full_stack_en.json").read_text(encoding="utf-8")
    )
    guidance = {
        "columnMode": "double",
        "headerFont": "serif",
        "bodyFont": "sans-serif",
        "sectionHeadingStyle": "underline",
        "sectionHeadingCase": "uppercase",
        "dateStyle": "bottom-inline",
        "bulletStyle": "disc",
        "contactLayout": "inline",
        "showHeaderDivider": True,
        "margins": {"top": 12, "bottom": 12, "left": 12, "right": 12},
    }
    sections = [
        {"id": "projects", "key": "personalProjects", "title": "Projects", "visible": True, "column": "right", "order": 4},
        {"id": "skills", "key": "technicalSkills", "title": "Skills", "visible": True, "column": "left", "order": 1},
        {"id": "summary", "key": "summary", "title": "Summary", "visible": True, "column": "left", "order": 0},
        {"id": "education", "key": "education", "title": "Education", "visible": True, "column": "right", "order": 3},
        {"id": "work", "key": "workExperience", "title": "Work Experience", "visible": True, "column": "right", "order": 2},
    ]

    tex = render_tex(resume_obj, guidance, sections)

    left_summary = tex.index("\\cvsection{ Summary }")
    left_skills = tex.index("\\cvsection{ Skills }")
    right_work = tex.index("\\cvsection{ Work Experience }")
    right_education = tex.index("\\cvsection{ Education }")
    right_projects = tex.index("\\cvsection{ Projects }")
    assert left_summary < left_skills
    assert right_work < right_education < right_projects


# ── new unit tests ──────────────────────────────────────────────────


class TestLatexRenderer:
    def test_style_adapter_maps_css_vars_to_latex_context(self):
        html = """
        <style>
          :root {
            --r-accent: #123456;
            --r-heading-size: 16px;
            --r-contact-gap: 8px;
            --r-tag-radius: 4px;
            --r-left-basis: 280px;
          }
        </style>
        """
        ctx = build_latex_style_context(
            {**DEFAULT_GUIDANCE, "sectionHeadingStyle": "bar", "dateStyle": "inline"},
            html,
        )

        assert ctx["colors"]["accent"] == "123456"
        assert ctx["typography"]["heading_size"] == 12.0
        assert ctx["spacing"]["meta_gap"] == 6.0
        assert ctx["spacing"]["tag_radius"] == 3.0
        assert ctx["heading"]["style"] == "bar"
        assert ctx["entry"]["date_layout"] == "title_row_right"
        assert ctx["support"]["photo"] == "html_only"

    def test_produces_valid_tex(self):
        tex = render_tex(load_fixture("full_stack_en.json"), DEFAULT_GUIDANCE, DEFAULT_SECTIONS)
        assert tex
        assert "\\begin{document}" in tex
        assert "\\end{document}" in tex
        assert "Alex Chen" in tex

    def test_has_all_sections(self):
        tex = render_tex(load_fixture("full_stack_en.json"), DEFAULT_GUIDANCE, DEFAULT_SECTIONS)
        assert "Work Experience" in tex or "WORK EXPERIENCE" in tex
        assert "Education" in tex or "EDUCATION" in tex
        assert "Skills" in tex or "SKILLS" in tex

    def test_has_bullets(self):
        tex = render_tex(load_fixture("full_stack_en.json"), DEFAULT_GUIDANCE, DEFAULT_SECTIONS)
        assert "\\item" in tex
        assert len(re.findall(r"\\item\s", tex)) >= 10

    def test_has_tags(self):
        tex = render_tex(load_fixture("full_stack_en.json"), DEFAULT_GUIDANCE, DEFAULT_SECTIONS)
        assert "\\cvtag" in tex
        assert "Python" in tex

    def test_handles_chinese(self):
        resume_zh = load_fixture("full_stack_zh.json")
        tex = render_tex(resume_zh, DEFAULT_GUIDANCE, DEFAULT_SECTIONS)
        assert tex
        has_cjk = bool(re.search(r'[一-鿿㐀-䶿]', json.dumps(resume_zh, ensure_ascii=False)))
        if has_cjk:
            assert "xeCJK" in tex

    def test_escapes_special_chars(self):
        tex = render_tex(load_fixture("full_stack_en.json"), DEFAULT_GUIDANCE, DEFAULT_SECTIONS)
        body_match = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", tex, re.DOTALL)
        body = body_match.group(1) if body_match else tex
        assert "Unescaped &" not in _find_tex_issues(tex)

    def test_with_html_source(self):
        resume = load_fixture("full_stack_en.json")
        html = render_single_column_template_html(resume, DEFAULT_GUIDANCE, page_count_mode="single-page", target_pages=1)
        tex = render_tex(resume, DEFAULT_GUIDANCE, DEFAULT_SECTIONS, html_source=html)
        assert tex
        assert "31457F" in tex.upper()

    def test_all_heading_styles(self):
        resume = load_fixture("full_stack_en.json")
        for style in ["underline", "boxed", "bar", "plain"]:
            g = {**DEFAULT_GUIDANCE, "sectionHeadingStyle": style}
            tex = render_tex(resume, g, DEFAULT_SECTIONS)
            assert tex and "\\begin{document}" in tex, f"Failed for style: {style}"
            assert _has_balanced_tex_groups(tex), f"Unbalanced TeX groups for style: {style}"

    def test_date_style_controls_entry_header_layout(self):
        resume = load_fixture("full_stack_en.json")
        inline_tex = render_tex(resume, {**DEFAULT_GUIDANCE, "dateStyle": "inline"}, DEFAULT_SECTIONS)
        bottom_tex = render_tex(resume, {**DEFAULT_GUIDANCE, "dateStyle": "bottom-inline"}, DEFAULT_SECTIONS)
        muted_tex = render_tex(resume, {**DEFAULT_GUIDANCE, "dateStyle": "muted"}, DEFAULT_SECTIONS)

        assert "\\expheaderinline{" in inline_tex
        assert "\\expheader{ Senior Software Engineer }{ TechCorp Inc." in bottom_tex
        assert "\\expheadermuted{" in muted_tex

    def test_section_heading_bar_and_box_match_html_semantics(self):
        resume = load_fixture("full_stack_en.json")
        bar_tex = render_tex(resume, {**DEFAULT_GUIDANCE, "sectionHeadingStyle": "bar"}, DEFAULT_SECTIONS)
        boxed_tex = render_tex(resume, {**DEFAULT_GUIDANCE, "sectionHeadingStyle": "boxed"}, DEFAULT_SECTIONS)

        assert "\\rule{2.25pt}" in bar_tex
        assert "\\hspace{6.0pt}" in bar_tex
        assert "colframe=accentmuted" in boxed_tex
        assert "boxrule=0.75pt" in boxed_tex
        assert "height=" not in boxed_tex

    def test_double_column(self):
        resume = load_fixture("full_stack_en.json")
        g = {**DEFAULT_GUIDANCE, "columnMode": "double"}
        tex = render_tex(resume, g, DEFAULT_SECTIONS)
        assert "minipage" in tex

    def test_education_description(self):
        tex = render_tex(load_fixture("full_stack_en.json"), DEFAULT_GUIDANCE, DEFAULT_SECTIONS)
        assert "distributed systems" in tex.lower() or "Dean" in tex

    def test_contacts(self):
        tex = render_tex(load_fixture("full_stack_en.json"), DEFAULT_GUIDANCE, DEFAULT_SECTIONS)
        assert "alex.chen@example.com" in tex or "555-1234" in tex


class TestLatexChineseSupport:
    def test_english_resume_has_xecjk_safety(self):
        tex = render_tex(load_fixture("full_stack_en.json"), DEFAULT_GUIDANCE, DEFAULT_SECTIONS)
        assert "xeCJK" in tex

    def test_chinese_resume_has_cjk_support(self):
        resume_zh = load_fixture("full_stack_zh.json")
        tex = render_tex(resume_zh, DEFAULT_GUIDANCE, DEFAULT_SECTIONS)
        has_chinese = bool(re.search(r'[一-鿿㐀-䶿]', json.dumps(resume_zh, ensure_ascii=False)))
        if has_chinese:
            assert "xeCJK" in tex

    def test_chinese_content_preserved(self):
        resume_zh = load_fixture("full_stack_zh.json")
        tex = render_tex(resume_zh, DEFAULT_GUIDANCE, DEFAULT_SECTIONS)
        has_chinese = bool(re.search(r'[一-鿿㐀-䶿]', json.dumps(resume_zh, ensure_ascii=False)))
        if has_chinese:
            assert "CJK" in tex


class TestLatexEdgeCases:
    def test_minimal_resume(self):
        tex = render_tex(load_fixture("minimal.json"), DEFAULT_GUIDANCE, DEFAULT_SECTIONS)
        assert tex and "\\begin{document}" in tex

    def test_special_characters(self):
        resume = {
            "personalInfo": {"name": "John & Jane's Resume", "title": "CEO @ 50% Growth"},
            "summary": "Special chars: _ underline {brace} #hashtag $money ~tilde",
            "workExperience": [{"title": "S&P 500 Analyst", "company": "Goldman_Sachs", "years": "2020-2024", "description": ["Revenue grew 150% YoY"]}],
            "additional": {"technicalSkills": "C++ & Rust"},
        }
        tex = render_tex(resume, DEFAULT_GUIDANCE, DEFAULT_SECTIONS)
        issues = _find_tex_issues(tex)
        assert len(issues) == 0, f"Special chars not escaped: {issues}"
        assert "\\&" in tex

    def test_empty_sections_skipped(self):
        resume = {"personalInfo": {"name": "Test"}, "summary": "Just a summary."}
        tex = render_tex(resume, DEFAULT_GUIDANCE, DEFAULT_SECTIONS)
        sections_count = len(re.findall(r"\\cvsection\{", tex))
        assert sections_count <= 2, f"Too many sections: {sections_count}"

    def test_default_sections_when_sections_missing(self):
        tex = render_tex(load_fixture("full_stack_en.json"), DEFAULT_GUIDANCE, [])
        assert "\\cvsection{ Summary }" in tex
        assert "\\cvsection{ Work Experience }" in tex
        assert _has_balanced_tex_groups(tex)

    def test_all_fixtures_render(self):
        for fname in FIXTURE_DIR.glob("*.json"):
            resume = load_fixture(fname.name)
            tex = render_tex(resume, DEFAULT_GUIDANCE, DEFAULT_SECTIONS)
            assert tex and "\\begin{document}" in tex, f"Failed: {fname.name}"

    def test_different_page_formats(self):
        resume = load_fixture("full_stack_en.json")
        for fmt in ["a4", "letter"]:
            g = {**DEFAULT_GUIDANCE, "pageFormat": fmt}
            tex = render_tex(resume, g, DEFAULT_SECTIONS)
            assert tex, f"Empty output for format: {fmt}"


def _find_tex_issues(tex: str) -> list[str]:
    """Find common LaTeX issues that would prevent compilation."""
    issues = []
    body_match = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", tex, re.DOTALL)
    body = body_match.group(1) if body_match else tex
    body_lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("%"):
            continue
        body_lines.append(stripped)
    body_clean = "\n".join(body_lines)
    if re.search(r"(?<!\\)&(?!\w+;)", body_clean):
        issues.append("Unescaped & in body text")
    if "\\begin{document}" not in tex:
        issues.append("Missing \\begin{document}")
    if "\\end{document}" not in tex:
        issues.append("Missing \\end{document}")
    return issues


def _has_balanced_tex_groups(tex: str) -> bool:
    depth = 0
    for line in tex.splitlines():
        index = 0
        while index < len(line):
            char = line[index]
            if char == "%":
                break
            if char == "\\":
                index += 2
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth < 0:
                    return False
            index += 1
    return depth == 0
