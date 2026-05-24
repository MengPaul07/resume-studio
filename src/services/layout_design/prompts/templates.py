import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


RESUME_MATCHER_REFERENCE_FILES = {
    "swiss-single": [
        "apps/frontend/components/resume/resume-single-column.tsx",
        "apps/frontend/components/resume/styles/swiss-single.module.css",
    ],
    "swiss-two-column": [
        "apps/frontend/components/resume/resume-two-column.tsx",
        "apps/frontend/components/resume/styles/swiss-two-column.module.css",
    ],
    "modern": [
        "apps/frontend/components/resume/resume-modern.tsx",
        "apps/frontend/components/resume/styles/modern.module.css",
    ],
    "modern-two-column": [
        "apps/frontend/components/resume/resume-modern-two-column.tsx",
        "apps/frontend/components/resume/styles/modern-two-column.module.css",
    ],
}

REFERENCE_SIGNAL_PATTERNS = [
    "resume-header",
    "resume-name",
    "resume-title",
    "resume-meta",
    "resume-section-title",
    "resume-section-title-sm",
    "resume-item-title",
    "resume-item-subtitle",
    "resume-items",
    "resume-item",
    "resume-date",
    "name-underline",
    "nameAccent",
    "section-title-accent",
    "sectionTitleAccent",
    "styles.grid",
    "styles.mainColumn",
    "styles.sidebarColumn",
]

REFERENCE_FALLBACK_GUIDE = """
ResumeMatcher template guide (derived from target references):
1) Shared structure:
- Header block with centered name/title/contact line.
- Semantic content blocks: summary, workExperience, education, personalProjects, technicalSkills, languages, certifications, awards, customSections.
- Experience/project/education item rows use title + date, subtitle row, optional bullet list.
- Shared class family should appear in markup: resume-header, resume-name, resume-title/resume-role, resume-meta/resume-contact, resume-section, resume-section-title, resume-items, resume-item, resume-item-title, resume-item-subtitle, resume-date, resume-link.
2) swiss-single:
- Single flow layout, no split grid.
- section titles use resume-section-title (base underline style).
3) swiss-two-column:
- Two-column grid with 65/35 style split.
- grid wrapper + mainColumn + sidebarColumn structure.
- main column contains summary/experience/projects/certifications/custom sections.
- sidebar contains education/skills/languages/awards/links.
4) modern:
- Single flow layout.
- Accent section titles class: section-title-accent.
- Name has accent underline element class name-underline.
5) modern-two-column:
- Two-column grid wrapper + mainColumn + sidebarColumn.
- Accent section title class: sectionTitleAccent.
- Name accent class: nameAccent.
- Sidebar small section titles still readable and compact.
6) print/pagination cues:
- Avoid breaking resume-item across pages.
- Avoid separating section title from first content row.
""".strip()


def _candidate_resume_matcher_roots() -> List[Path]:
    roots: List[Path] = []
    env_root = os.environ.get("RESUME_MATCHER_ROOT", "").strip()
    if env_root:
        roots.append(Path(env_root))

    try:
        current = Path(__file__).resolve()
        # .../<repo>/src/services/layout_design/prompts/templates.py
        repo_root = current.parents[4]
        roots.append(repo_root.parent / "Resume-Matcher")
    except Exception:
        pass

    roots.append(Path("D:/Repo/Resume-Matcher"))
    return roots


def _pick_resume_matcher_root() -> Path | None:
    for root in _candidate_resume_matcher_roots():
        if root.exists() and root.is_dir():
            return root
    return None


def _extract_signal_lines(text: str, *, max_lines: int = 64) -> str:
    lines = text.splitlines()
    selected: List[str] = []
    for idx, line in enumerate(lines, start=1):
        if any(pattern in line for pattern in REFERENCE_SIGNAL_PATTERNS):
            clean = line.strip()
            if not clean:
                continue
            selected.append(f"{idx}: {clean}")
        if len(selected) >= max_lines:
            break
    return "\n".join(selected)


@lru_cache(maxsize=8)
def _load_resume_matcher_reference_context(template_id: str) -> str:
    template_key = template_id.strip().lower()
    files = RESUME_MATCHER_REFERENCE_FILES.get(template_key, [])
    if not files:
        return REFERENCE_FALLBACK_GUIDE

    root = _pick_resume_matcher_root()
    if root is None:
        return REFERENCE_FALLBACK_GUIDE

    chunks: List[str] = [REFERENCE_FALLBACK_GUIDE]
    for rel_path in files:
        path = root / rel_path
        if not path.exists() or not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if rel_path.endswith(".css"):
            content = "\n".join(raw.splitlines()[:180]).strip()
        else:
            content = _extract_signal_lines(raw, max_lines=80)

        if content:
            chunks.append(f"[Reference: {rel_path}]\n{content}")

    return "\n\n".join(chunks)


def build_layout_planner_prompts(
    *,
    resume_obj: Dict[str, Any],
    preferences: Dict[str, Any],
    fallback_plan: Dict[str, Any],
) -> Tuple[str, str]:
    system_prompt = (
        "You are LayoutPlannerAgent, a senior resume information architect. "
        "Your ONLY job is to output one strict JSON object for layout constraints. "
        "Do not output markdown, HTML, comments, explanations, or code fences."
    )

    user_prompt = (
        "Task:\n"
        "Generate one robust layout plan JSON for resume rendering. The renderer will enforce this plan.\n\n"
        "Hard requirements:\n"
        "1) Output ONE JSON object only.\n"
        "2) Preserve ATS readability (clear headings, logical section order, no gimmick layout).\n"
        "3) Page format MUST be A4 only. Never output letter.\n"
        "4) Enforce boundary policy: no content beyond printable page box.\n"
        "5) Respect required column_mode and page_count_mode from layout_preferences.metadata.layout_builder_payload when present.\n"
        "6) Keep factual fidelity constraints explicit.\n"
        "7) Include max_items limits for core arrays to avoid overflow.\n"
        "8) Keep spacing practical for A4 print.\n\n"
        "Output schema (must follow key names):\n"
        "{\n"
        "  \"theme\": \"string\",\n"
        "  \"page\": {\n"
        "    \"format\": \"a4\",\n"
        "    \"columns\": [{\"id\": \"left\", \"width\": \"32%\"}, {\"id\": \"right\", \"width\": \"68%\"}] OR [{\"id\": \"main\", \"width\": \"100%\"}],\n"
        "    \"max_width_px\": 1040,\n"
        "    \"padding_px\": 24,\n"
        "    \"margins_mm\": {\"top\": 12, \"right\": 12, \"bottom\": 12, \"left\": 12},\n"
        "    \"boundary_policy\": {\"enforce_a4\": true, \"overflow_behavior\": \"forbid\", \"content_must_fit\": true},\n"
        "    \"pagination_policy\": {\"page_count_mode\": \"single-page\", \"target_pages\": 1}\n"
        "  },\n"
        "  \"section_map\": {\n"
        "    \"left\": [\"summary\", \"technicalSkills\", \"languages\", \"certifications\", \"awards\"],\n"
        "    \"right\": [\"workExperience\", \"education\", \"personalProjects\", \"customSections\"]\n"
        "  },\n"
        "  \"constraints\": {\n"
        "    \"preserve_facts\": true,\n"
        "    \"max_items\": {\"workExperience\": 8, \"personalProjects\": 8, \"education\": 6},\n"
        "    \"bullet_style\": \"impact_first\",\n"
        "    \"date_style\": \"ym\"\n"
        "  }\n"
        "}\n\n"
        f"Fallback baseline:\n{_dump(fallback_plan)}\n\n"
        f"Resume JSON:\n{_dump(resume_obj)}\n\n"
        f"Layout preferences:\n{_dump(preferences)}\n\n"
        "Return valid JSON only."
    )

    return system_prompt, user_prompt


def build_style_designer_prompts(
    *,
    resume_obj: Dict[str, Any],
    preferences: Dict[str, Any],
    fallback_styles: List[Dict[str, Any]],
    style_count: int,
) -> Tuple[str, str]:
    system_prompt = (
        "You are StyleDesignerAgent, a premium resume art director. "
        "You output JSON only. No markdown, no prose, no HTML."
    )

    user_prompt = (
        "Task:\n"
        f"Generate exactly {max(2, style_count)} style variants for ONE fixed resume structure.\n"
        "These are visual skins only; they must not alter content hierarchy.\n\n"
        "Output format (strict):\n"
        "{\n"
        "  \"styles\": [\n"
        "    {\n"
        "      \"id\": \"modern-clean\",\n"
        "      \"name\": \"Modern Clean\",\n"
        "      \"theme\": \"modern\",\n"
        "      \"palette\": {\"primary\": \"#xxxxxx\", \"accent\": \"#xxxxxx\", \"text\": \"#xxxxxx\", \"muted\": \"#xxxxxx\", \"bg\": \"#xxxxxx\", \"paper\": \"#xxxxxx\"},\n"
        "      \"typography\": {\"font_family\": \"string\", \"base_size_px\": 14, \"title_size_px\": 30},\n"
        "      \"effects\": {\"title_shadow\": \"string\", \"card_shadow\": \"string\", \"section_title_transform\": \"uppercase\", \"border_radius_px\": 10}\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Style quality rules:\n"
        "1) Each style must be clearly distinct in mood and color logic.\n"
        "2) Must remain professional for real hiring contexts (no neon chaos).\n"
        "3) Use exactly 6-digit HEX colors.\n"
        "4) Name styles clearly (e.g., Clean, Editorial, Executive, Vibrant).\n"
        "5) Keep effects tasteful and printable, with A4 layout safety in mind.\n"
        "6) Do not remove required keys.\n"
        "7) If metadata.layout_builder_payload exists, keep visual choices consistent with its style_controls.\n\n"
        f"Fallback references:\n{_dump(fallback_styles)}\n\n"
        f"Resume JSON:\n{_dump(resume_obj)}\n\n"
        f"Layout preferences:\n{_dump(preferences)}\n\n"
        "Return JSON only."
    )

    return system_prompt, user_prompt


def build_html_renderer_prompts(
    *,
    resume_obj: Dict[str, Any],
    layout_preferences: Dict[str, Any],
    layout_builder_payload: Dict[str, Any],
    selected_style_id: str,
    expected_template_id: str,
    expected_column_mode: str,
    expected_page_count_mode: str,
    expected_target_pages: int,
) -> Tuple[str, str]:
    reference_context = _load_resume_matcher_reference_context(expected_template_id)

    system_prompt = (
        "You are HtmlRendererAgent. Produce ONE complete, standalone HTML document. "
        "Output HTML only. No markdown, no explanation."
    )

    user_prompt = (
        "Task:\n"
        "Render full resume HTML directly from form payload + resume content.\n\n"
        "Critical output contract:\n"
        "1) Output must be a valid full HTML document with <html>, <head>, <body>.\n"
        "2) <html> must include data-style-id set to selected_style_id.\n"
        f"3) <html> must include data-template-id='{expected_template_id}'.\n"
        f"4) <html> must include data-column-mode='{expected_column_mode}'.\n"
        f"5) <html> must include data-page-count-mode='{expected_page_count_mode}' and data-target-pages='{expected_target_pages}'.\n"
        "6) Include <script id='resume-style-pack' type='application/json'>...</script> containing an array of style objects (at least one).\n"
        "7) Provide JS function window.applyResumeStyle(styleId) that updates html[data-style-id].\n"
        "8) Include style variable blocks for each style id via selectors like html[data-style-id='x'] { --primary: ... }.\n"
        "9) Render complete content: personal header, summary, workExperience, education, personalProjects, technicalSkills, languages, certifications, awards, customSections (when present).\n"
        "10) Every rendered major section must use marker: <section data-section='summary'>, <section data-section='workExperience'>, etc.\n"
        "11) Do not invent facts, dates, employers, skills, or achievements.\n"
        "12) Page format MUST be A4 (210mm x 297mm) and content must not exceed page margins.\n"
        "13) Enforce no-overflow boundary behavior from layout_builder_payload.page_spec.boundary_guardrails.\n"
        "14) Respect layout_builder_payload.page_spec.margins_mm and target_pages strictly.\n"
        "15) Respect metadata.layout_builder_payload when present in layout_preferences.\n"
        "16) If data-column-mode is single, render one-column structure only (no two-column split).\n"
        "17) If data-column-mode is double, render two-column structure matching layout_builder_payload.grid_spec.\n"
        "18) Keep the layout print-safe and responsive.\n"
        "19) Keep semantic, readable HTML (headings/lists/articles).\n"
        "20) Avoid generic SaaS card UI (no big radius, no blurred glow, no floating dashboard cards).\n\n"
        "Template fidelity rules (strict):\n"
        "- Reproduce ResumeMatcher hierarchy and visual logic from the provided references.\n"
        "- Header block: centered name (uppercase), role line, then contact row.\n"
        "- Item block: title/date row + subtitle row + bullet list.\n"
        "- Shared class family must appear in rendered markup: resume-header, resume-name, resume-section, resume-items, resume-item, resume-item-title, resume-item-subtitle, resume-date.\n"
        "- For swiss-single: section titles use resume-section-title and no split grid.\n"
        "- For swiss-two-column: render grid/mainColumn/sidebarColumn-style split and keep summary+experience in main column.\n"
        "- For modern: include name-underline and section-title-accent classes with accent color.\n"
        "- For modern-two-column: include sectionTitleAccent + nameAccent and two-column split.\n\n"
        "Section marker list to use exactly:\n"
        "summary, workExperience, education, personalProjects, technicalSkills, languages, certifications, awards, customSections\n\n"
        f"expected_template_id:\n{expected_template_id}\n\n"
        f"selected_style_id:\n{selected_style_id}\n\n"
        f"ResumeMatcher reference snippets:\n{reference_context}\n\n"
        f"layout_builder_payload JSON:\n{_dump(layout_builder_payload)}\n\n"
        f"resume JSON:\n{_dump(resume_obj)}\n\n"
        f"layout_preferences JSON:\n{_dump(layout_preferences)}\n\n"
        "Return HTML only."
    )

    return system_prompt, user_prompt


def build_html_repair_prompt(
    *,
    previous_html: str,
    missing_sections: List[str],
    contract_issues: List[str],
    expected_template_id: str,
    expected_column_mode: str,
    expected_page_count_mode: str,
    expected_target_pages: int,
) -> str:
    missing = ", ".join(missing_sections) if missing_sections else "none"
    issues = ", ".join(contract_issues) if contract_issues else "none"
    return (
        "The previous HTML is incomplete. Repair and return FULL HTML only.\n"
        f"Missing section markers: {missing}.\n"
        f"Contract issues: {issues}.\n"
        f"Expected data-template-id: {expected_template_id}.\n"
        f"Expected data-column-mode: {expected_column_mode}.\n"
        f"Expected data-page-count-mode: {expected_page_count_mode}.\n"
        f"Expected data-target-pages: {expected_target_pages}.\n"
        "Ensure resume-style-pack script exists and all required data-section markers are present.\n"
        "Ensure html data attributes strictly match expected values.\n"
        "Ensure ResumeMatcher template classes are present for the expected template mode.\n"
        "Do not omit any existing section content.\n\n"
        "Previous HTML:\n"
        f"{previous_html}"
    )
