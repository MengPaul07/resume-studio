import re
from typing import Any, Dict, List

from ..state import LayoutDesignState
from .common import (
    default_layout_plan,
    default_style_options,
    get_metadata,
    get_theme,
    render_single_column_template_html,
    to_dict,
    to_list,
)


SECTION_KEYS = [
    "summary",
    "workExperience",
    "education",
    "personalProjects",
    "research",
    "technicalSkills",
    "languages",
    "certifications",
    "awards",
    "customSections",
]

TEMPLATE_CLASS_REQUIREMENTS = {
    "swiss-single": ["resume-header", "resume-name", "resume-section", "resume-section-title", "resume-item", "resume-date"],
    "swiss-two-column": ["resume-header", "resume-name", "resume-section", "resume-item", "resume-date", "resume-grid"],
    "modern": ["resume-header", "resume-name", "resume-section", "resume-item", "resume-date", "name-underline", "section-title-accent"],
    "modern-two-column": [
        "resume-header",
        "resume-name",
        "resume-section",
        "resume-item",
        "resume-date",
        "resume-grid",
        "nameAccent",
        "sectionTitleAccent",
    ],
}


def _expected_template_id(payload: Dict[str, Any], column_mode: str) -> str:
    style_controls = to_dict(payload.get("style_controls"))
    tone = str(style_controls.get("tone") or "").strip().lower()
    if tone == "swiss-clean":
        return "swiss-single" if column_mode == "single" else "swiss-two-column"
    if tone in {"modern-editorial", "executive-bold"}:
        return "modern" if column_mode == "single" else "modern-two-column"
    return "swiss-single" if column_mode == "single" else "swiss-two-column"


def _has_class_token(html_text: str, class_name: str) -> bool:
    if not class_name:
        return False
    escaped = re.escape(class_name)
    return bool(
        re.search(
            rf"class\s*=\s*['\"][^'\"]*\b{escaped}\b[^'\"]*['\"]",
            html_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
    )


def _missing_template_classes(html_text: str, expected_template_id: str) -> List[str]:
    expected = TEMPLATE_CLASS_REQUIREMENTS.get(expected_template_id, [])
    missing: List[str] = []
    for class_name in expected:
        if not _has_class_token(html_text, class_name):
            missing.append(class_name)
    return missing


def _has_data(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    return bool(value)


def _required_sections(resume_obj: Dict[str, Any]) -> List[str]:
    additional = to_dict(resume_obj.get("additional"))
    required: List[str] = []

    if _has_data(resume_obj.get("summary")):
        required.append("summary")
    if _has_data(resume_obj.get("workExperience")):
        required.append("workExperience")
    if _has_data(resume_obj.get("education")):
        required.append("education")
    if _has_data(resume_obj.get("personalProjects")):
        required.append("personalProjects")
    if _has_data(resume_obj.get("research")):
        required.append("research")
    if _has_data(additional.get("technicalSkills")):
        required.append("technicalSkills")
    if _has_data(additional.get("languages")):
        required.append("languages")
    if _has_data(additional.get("certificationsTraining")):
        required.append("certifications")
    if _has_data(additional.get("awards")):
        required.append("awards")
    if _has_data(resume_obj.get("customSections")):
        required.append("customSections")

    return required or ["summary"]


def _missing_section_markers(html_text: str, required_sections: List[str]) -> List[str]:
    lower = html_text.lower()
    missing: List[str] = []
    for key in required_sections:
        marker_a = f'data-section="{key.lower()}"'
        marker_b = f"data-section='{key.lower()}'"
        if marker_a not in lower and marker_b not in lower:
            missing.append(key)
    return missing


def _validate_html_contract(html_text: str, required_sections: List[str]) -> List[str]:
    return _validate_html_contract_with_modes(
        html_text,
        required_sections=required_sections,
        expected_template_id="",
        expected_column_mode="",
        expected_page_count_mode="",
        expected_target_pages=0,
    )


def _validate_html_contract_with_modes(
    html_text: str,
    *,
    required_sections: List[str],
    expected_template_id: str,
    expected_column_mode: str,
    expected_page_count_mode: str,
    expected_target_pages: int,
) -> List[str]:
    lower = html_text.lower()
    issues: List[str] = []

    if "<html" not in lower or "</html>" not in lower:
        issues.append("missing_document_wrapper")
    if "resume-style-pack" not in lower:
        issues.append("missing_style_pack")
    if "applyresumestyle" not in lower:
        issues.append("missing_apply_style_function")

    if expected_template_id:
        marker = f'data-template-id="{expected_template_id}"'
        marker_b = f"data-template-id='{expected_template_id}'"
        if marker not in lower and marker_b not in lower:
            issues.append("mismatch_template_id")

    if expected_column_mode:
        marker = f'data-column-mode="{expected_column_mode}"'
        marker_b = f"data-column-mode='{expected_column_mode}'"
        if marker not in lower and marker_b not in lower:
            issues.append("mismatch_column_mode")

    if expected_page_count_mode:
        marker = f'data-page-count-mode="{expected_page_count_mode}"'
        marker_b = f"data-page-count-mode='{expected_page_count_mode}'"
        if marker not in lower and marker_b not in lower:
            issues.append("mismatch_page_count_mode")

    if expected_target_pages > 0:
        marker = f'data-target-pages="{expected_target_pages}"'
        marker_b = f"data-target-pages='{expected_target_pages}'"
        if marker not in lower and marker_b not in lower:
            issues.append("mismatch_target_pages")

    compact = re.sub(r"\s+", " ", lower)
    if expected_column_mode == "single":
        if "grid-template-columns" in compact and re.search(r"grid-template-columns\s*:\s*[^;]*\s+[^;]+;", compact):
            if "grid-template-columns: 1fr;" not in compact and "grid-template-columns:1fr;" not in compact:
                issues.append("suspect_two_column_layout")

    missing_sections = _missing_section_markers(html_text, required_sections)
    issues.extend([f"missing_section:{name}" for name in missing_sections])
    missing_classes = _missing_template_classes(html_text, expected_template_id)
    issues.extend([f"missing_template_class:{name}" for name in missing_classes])
    return issues


def _inject_guardrails(
    html_text: str,
    *,
    margins_mm: Dict[str, int],
    page_count_mode: str,
    target_pages: int,
    column_mode: str,
    left_width: str,
    right_width: str,
) -> str:
    top = int(margins_mm.get("top", 16))
    right = int(margins_mm.get("right", 16))
    bottom = int(margins_mm.get("bottom", 16))
    left = int(margins_mm.get("left", 16))

    hide_rule = ""
    if page_count_mode == "single-page":
        hide_rule = ".page:nth-of-type(n+2){display:none !important;}"
    elif page_count_mode == "double-page" and target_pages <= 2:
        hide_rule = ".page:nth-of-type(n+3){display:none !important;}"

    column_rule = ""
    if column_mode == "single":
        column_rule = (
            ".resume-grid,.layout-grid,.grid,[data-layout-columns='resume']"
            "{display:grid !important;grid-template-columns:1fr !important;}"
        )
    else:
        column_rule = (
            ".resume-grid,.layout-grid,.grid,[data-layout-columns='resume']"
            f"{{display:grid !important;grid-template-columns:{left_width} {right_width} !important;}}"
        )

    guardrail_css = (
        "<style id='resume-guardrails'>"
        "@page{size:A4;margin:0;}"
        "html,body{margin:0 !important;padding:0 !important;}"
        ".page{"
        "width:210mm !important;"
        "min-height:297mm !important;"
        "max-height:297mm !important;"
        "box-sizing:border-box !important;"
        f"padding:{top}mm {right}mm {bottom}mm {left}mm !important;"
        "overflow:visible !important;"
        "}"
        ".page *{box-sizing:border-box;max-width:100%;}"
        "img,svg,table,pre,code{max-width:100% !important;}"
        f"{hide_rule}"
        f"{column_rule}"
        "</style>"
    )

    if "</head>" in html_text:
        return html_text.replace("</head>", f"{guardrail_css}</head>")
    return f"{guardrail_css}{html_text}"


def _page_guardrails_from_inputs(
    layout_plan: Dict[str, Any],
    layout_preferences: Dict[str, Any],
) -> Dict[str, Any]:
    page = to_dict(layout_plan.get("page"))
    margins = to_dict(page.get("margins_mm"))
    pagination = to_dict(page.get("pagination_policy"))

    metadata = get_metadata(layout_preferences)
    payload = to_dict(metadata.get("layout_builder_payload"))
    payload_page = to_dict(payload.get("page_spec"))

    page_count_mode = str(
        pagination.get("page_count_mode")
        or payload_page.get("page_count_mode")
        or to_dict(metadata.get("render_guidance")).get("pageCountMode")
        or "single-page"
    ).strip().lower()
    if page_count_mode not in {"single-page", "double-page"}:
        page_count_mode = "single-page"

    target_pages_raw = (
        pagination.get("target_pages")
        or payload_page.get("target_pages")
        or (2 if page_count_mode == "double-page" else 1)
    )
    try:
        target_pages = int(target_pages_raw)
    except Exception:
        target_pages = 1
    target_pages = 2 if target_pages >= 2 else 1
    if page_count_mode == "single-page":
        target_pages = 1

    columns = to_list(page.get("columns"))
    column_mode = "double"
    left_width = "36%"
    right_width = "64%"
    if len(columns) == 1 and isinstance(columns[0], dict):
        column_mode = "single"
    elif len(columns) >= 2 and isinstance(columns[0], dict) and isinstance(columns[1], dict):
        left_width = str(columns[0].get("width") or left_width)
        right_width = str(columns[1].get("width") or right_width)
        if str(columns[0].get("id") or "").strip().lower() == "main":
            column_mode = "single"
    if payload:
        rerender = to_dict(to_dict(payload.get("tweak_split")).get("llm_rerender_required"))
        mode_from_payload = str(rerender.get("column_mode") or "").strip().lower()
        if mode_from_payload in {"single", "double"}:
            column_mode = mode_from_payload
    if column_mode == "single":
        left_width = "100%"
        right_width = "0%"

    return {
        "margins_mm": {
            "top": int(margins.get("top", 16)),
            "right": int(margins.get("right", 16)),
            "bottom": int(margins.get("bottom", 16)),
            "left": int(margins.get("left", 16)),
        },
        "page_count_mode": page_count_mode,
        "target_pages": target_pages,
        "column_mode": column_mode,
        "left_width": left_width,
        "right_width": right_width,
    }


def _layout_plan_from_payload(payload: Dict[str, Any], theme: str) -> Dict[str, Any]:
    base = default_layout_plan(theme)
    page_spec = to_dict(payload.get("page_spec"))
    grid_spec = to_dict(payload.get("grid_spec"))
    section_map = to_dict(grid_spec.get("section_map"))
    content_policy = to_dict(payload.get("content_policy"))
    max_items = to_dict(content_policy.get("max_items"))

    columns = to_list(grid_spec.get("sections"))
    column_mode = str(grid_spec.get("column_mode") or "double").strip().lower()
    left_width = int(grid_spec.get("left_width_percent") or 36)
    right_width = int(grid_spec.get("right_width_percent") or (100 - left_width))

    if column_mode == "single":
        page_columns = [{"id": "main", "width": "100%"}]
    else:
        page_columns = [
            {"id": "left", "width": f"{left_width}%"},
            {"id": "right", "width": f"{right_width}%"},
        ]

    _ = columns  # sections are passed separately via payload; keep plan minimal here.
    return {
        "theme": theme,
        "page": {
            "format": "a4",
            "columns": page_columns,
            "max_width_px": int(page_spec.get("max_width_px") or base["page"]["max_width_px"]),
            "padding_px": int(page_spec.get("padding_px") or base["page"]["padding_px"]),
            "margins_mm": to_dict(page_spec.get("margins_mm")) or to_dict(base["page"].get("margins_mm")),
            "boundary_policy": to_dict(page_spec.get("boundary_guardrails")) or to_dict(base["page"].get("boundary_policy")),
            "pagination_policy": {
                "page_count_mode": str(page_spec.get("page_count_mode") or "single-page"),
                "target_pages": int(page_spec.get("target_pages") or 1),
            },
        },
        "section_map": {
            "left": [str(x) for x in to_list(section_map.get("left"))] or list(base["section_map"]["left"]),
            "right": [str(x) for x in to_list(section_map.get("right"))] or list(base["section_map"]["right"]),
        },
        "constraints": {
            "preserve_facts": bool(content_policy.get("preserve_facts", True)),
            "max_items": {
                "workExperience": int(max_items.get("work_experience") or 8),
                "personalProjects": int(max_items.get("projects") or 8),
                "education": int(max_items.get("education") or 6),
                "research": int(max_items.get("research") or 6),
            },
            "bullet_style": "impact_first",
            "date_style": "ym",
        },
    }


def _style_pack_from_payload(payload: Dict[str, Any], theme: str) -> List[Dict[str, Any]]:
    style_controls = to_dict(payload.get("style_controls"))
    palette = to_dict(style_controls.get("accent_palette"))
    typography = to_dict(payload.get("typography"))
    title_effect = to_dict(style_controls.get("title_effect"))

    style = {
        "id": "form-style-1",
        "name": "Form Style",
        "theme": theme,
        "palette": {
            "primary": str(palette.get("primary") or "#1D4ED8"),
            "accent": str(palette.get("primary") or "#1D4ED8"),
            "text": "#111827",
            "muted": "#4B5563",
            "bg": str(palette.get("canvas") or "#F0F0E8"),
            "paper": "#FFFFFF",
        },
        "typography": {
            "font_family": "'IBM Plex Sans', 'PingFang SC', sans-serif",
            "base_size_px": 14,
            "title_size_px": 30,
        },
        "effects": {
            "title_shadow": "2px 2px 0 rgba(0,0,0,0.18)" if str(title_effect.get("text_shadow")) == "hard-offset" else "none",
            "card_shadow": "4px 4px 0 rgba(0,0,0,0.12)",
            "section_title_transform": "uppercase",
            "border_radius_px": 0,
        },
        "typography_meta": {
            "heading_font": str(typography.get("heading_font") or "serif"),
            "body_font": str(typography.get("body_font") or "sans-serif"),
            "density_level": int(typography.get("density_level") or 3),
        },
    }
    return [style]


def render_html(state: LayoutDesignState) -> Dict[str, str]:
    resume_obj = state.get("resume_obj", {})
    layout_preferences = state.get("layout_preferences", {})
    preferences = layout_preferences if isinstance(layout_preferences, dict) else {}
    metadata = get_metadata(preferences)
    theme = get_theme(preferences)
    payload = to_dict(metadata.get("layout_builder_payload"))

    layout_plan = to_dict(metadata.get("layout_plan"))
    if not layout_plan:
        layout_plan = _layout_plan_from_payload(payload, theme) if payload else default_layout_plan(theme)

    styles = [x for x in to_list(metadata.get("style_options")) if isinstance(x, dict)]
    if not styles:
        styles = _style_pack_from_payload(payload, theme) if payload else default_style_options(theme)[:1]
    selected_style_id = str(metadata.get("style_id") or styles[0].get("id") or "form-style-1")
    active_style = next((s for s in styles if str(s.get("id")) == selected_style_id), styles[0] if styles else {})

    design_spec = {
        "theme": theme,
        "layout_plan": layout_plan,
        "styles": styles,
        "selected_style_id": selected_style_id,
        "active_style": active_style,
        "layout_builder_payload": payload,
        "generation_mode": "single_html_node",
    }

    guardrails = _page_guardrails_from_inputs(
        layout_plan=layout_plan,
        layout_preferences=preferences,
    )

    output_html = render_single_column_template_html(
        resume_obj if isinstance(resume_obj, dict) else {},
        active_style,
        page_count_mode=str(guardrails.get("page_count_mode") or "single-page"),
        target_pages=int(guardrails.get("target_pages") or 1),
    )
    output_html = _inject_guardrails(
        output_html,
        margins_mm=to_dict(guardrails.get("margins_mm")),
        page_count_mode=str(guardrails.get("page_count_mode") or "single-page"),
        target_pages=int(guardrails.get("target_pages") or 1),
        column_mode="single",
        left_width="100%",
        right_width="0%",
    )

    return {
        "output_html": output_html,
        "design_spec": design_spec,
        "selected_style_id": selected_style_id,
        "active_style": active_style,
        "style_options": styles,
        "layout_plan": layout_plan,
    }
