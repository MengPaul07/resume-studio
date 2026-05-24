import json
from pathlib import Path

from src.services.latex_gen import render_tex


def test_render_tex_matches_css_html_mode_with_full_stack_fixture():
    resume_obj = json.loads(
        Path("tests/fixtures/resumes/full_stack_en.json").read_text(encoding="utf-8")
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
    assert "itemsep= 0.7875 pt" in tex
    assert "\\rule{\\linewidth}{ 0.75 pt}" in tex
    assert "arc=9.0pt" in tex
    assert "left=6.0pt" in tex
    assert "\\vspace{ 6.0 pt}" in tex
    assert "Alex Chen" in tex
    assert "Senior Software Engineer" in tex
    assert "\\cvtag{ Python }" in tex


def test_render_tex_honors_section_order_field_when_input_is_shuffled():
    resume_obj = json.loads(
        Path("tests/fixtures/resumes/full_stack_en.json").read_text(encoding="utf-8")
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
