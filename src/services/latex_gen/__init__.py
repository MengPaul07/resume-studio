"""
LaTeX resume generator — renders .tex matching the frontend HTML CSS variables.
Aligns with frontend RenderGuidanceSettings + buildCssVariables().
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates" / "latex"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)

# Compact spacing multipliers — must match html-renderer.ts COMPACT_SP / COMPACT_LH
COMPACT_SP = [1, 0.85, 0.70, 0.55, 0.40]
COMPACT_LH = [1, 0.97, 0.92, 0.88, 0.85]

# ── helpers ──────────────────────────────────────────────────────────

def _escape_latex(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&":  r"\&",
        "%":  r"\%",
        "$":  r"\$",
        "#":  r"\#",
        "_":  r"\_",
        "{":  r"\{",
        "}":  r"\}",
        "~":  r"\textasciitilde{}",
        "^":  r"\^{}",
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    return text


def _hex_color(hex_str: Any, fallback: str = "000000") -> str:
    raw = str(hex_str or "").strip()
    match = re.search(r"#?([0-9a-fA-F]{6})", raw)
    return match.group(1).upper() if match else fallback.upper()


def _extract_css_vars(html_source: str | None) -> Dict[str, str]:
    if not html_source:
        return {}
    return {
        key.strip(): value.strip()
        for key, value in re.findall(r"--r-([a-zA-Z0-9-]+)\s*:\s*([^;]+);", html_source)
    }


def _css_var(css_vars: Dict[str, str], key: str, fallback: Any) -> Any:
    return css_vars.get(key, fallback)


def _css_px(value: Any, fallback: float) -> float:
    raw = str(value or "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not match:
        try:
            return float(value)
        except Exception:
            return float(fallback)
    return float(match.group(0))


def _px_to_mm(px: float) -> float:
    return round(px * 25.4 / 96, 2)


def _px_to_pt(px: float) -> float:
    return round(px * 72 / 96, 2)


def _font_px_to_pt(px: float) -> float:
    return round(px * 72 / 96, 2)


def _css_px_var(css_vars: Dict[str, str], key: str, fallback: float) -> float:
    return _css_px(css_vars.get(key), fallback) if key in css_vars else float(fallback)


def _guidance_px(guidance: Dict[str, Any], key: str, fallback: float) -> float:
    return _css_px(guidance.get(key), fallback)


def _css_hex_var(css_vars: Dict[str, str], key: str, fallback: Any) -> str:
    return _hex_color(css_vars.get(key, fallback), str(fallback).lstrip("#"))


def _font_key_from_css(value: str, fallback: str) -> str:
    raw = str(value or "").lower()
    if "georgia" in raw or "pagella" in raw or "serif" in raw and "sans" not in raw:
        return "serif"
    if "mono" in raw or "cursor" in raw:
        return "mono"
    if "inter" in raw or "segoe" in raw or "heros" in raw or "sans" in raw:
        return "sans-serif"
    return fallback


def _tex_font_name(font_key: str) -> str:
    if font_key == "serif":
        return "TeX Gyre Pagella"
    if font_key == "mono":
        return "TeX Gyre Cursor"
    return "TeX Gyre Heros"


def _default_sections() -> List[Dict[str, Any]]:
    return [
        {"key": "summary", "title": "Summary", "visible": True, "column": "left"},
        {"key": "technicalSkills", "title": "Skills", "visible": True, "column": "left"},
        {"key": "languages", "title": "Languages", "visible": True, "column": "left"},
        {"key": "certifications", "title": "Certifications", "visible": True, "column": "left"},
        {"key": "awards", "title": "Awards", "visible": True, "column": "left"},
        {"key": "workExperience", "title": "Work Experience", "visible": True, "column": "right"},
        {"key": "education", "title": "Education", "visible": True, "column": "right"},
        {"key": "personalProjects", "title": "Projects", "visible": True, "column": "right"},
        {"key": "research", "title": "Research", "visible": True, "column": "right"},
    ]


def _sp(guidance: dict, key: str, default: float) -> float:
    """Apply compact spacing multiplier."""
    level = int(guidance.get("compactLevel", 0) or 0)
    return round(float(guidance.get(key, default)) * COMPACT_SP[min(level, 4)])


def _clh(guidance: dict) -> float:
    """Compact line-height multiplier."""
    level = int(guidance.get("compactLevel", 0) or 0)
    lh = float(guidance.get("lineHeightPercent", 155))
    return lh * COMPACT_LH[min(level, 4)] / 100.0


_DEFAULT_TITLES = {
    "summary": "Summary",
    "workExperience": "Work Experience",
    "personalProjects": "Projects",
    "education": "Education",
    "research": "Research",
    "technicalSkills": "Skills",
    "languages": "Languages",
    "certifications": "Certifications",
    "awards": "Awards",
}


# ── section resolution (separates left/right for dual-column) ────────

_DEFAULT_SECTION_ORDER = {section["key"]: index for index, section in enumerate(_default_sections())}


def _numeric_sort_value(value: Any, fallback: int) -> float:
    try:
        if value is None or value == "":
            return float(fallback)
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def _ordered_sections(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    indexed = [(index, sec) for index, sec in enumerate(sections)]

    def sort_key(item: tuple[int, Dict[str, Any]]) -> tuple[float, float, float]:
        index, sec = item
        key = str(sec.get("key", ""))
        default_order = _DEFAULT_SECTION_ORDER.get(key, index)
        page = _numeric_sort_value(sec.get("page"), 1)
        order = _numeric_sort_value(sec.get("order"), default_order)
        return (page, order, float(index))

    return [sec for _, sec in sorted(indexed, key=sort_key)]


def _resolve_sections(
    resume_obj: Dict[str, Any],
    guidance: Dict[str, Any],
    sections: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Return {"left": [...], "right": [...]} section lists for dual-column layout."""
    left: List[Dict[str, Any]] = []
    right: List[Dict[str, Any]] = []
    date_style = str(guidance.get("dateStyle", "muted"))
    bullet_style = str(guidance.get("bulletStyle", "disc"))
    body_size = guidance.get("bodyFontSizePx", 13)

    for sec in _ordered_sections(sections):
        if not sec.get("visible", True):
            continue
        key = str(sec.get("key", ""))
        title = str(sec.get("title") or "")
        if not title or title == key:
            title = _DEFAULT_TITLES.get(key, str(key))
        title_tex = _escape_latex(title)
        column = str(sec.get("column", "right"))

        entry = _build_section(key, title_tex, resume_obj, guidance, date_style, bullet_style, body_size)
        if entry is None:
            continue
        if column == "left":
            left.append(entry)
        else:
            right.append(entry)

    return {"left": left, "right": right}


def _build_section(
    key: str,
    title_tex: str,
    resume_obj: dict,
    guidance: dict,
    date_style: str,
    bullet_style: str,
    body_size: float,
) -> Optional[Dict[str, Any]]:
    is_bottom = date_style == "bottom-inline"

    if key == "summary":
        text = str(resume_obj.get("summary", "")).strip()
        if text:
            return {"title": title_tex, "type": "text", "content": _escape_latex(text)}

    elif key == "workExperience":
        items = resume_obj.get("workExperience") or []
        entries = _experience_entries(items, is_bottom, bullet_style, body_size, "exp")
        if entries:
            return {"title": title_tex, "type": "experience", "items": entries, "date_style": date_style}

    elif key == "personalProjects":
        items = resume_obj.get("personalProjects") or []
        entries = _experience_entries(items, is_bottom, bullet_style, body_size, "proj")
        if entries:
            return {"title": title_tex, "type": "experience", "items": entries, "date_style": date_style}

    elif key == "education":
        items = resume_obj.get("education") or []
        entries = []
        for edu in (items if isinstance(items, list) else []):
            if not isinstance(edu, dict):
                continue
            inst = _escape_latex(str(edu.get("institution", "")))
            degree = _escape_latex(str(edu.get("degree", "")))
            years = _escape_latex(str(edu.get("years", "")))
            gpa = _escape_latex(str(edu.get("gpa", ""))) if edu.get("gpa") else ""
            entries.append({
                "institution": inst or "Institution",
                "degree": degree,
                "years": years,
                "gpa": gpa,
                "is_bottom": is_bottom,
            })
        if entries:
            return {"title": title_tex, "type": "education", "items": entries, "date_style": date_style}

    elif key == "research":
        items = resume_obj.get("research") or []
        entries = _experience_entries(items, is_bottom, bullet_style, body_size, "research")
        if entries:
            return {"title": title_tex, "type": "experience", "items": entries, "date_style": date_style}

    elif key in ("technicalSkills", "languages", "certifications", "awards"):
        additional = resume_obj.get("additional", {}) or {}
        mapping = {
            "technicalSkills": "technicalSkills",
            "languages": "languages",
            "certifications": "certificationsTraining",
            "awards": "awards",
        }
        raw = additional.get(mapping.get(key, key)) or []
        tag_size = guidance.get("tagFontSizePx", 10)
        items = [_escape_latex(str(x).strip()) for x in (raw if isinstance(raw, list) else []) if str(x).strip()]
        if items:
            return {"title": title_tex, "type": "tags", "items": items, "tag_size": tag_size}

    else:
        # Generic fallback
        raw_val = resume_obj.get(key)
        if raw_val is None:
            additional = resume_obj.get("additional", {}) or {}
            raw_val = additional.get(key)
        if raw_val is None:
            cs = resume_obj.get("customSections", {}) or {}
            raw_val = cs.get(key)
        if isinstance(raw_val, list):
            items = [_escape_latex(str(x).strip()) for x in raw_val if str(x).strip()]
            if items:
                return {"title": title_tex, "type": "list", "items": items}
        elif isinstance(raw_val, str) and raw_val.strip():
            return {"title": title_tex, "type": "text", "content": _escape_latex(raw_val)}

    return None


def _experience_entries(
    items: list,
    is_bottom: bool,
    bullet_style: str,
    body_size: float,
    kind: str,
) -> list:
    entries = []
    for item in (items if isinstance(items, list) else []):
        if not isinstance(item, dict):
            continue
        if kind == "exp":
            title_val = _escape_latex(str(item.get("title", "")))
            subtitle_val = _escape_latex(str(item.get("company", "")))
            loc = _escape_latex(str(item.get("location", "")))
            sub = " · ".join(filter(None, [subtitle_val, loc]))
        elif kind == "research":
            title_val = _escape_latex(str(item.get("name", "")))
            role_v = _escape_latex(str(item.get("role", "")))
            inst_v = _escape_latex(str(item.get("institution", "")))
            sub = ", ".join(filter(None, [role_v, inst_v]))
        else:
            title_val = _escape_latex(str(item.get("name") or item.get("title") or ""))
            sub = _escape_latex(str(item.get("role", "")))
        years = _escape_latex(str(item.get("years", "")))
        desc = item.get("description") or []
        bullets = [_escape_latex(str(b).strip()) for b in (desc if isinstance(desc, list) else []) if str(b).strip()]
        entries.append({
            "title": title_val or ("Role" if kind == "exp" else "Project"),
            "subtitle": sub,
            "years": years,
            "bullets": bullets,
            "is_bottom": is_bottom,
        })
    return entries


# ── main render function ─────────────────────────────────────────────

def render_tex(
    resume_obj: Dict[str, Any],
    guidance: Dict[str, Any],
    sections: List[Dict[str, Any]],
    personal_info: Optional[Dict[str, Any]] = None,
    html_source: Optional[str] = None,
) -> str:
    pi = personal_info or resume_obj.get("personalInfo", {}) or {}
    margins = guidance.get("margins", {}) or {}
    css_vars = _extract_css_vars(html_source)

    name = _escape_latex(str(pi.get("name", "Your Name")))
    role = _escape_latex(str(pi.get("title", "")))
    email = str(pi.get("email", "")).strip()
    phone = str(pi.get("phone", "")).strip()
    location = str(pi.get("location", "")).strip()
    website = str(pi.get("website", "")).strip()
    linkedin = str(pi.get("linkedin", "")).strip()
    github = str(pi.get("github", "")).strip()

    contacts = [_escape_latex(x) for x in [email, phone, location] if x]
    links_raw = [_escape_latex(x) for x in [website, linkedin, github] if x]
    links = [rf"\href{{{x}}}{{{x}}}" for x in links_raw] if links_raw else []

    # ── extract guidance params (same as html-renderer buildCssVariables) ──
    accent = _css_hex_var(css_vars, "accent", guidance.get("accentColor", "31457f"))
    accent_muted = _css_hex_var(css_vars, "accent-muted", "e5e5e5")
    body_color = _css_hex_var(css_vars, "body-color", guidance.get("bodyTextColor", "1d1d1f"))
    meta_color = _css_hex_var(css_vars, "meta-color", guidance.get("metaTextColor", "5f6b7a"))
    header_bg = _css_hex_var(css_vars, "header-bg", guidance.get("headerBgColor", "ffffff"))
    header_text = _css_hex_var(css_vars, "header-color", guidance.get("headerTextColor", "1d1d1f"))
    sidebar_bg = _css_hex_var(css_vars, "sidebar-bg", guidance.get("leftSidebarBg", "fafafa"))
    divider_color = _css_hex_var(css_vars, "divider-color", guidance.get("headerDividerColor", "d1d1d1"))
    tag_bg = _css_hex_var(css_vars, "tag-bg", guidance.get("tagBgColor", "f5f5f5"))
    tag_border = _css_hex_var(css_vars, "tag-border", guidance.get("tagBorderColor", "e5e5e5"))

    # 字号换算：HTML/CSS 使用 px，LaTeX 使用 pt；这里按 96dpi -> 72pt 换算。
    # 如果觉得整体字体偏大/偏小，优先调 _font_px_to_pt() 的倍率，而不是模板里的 \fontsize。
    name_size_px = _css_px_var(css_vars, "name-size", _guidance_px(guidance, "nameFontSizePx", 32))
    role_size_px = _css_px_var(css_vars, "role-size", _guidance_px(guidance, "roleFontSizePx", 14))
    meta_size_px = _css_px_var(css_vars, "meta-size", _guidance_px(guidance, "metaFontSizePx", 12))
    body_size_px = _css_px_var(css_vars, "body-size", _guidance_px(guidance, "bodyFontSizePx", 13))
    heading_size_px = _css_px_var(css_vars, "heading-size", _guidance_px(guidance, "sectionHeadingSizePx", 12))
    tag_size_px = _css_px_var(css_vars, "tag-size", _guidance_px(guidance, "tagFontSizePx", 10))
    name_size = _font_px_to_pt(name_size_px)
    role_size = _font_px_to_pt(role_size_px)
    meta_size = _font_px_to_pt(meta_size_px)
    body_size = _font_px_to_pt(body_size_px)
    heading_size = _font_px_to_pt(heading_size_px)
    tag_size = _font_px_to_pt(tag_size_px)
    name_weight = _css_px_var(css_vars, "name-weight", _guidance_px(guidance, "nameFontWeight", 700))

    # 行距：来自 CSS --r-line-height。正文使用完整比例，标题行距会被限制到 1.15-1.35，避免标题过松。
    line_height = float(css_vars.get("line-height", _clh(guidance)) or _clh(guidance))
    body_leading = round(body_size * line_height, 1)
    heading_leading = round(heading_size * max(1.15, min(line_height, 1.35)), 1)
    name_leading = round(name_size * 1.2, 1)
    role_leading = round(role_size * 1.3, 1)
    meta_leading = round(meta_size * 1.3, 1)
    tag_leading = round(tag_size * 1.4, 1)
    heading_style = str(guidance.get("sectionHeadingStyle", "underline"))
    heading_case = str(guidance.get("sectionHeadingCase", "uppercase")).upper()
    is_uppercase = heading_case == "UPPERCASE"

    header_font = _font_key_from_css(str(css_vars.get("header-font", "")), str(guidance.get("headerFont", "serif")))
    body_font = _font_key_from_css(str(css_vars.get("body-font", "")), str(guidance.get("bodyFont", "sans-serif")))

    # spacing with compact multipliers
    # 页面边距：HTML 的 --r-page-padding(px) 会转成 geometry 的 hmargin/vmargin(mm)。
    # 如果 PDF 边距不舒服，可以先调这里的 page_padding_mm，或在模板 geometry 行手动改 hmargin/vmargin。
    page_padding_px = _css_px_var(css_vars, "page-padding", _guidance_px(guidance, "pagePaddingPx", min(margins.get("top", 12), margins.get("left", 12)) * 96 / 25.4))
    page_padding_mm = _px_to_mm(page_padding_px)
    content_width_px = max(320.0, 210 * 96 / 25.4 - page_padding_px * 2)
    section_gap = _css_px_var(css_vars, "section-gap", _sp(guidance, "sectionGapPx", 18))
    item_gap = _css_px_var(css_vars, "item-gap", _sp(guidance, "itemGapPx", 10))
    heading_margin = _css_px_var(css_vars, "heading-margin", _sp(guidance, "headingMarginBottomPx", 8))
    heading_rule_gap = _css_px_var(css_vars, "heading-rule-gap", _sp(guidance, "sectionUnderlineGapPx", 4))
    heading_rule_thick = _css_px_var(css_vars, "heading-rule-thick", _guidance_px(guidance, "sectionUnderlineThicknessPx", 1))
    header_margin = _css_px_var(css_vars, "header-margin", _sp(guidance, "headerMarginBottomPx", 14))
    header_pad = _css_px_var(css_vars, "header-pad", _sp(guidance, "headerPaddingBottomPx", 8))
    role_mt = _css_px_var(css_vars, "role-mt", _sp(guidance, "roleMarginTopPx", 6))
    contact_gap = _css_px_var(css_vars, "contact-gap", _sp(guidance, "contactGapPx", 4))
    bullet_indent = _css_px_var(css_vars, "bullet-indent", _guidance_px(guidance, "bulletIndentPx", 18))
    bullet_top_gap = _css_px_var(css_vars, "bullet-top-gap", _sp(guidance, "bulletListTopGapPx", 3))
    bullet_gap = _css_px_var(css_vars, "bullet-gap", _sp(guidance, "bulletItemGapPx", 6))
    tag_gap = _css_px_var(css_vars, "tag-gap", _sp(guidance, "tagGapPx", 6))
    tag_pad_x = _css_px_var(css_vars, "tag-pad-x", _guidance_px(guidance, "tagPaddingXPx", 8))
    tag_pad_y = _css_px_var(css_vars, "tag-pad-y", _guidance_px(guidance, "tagPaddingYPx", 2))
    tag_radius = _css_px_var(css_vars, "tag-radius", _guidance_px(guidance, "tagRadiusPx", 12))
    tag_border_width = _css_px_var(css_vars, "tag-border-width", _guidance_px(guidance, "tagBorderWidthPx", 1))
    sidebar_padding = _css_px_var(css_vars, "sidebar-pad", _sp(guidance, "sidebarPaddingPx", 8))
    sidebar_radius = _css_px_var(css_vars, "sidebar-radius", _guidance_px(guidance, "sidebarRadiusPx", 4))
    col_gap = _css_px_var(css_vars, "col-gap", _sp(guidance, "columnGapPx", 16))
    left_basis_px = _css_px_var(
        css_vars,
        "left-basis",
        max(120.0, round(((content_width_px - col_gap) * float(guidance.get("leftWidthPercent", 36))) / 100)),
    )
    # 左右栏宽度：HTML 传的是左栏像素宽 --r-left-basis；这里换成 LaTeX \textwidth 的比例。
    # 手调时可改 left_frac/right_frac，或改 left_col_width/right_col_width 里的固定扣减值。
    left_pct = round(left_basis_px / content_width_px * 100, 2)
    left_frac = f"{max(0.1, min(0.9, left_pct / 100)):.4f}".lstrip("0")
    right_frac = f"{max(0.1, min(0.9, 1 - left_pct / 100)):.4f}".lstrip("0")
    half_col_gap = round(_px_to_pt(col_gap) / 2, 2)
    sidebar_pad_pt = _px_to_pt(sidebar_padding)
    sidebar_inner_deduct = round(sidebar_pad_pt * 2, 2)
    left_col_width = rf"\dimexpr {left_frac}\textwidth - {half_col_gap}pt - {sidebar_inner_deduct}pt\relax"
    right_col_width = rf"\dimexpr {right_frac}\textwidth - {half_col_gap}pt\relax"

    column_mode = str(guidance.get("columnMode", "double"))
    is_double = column_mode == "double"
    header_layout = str(guidance.get("headerLayout", "left"))
    contact_layout = str(guidance.get("contactLayout", "inline"))
    show_divider = bool(guidance.get("showHeaderDivider", True))
    divider_thick = _css_px_var(css_vars, "divider-thick", _guidance_px(guidance, "headerDividerThicknessPx", 1))
    # 垂直密度调节区：
    # - section_title_gap：每个 section 标题前的空白，越大 section 越分散。
    # - exp_gap：每段经历标题前的空白，控制 work/project/education 条目密度。
    # - bullet_item_sep：bullet 之间的空白，单页溢出时优先减小它。
    # - bullet_topsep：bullet 列表和条目头之间的空白。
    # - tag_gap_tex：技能/语言等标签之间的横向间距。
    section_title_gap = min(_px_to_pt(section_gap) * 0.45, 6.0)
    exp_gap = min(_px_to_pt(item_gap) * 0.55, 3.0)
    bullet_item_sep = max(0.5, min(_px_to_pt(bullet_gap) * 0.35, 1.5))
    bullet_topsep = max(0.0, min(_px_to_pt(bullet_top_gap), 2.5))
    tag_gap_tex = max(1.5, min(_px_to_pt(tag_gap) * 0.6, 2.5))

    # sections split by column
    section_data = _resolve_sections(resume_obj, guidance, sections)

    template = _env.get_template("resume.tex.jinja2")
    return template.render(
        name=name,
        role=role,
        contacts=contacts,
        links=links,
        page_padding=page_padding_mm,
        accent=accent,
        accent_muted=accent_muted,
        body_color=body_color,
        meta_color=meta_color,
        header_bg=header_bg,
        header_text=header_text,
        sidebar_bg=sidebar_bg,
        divider_color=divider_color,
        tag_bg=tag_bg,
        tag_border=tag_border,
        name_size=name_size,
        role_size=role_size,
        meta_size=meta_size,
        body_size=body_size,
        heading_size=heading_size,
        tag_size=tag_size,
        name_weight=name_weight,
        body_leading=body_leading,
        heading_leading=heading_leading,
        name_leading=name_leading,
        role_leading=role_leading,
        meta_leading=meta_leading,
        tag_leading=tag_leading,
        heading_style=heading_style,
        is_uppercase=is_uppercase,
        header_font=header_font,
        body_font=body_font,
        header_font_name=_tex_font_name(header_font),
        body_font_name=_tex_font_name(body_font),
        section_gap=section_title_gap,
        item_gap=exp_gap,
        heading_margin=_px_to_pt(heading_margin),
        heading_rule_gap=_px_to_pt(heading_rule_gap),
        heading_rule_thick=_px_to_pt(heading_rule_thick),
        header_margin=_px_to_pt(header_margin),
        header_pad=_px_to_pt(header_pad),
        role_mt=_px_to_pt(role_mt),
        contact_gap=_px_to_pt(contact_gap),
        bullet_indent=_px_to_pt(bullet_indent),
        bullet_gap=bullet_item_sep,
        bullet_topsep=bullet_topsep,
        tag_gap=tag_gap_tex,
        tag_pad_x=_px_to_pt(tag_pad_x),
        tag_pad_y=_px_to_pt(tag_pad_y),
        tag_radius=_px_to_pt(tag_radius),
        tag_border_width=_px_to_pt(tag_border_width),
        sidebar_padding=sidebar_pad_pt,
        sidebar_radius=_px_to_pt(sidebar_radius),
        sidebar_inner_deduct=sidebar_inner_deduct,
        col_gap=_px_to_pt(col_gap),
        left_pct=left_pct,
        left_frac=left_frac,
        right_frac=right_frac,
        left_col_width=left_col_width,
        right_col_width=right_col_width,
        is_double=is_double,
        header_layout=header_layout,
        contact_layout=contact_layout,
        show_divider=show_divider,
        divider_thick=divider_thick,
        left_sections=section_data["left"],
        right_sections=section_data["right"],
    )


