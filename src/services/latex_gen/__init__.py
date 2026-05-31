"""
LaTeX resume generator — renders .tex matching the frontend HTML CSS variables.
Aligns with frontend RenderGuidanceSettings + buildCssVariables().
"""
from __future__ import annotations

import logging
import json
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
    lstrip_blocks=False,
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
    return round(px * 25.4 / 96, 4)


def _px_to_pt(px: float) -> float:
    return round(px * 72 / 96, 4)


def _font_px_to_pt(px: float) -> float:
    return round(px * 72 / 96, 4)


def _fmt_pt(v: float) -> str:
    """Format a pt value without trailing zeros or excessive precision."""
    rounded = round(v, 4)
    if rounded == int(rounded):
        return str(int(rounded))
    # Strip trailing zeros but keep at least one decimal if needed
    s = f"{rounded:.4f}".rstrip('0').rstrip('.')
    return s


def _tex_color(name: str, hex_val: str) -> str:
    """Format a complete \definecolor command."""
    return f"\\definecolor{{{name}}}{{HTML}}{{{hex_val}}}"


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


STYLE_SUPPORT = {
    "page.padding": "supported",
    "colors.palette": "supported",
    "typography.font_family": "supported",
    "typography.sizes": "supported",
    "typography.line_height": "supported",
    "header.layout": "supported",
    "header.contact_layout": "supported",
    "header.divider": "supported",
    "section.heading_style": "supported",
    "entry.date_style": "supported",
    "list.bullet_spacing": "supported",
    "tag.shape": "supported",
    "columns.two_column": "supported",
    "photo": "html_only",
}

LATEX_STYLE_TUNING = {
    # HTML has margin-bottom on sections, while LaTeX needs a pre-heading gap.
    # Keep this below 1.0 so successive sections do not visually double-space.
    "section_gap_factor": 0.38,
    "section_gap_max_pt": 5.5,
    # Article/item gaps in HTML are visible vertical rhythm; previous mapping
    # compressed them too much, making entry blocks look glued together.
    "entry_gap_factor": 0.72,
    "entry_gap_max_pt": 4.5,
    # Bullet/tag gaps should track CSS more closely than section gaps because
    # they sit inside already compact content blocks.
    "bullet_gap_factor": 0.50,
    "bullet_gap_min_pt": 0.45,
    "bullet_gap_max_pt": 2.25,
    "tag_gap_factor": 0.75,
    "tag_gap_min_pt": 1.25,
    "tag_gap_max_pt": 4.5,
    # LaTeX fonts tend to look looser than browser text at the same leading.
    "heading_leading_min": 1.12,
    "heading_leading_max": 1.28,
}


def build_latex_style_context(guidance: Dict[str, Any], html_source: Optional[str] = None) -> Dict[str, Any]:
    """Translate builder CSS vars/guidance into LaTeX-ready style semantics."""
    css_vars = _extract_css_vars(html_source)
    margins = guidance.get("margins", {}) or {}

    colors = {
        "accent": _css_hex_var(css_vars, "accent", guidance.get("accentColor", "31457f")),
        "accent_muted": _css_hex_var(css_vars, "accent-muted", "e5e5e5"),
        "body": _css_hex_var(css_vars, "body-color", guidance.get("bodyTextColor", "1d1d1f")),
        "meta": _css_hex_var(css_vars, "meta-color", guidance.get("metaTextColor", "5f6b7a")),
        "header_bg": _css_hex_var(css_vars, "header-bg", guidance.get("headerBgColor", "ffffff")),
        "header_text": _css_hex_var(css_vars, "header-color", guidance.get("headerTextColor", "1d1d1f")),
        "sidebar_bg": _css_hex_var(css_vars, "sidebar-bg", guidance.get("leftSidebarBg", "fafafa")),
        "divider": _css_hex_var(css_vars, "divider-color", guidance.get("headerDividerColor", "d1d1d1")),
        "tag_bg": _css_hex_var(css_vars, "tag-bg", guidance.get("tagBgColor", "f5f5f5")),
        "tag_border": _css_hex_var(css_vars, "tag-border", guidance.get("tagBorderColor", "e5e5e5")),
    }

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
    line_height = float(css_vars.get("line-height", _clh(guidance)) or _clh(guidance))

    typography = {
        "name_size": name_size,
        "role_size": role_size,
        "meta_size": meta_size,
        "body_size": body_size,
        "heading_size": heading_size,
        "tag_size": tag_size,
        "name_weight": _css_px_var(css_vars, "name-weight", _guidance_px(guidance, "nameFontWeight", 700)),
        "body_leading": round(body_size * line_height, 1),
        "heading_leading": round(
            heading_size
            * max(
                LATEX_STYLE_TUNING["heading_leading_min"],
                min(line_height, LATEX_STYLE_TUNING["heading_leading_max"]),
            ),
            1,
        ),
        "name_leading": round(name_size * 1.2, 1),
        "role_leading": round(role_size * 1.3, 1),
        "meta_leading": round(meta_size * 1.3, 1),
        "tag_leading": round(tag_size * 1.4, 1),
        "header_font": _font_key_from_css(str(css_vars.get("header-font", "")), str(guidance.get("headerFont", "serif"))),
        "body_font": _font_key_from_css(str(css_vars.get("body-font", "")), str(guidance.get("bodyFont", "sans-serif"))),
        "line_height": line_height,
    }

    page_padding_px = _css_px_var(
        css_vars,
        "page-padding",
        _guidance_px(guidance, "pagePaddingPx", min(margins.get("top", 12), margins.get("left", 12)) * 96 / 25.4),
    )
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

    spacing = {
        "page_padding_mm": _px_to_mm(page_padding_px),
        "section_title_gap": min(
            _px_to_pt(section_gap) * LATEX_STYLE_TUNING["section_gap_factor"],
            LATEX_STYLE_TUNING["section_gap_max_pt"],
        ),
        "entry_gap": min(
            _px_to_pt(item_gap) * LATEX_STYLE_TUNING["entry_gap_factor"],
            LATEX_STYLE_TUNING["entry_gap_max_pt"],
        ),
        "meta_gap": _px_to_pt(contact_gap),
        "heading_margin": _px_to_pt(heading_margin),
        "heading_rule_gap": _px_to_pt(heading_rule_gap),
        "heading_rule_thick": _px_to_pt(heading_rule_thick),
        "header_margin": _px_to_pt(header_margin),
        "header_pad": _px_to_pt(header_pad),
        "role_mt": _px_to_pt(role_mt),
        "contact_gap": _px_to_pt(contact_gap),
        "bullet_indent": _px_to_pt(bullet_indent),
        "bullet_gap": max(
            LATEX_STYLE_TUNING["bullet_gap_min_pt"],
            min(
                _px_to_pt(bullet_gap) * LATEX_STYLE_TUNING["bullet_gap_factor"],
                LATEX_STYLE_TUNING["bullet_gap_max_pt"],
            ),
        ),
        "bullet_topsep": max(0.0, min(_px_to_pt(bullet_top_gap), 2.5)),
        "tag_gap": max(
            LATEX_STYLE_TUNING["tag_gap_min_pt"],
            min(
                _px_to_pt(tag_gap) * LATEX_STYLE_TUNING["tag_gap_factor"],
                LATEX_STYLE_TUNING["tag_gap_max_pt"],
            ),
        ),
        "tag_pad_x": _px_to_pt(tag_pad_x),
        "tag_pad_y": _px_to_pt(tag_pad_y),
        "tag_radius": _px_to_pt(tag_radius),
        "tag_border_width": _px_to_pt(tag_border_width),
        "sidebar_padding": _px_to_pt(sidebar_padding),
        "sidebar_radius": _px_to_pt(sidebar_radius),
        "col_gap": _px_to_pt(col_gap),
    }

    left_basis_px = _css_px_var(
        css_vars,
        "left-basis",
        max(120.0, round(((content_width_px - col_gap) * float(guidance.get("leftWidthPercent", 36))) / 100)),
    )
    left_pct = round(left_basis_px / content_width_px * 100, 2)
    left_frac_num = max(0.1, min(0.9, left_pct / 100))
    right_frac_num = max(0.1, min(0.9, 1 - left_pct / 100))
    half_col_gap = round(spacing["col_gap"] / 2, 2)
    sidebar_inner_deduct = round(spacing["sidebar_padding"] * 2, 2)
    left_frac = f"{left_frac_num:.4f}".lstrip("0")
    right_frac = f"{right_frac_num:.4f}".lstrip("0")

    layout = {
        "column_mode": str(guidance.get("columnMode", "double")),
        "is_double": str(guidance.get("columnMode", "double")) == "double",
        "header_layout": str(guidance.get("headerLayout", "left")),
        "contact_layout": str(guidance.get("contactLayout", "inline")),
        "show_divider": bool(guidance.get("showHeaderDivider", True)),
        "divider_thick": _css_px_var(css_vars, "divider-thick", _guidance_px(guidance, "headerDividerThicknessPx", 1)),
        "content_width_px": content_width_px,
        "left_pct": left_pct,
        "left_frac": left_frac,
        "right_frac": right_frac,
        "sidebar_inner_deduct": sidebar_inner_deduct,
        "left_col_width": rf"\dimexpr {left_frac}\textwidth - {half_col_gap}pt - {sidebar_inner_deduct}pt\relax",
        "right_col_width": rf"\dimexpr {right_frac}\textwidth - {half_col_gap}pt\relax",
    }

    heading = {
        "style": str(guidance.get("sectionHeadingStyle", "underline")),
        "case": str(guidance.get("sectionHeadingCase", "uppercase")).upper(),
        "is_uppercase": str(guidance.get("sectionHeadingCase", "uppercase")).upper() == "UPPERCASE",
        "boxed_padding_x": _px_to_pt(6),
        "boxed_padding_y": _px_to_pt(3),
        "bar_width": _px_to_pt(3),
        "bar_pad": _px_to_pt(8),
        "bar_height": max(typography["heading_leading"], _px_to_pt(14)),
        "bar_raise": _px_to_pt(1),
    }

    entry = {
        "date_style": str(guidance.get("dateStyle", "muted")),
        "date_layout": {
            "inline": "title_row_right",
            "bottom-inline": "meta_row_right",
        }.get(str(guidance.get("dateStyle", "muted")), "muted_lines"),
    }

    return {
        "css_vars": css_vars,
        "colors": colors,
        "typography": typography,
        "spacing": spacing,
        "layout": layout,
        "heading": heading,
        "entry": entry,
        "support": STYLE_SUPPORT,
    }


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
    is_inline = date_style == "inline"

    if key == "summary":
        text = str(resume_obj.get("summary", "")).strip()
        if text:
            return {"title": title_tex, "type": "text", "content": _escape_latex(text)}

    elif key == "workExperience":
        items = resume_obj.get("workExperience") or []
        entries = _experience_entries(items, date_style, bullet_style, body_size, "exp")
        if entries:
            return {"title": title_tex, "type": "experience", "items": entries, "date_style": date_style}

    elif key == "personalProjects":
        items = resume_obj.get("personalProjects") or []
        entries = _experience_entries(items, date_style, bullet_style, body_size, "proj")
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
            # Render description bullets if present
            desc = edu.get("description", [])
            desc_items = []
            if isinstance(desc, list) and len(desc) > 0:
                desc_items = [_escape_latex(str(d).strip()) for d in desc if str(d).strip()]
            elif isinstance(desc, str) and desc.strip():
                desc_items = [_escape_latex(desc.strip())]
            entries.append({
                "institution": inst or "Institution",
                "degree": degree,
                "years": years,
                "gpa": gpa,
                "description": desc_items,
                "is_bottom": is_bottom,
                "is_inline": is_inline,
            })
        if entries:
            return {"title": title_tex, "type": "education", "items": entries, "date_style": date_style}

    elif key == "research":
        items = resume_obj.get("research") or []
        entries = _experience_entries(items, date_style, bullet_style, body_size, "research")
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
        if isinstance(raw, str) and raw.strip():
            # Split string on commas/semicolons (same as HTML renderer)
            raw = [x.strip() for x in re.split(r'[,;，；]+', raw) if x.strip()]
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
    date_style: str,
    bullet_style: str,
    body_size: float,
    kind: str,
) -> list:
    entries = []
    is_bottom = date_style == "bottom-inline"
    is_inline = date_style == "inline"
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
            "is_inline": is_inline,
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
    if not sections:
        sections = _default_sections()

    pi = personal_info or resume_obj.get("personalInfo", {}) or {}
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

    style = build_latex_style_context(guidance, html_source)
    colors = style["colors"]
    typography = style["typography"]
    spacing = style["spacing"]
    layout = style["layout"]
    heading = style["heading"]

    accent = colors["accent"]
    accent_muted = colors["accent_muted"]
    body_color = colors["body"]
    meta_color = colors["meta"]
    header_bg = colors["header_bg"]
    header_text = colors["header_text"]
    sidebar_bg = colors["sidebar_bg"]
    divider_color = colors["divider"]
    tag_bg = colors["tag_bg"]
    tag_border = colors["tag_border"]

    name_size = typography["name_size"]
    role_size = typography["role_size"]
    meta_size = typography["meta_size"]
    body_size = typography["body_size"]
    heading_size = typography["heading_size"]
    tag_size = typography["tag_size"]
    name_weight = typography["name_weight"]
    body_leading = typography["body_leading"]
    heading_leading = typography["heading_leading"]
    name_leading = typography["name_leading"]
    role_leading = typography["role_leading"]
    meta_leading = typography["meta_leading"]
    tag_leading = typography["tag_leading"]
    header_font = typography["header_font"]
    body_font = typography["body_font"]

    heading_style = heading["style"]
    is_uppercase = heading["is_uppercase"]

    page_padding_mm = spacing["page_padding_mm"]
    section_title_gap = spacing["section_title_gap"]
    exp_gap = spacing["entry_gap"]
    meta_gap = spacing["meta_gap"]
    bullet_item_sep = spacing["bullet_gap"]
    bullet_topsep = spacing["bullet_topsep"]
    tag_gap_tex = spacing["tag_gap"]

    is_double = layout["is_double"]
    header_layout = layout["header_layout"]
    contact_layout = layout["contact_layout"]
    show_divider = layout["show_divider"]
    divider_thick = layout["divider_thick"]
    left_pct = layout["left_pct"]
    left_frac = layout["left_frac"]
    right_frac = layout["right_frac"]
    left_col_width = layout["left_col_width"]
    right_col_width = layout["right_col_width"]
    sidebar_inner_deduct = layout["sidebar_inner_deduct"]

    # sections split by column
    section_data = _resolve_sections(resume_obj, guidance, sections)

    # Detect Chinese content — if present, enable xeCJK + CJK fonts
    has_chinese = bool(re.search(r'[一-鿿㐀-䶿]', json.dumps(resume_obj, ensure_ascii=False)))

    template = _env.get_template("resume.tex.jinja2")

    # Pre-compute heading LaTeX chunks to avoid Jinja2 backslash conflicts
    font_cmd = (
        r"{\fontsize{" + f"{heading_size}" + r"}{" + f"{heading_leading}"
        + r"}\selectfont\bfseries\color{accent}"
    )
    if heading_style == "boxed":
        heading_prefix = (
            r"\noindent\begin{tcolorbox}["
            r"colback=tagbg,colframe=accentmuted,arc=0pt,outer arc=0pt,"
            rf"boxrule={_px_to_pt(1)}pt,"
            rf"top={heading['boxed_padding_y']}pt,bottom={heading['boxed_padding_y']}pt,"
            rf"left={heading['boxed_padding_x']}pt,right={heading['boxed_padding_x']}pt,"
            r"enhanced,boxsep=0pt,before skip=0pt,after skip=0pt]"
            + font_cmd
        )
        heading_suffix = r"}\end{tcolorbox}"
    elif heading_style == "bar":
        heading_prefix = (
            rf"\noindent\raisebox{{-{heading['bar_raise']}pt}}{{\textcolor{{accent}}{{\rule{{{heading['bar_width']}pt}}{{{heading['bar_height']}pt}}}}}}"
            rf"\hspace{{{heading['bar_pad']}pt}}"
            + font_cmd
        )
        heading_suffix = r"}"
    elif heading_style == "underline":
        heading_prefix = r"\noindent" + font_cmd
        heading_suffix = (
            r"}\par\vspace{" + f"{spacing['heading_rule_gap']}" + r"pt}"
            r"\noindent\textcolor{accentmuted}{\rule{\linewidth}{"
            + f"{spacing['heading_rule_thick']}" + r"pt}}"
        )
    else:
        heading_prefix = r"\noindent" + font_cmd
        heading_suffix = r"}"

    # Pre-compute macro definitions to avoid Jinja2 #-escaping issues
    cvsection_def = (
        r"\newcommand{\cvsection}[1]{ %" + "\n"
        r"  \par\vspace{" + f"{section_title_gap}" + r" pt}%" + "\n"
        + heading_prefix + r"%" + "\n"
        + (r"\MakeUppercase{ #1}" if is_uppercase else r" #1") + r"%" + "\n"
        + heading_suffix + r"%" + "\n"
        r"  \par\vspace{" + f"{spacing['heading_margin']}" + r" pt}%" + "\n"
        r"}"
    )

    cvtag_def = (
        r"\newcommand{\cvtag}[1]{" + "\n"
        r"  \tcbox[" + "\n"
        r"    on line," + "\n"
        r"    colback=tagbg," + "\n"
        r"    colframe=tagborder," + "\n"
        r"    boxrule=" + f"{spacing['tag_border_width']}" + r"pt," + "\n"
        r"    arc=" + f"{spacing['tag_radius']}" + r"pt," + "\n"
        r"    boxsep=0pt," + "\n"
        r"    left=" + f"{spacing['tag_pad_x']}" + r"pt," + "\n"
        r"    right=" + f"{spacing['tag_pad_x']}" + r"pt," + "\n"
        r"    top=" + f"{spacing['tag_pad_y']}" + r"pt," + "\n"
        r"    bottom=" + f"{spacing['tag_pad_y']}" + r"pt" + "\n"
        r"  ]{\fontsize{" + f"{tag_size}" + r"}{" + f"{tag_leading}" + r"}\selectfont\bodyfont\strut#1}" + "\n"
        r"}"
    )

    expheader_bottom_def = (
        r"\newcommand{\expheader}[3]{" + "\n"
        r"  \par\vspace{" + f"{exp_gap}" + r" pt}" + "\n"
        r"  \noindent{\fontsize{" + f"{body_size}" + r"}{" + f"{body_leading}" + r"}\selectfont\bodyfont\bfseries #1}" + "\n"
        r"  \par\noindent{" + "\n"
        r"    \fontsize{" + f"{meta_size}" + r"}{" + f"{meta_leading}" + r"}\selectfont" + "\n"
        r"    \color{meta}\bodyfont #2%" + "\n"
        r"    \if\relax\detokenize{#3}\relax\else\hfill #3\fi" + "\n"
        r"    \par}" + "\n"
        r"}"
    )
    expheader_inline_def = (
        r"\newcommand{\expheaderinline}[3]{" + "\n"
        r"  \par\vspace{" + f"{exp_gap}" + r" pt}" + "\n"
        r"  \noindent{" + "\n"
        r"    \fontsize{" + f"{body_size}" + r"}{" + f"{body_leading}" + r"}\selectfont\bodyfont\bfseries #1%" + "\n"
        r"    \if\relax\detokenize{#3}\relax\else{\hfill\fontsize{" + f"{meta_size}" + r"}{" + f"{meta_leading}" + r"}\selectfont\mdseries\color{meta}#3}\fi" + "\n"
        r"    \par}" + "\n"
        r"  \if\relax\detokenize{#2}\relax\else" + "\n"
        r"    \par\vspace{" + f"{meta_gap}" + r" pt}" + "\n"
        r"    \noindent{\fontsize{" + f"{meta_size}" + r"}{" + f"{meta_leading}" + r"}\selectfont\color{meta}\bodyfont #2\par}" + "\n"
        r"  \fi" + "\n"
        r"}"
    )
    expheader_muted_def = (
        r"\newcommand{\expheadermuted}[3]{" + "\n"
        r"  \par\vspace{" + f"{exp_gap}" + r" pt}" + "\n"
        r"  \noindent{\fontsize{" + f"{body_size}" + r"}{" + f"{body_leading}" + r"}\selectfont\bodyfont\bfseries #1\par}" + "\n"
        r"  \if\relax\detokenize{#2}\relax\else" + "\n"
        r"    \par\vspace{" + f"{meta_gap}" + r" pt}" + "\n"
        r"    \noindent{\fontsize{" + f"{meta_size}" + r"}{" + f"{meta_leading}" + r"}\selectfont\color{meta}\bodyfont #2\par}" + "\n"
        r"  \fi" + "\n"
        r"  \if\relax\detokenize{#3}\relax\else" + "\n"
        r"    \par\vspace{" + f"{meta_gap}" + r" pt}" + "\n"
        r"    \noindent{\fontsize{" + f"{meta_size}" + r"}{" + f"{meta_leading}" + r"}\selectfont\color{meta}\bodyfont #3\par}" + "\n"
        r"  \fi" + "\n"
        r"}"
    )

    return template.render(
        name=name,
        role=role,
        contacts=contacts,
        links=links,
        cvsection_def=cvsection_def,
        cvtag_def=cvtag_def,
        expheader_def="\n\n".join([expheader_bottom_def, expheader_inline_def, expheader_muted_def]),
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
        heading_prefix=heading_prefix,
        heading_suffix=heading_suffix,
        header_font=header_font,
        body_font=body_font,
        has_chinese=has_chinese,
        header_font_name=_tex_font_name(header_font),
        body_font_name=_tex_font_name(body_font),
        section_gap=section_title_gap,
        item_gap=exp_gap,
        heading_margin=spacing["heading_margin"],
        heading_rule_gap=spacing["heading_rule_gap"],
        heading_rule_thick=spacing["heading_rule_thick"],
        header_margin=spacing["header_margin"],
        header_pad=spacing["header_pad"],
        role_mt=spacing["role_mt"],
        contact_gap=spacing["contact_gap"],
        bullet_indent=spacing["bullet_indent"],
        bullet_gap=bullet_item_sep,
        bullet_topsep=bullet_topsep,
        tag_gap=tag_gap_tex,
        tag_pad_x=spacing["tag_pad_x"],
        tag_pad_y=spacing["tag_pad_y"],
        tag_radius=spacing["tag_radius"],
        tag_border_width=spacing["tag_border_width"],
        sidebar_padding=spacing["sidebar_padding"],
        sidebar_radius=spacing["sidebar_radius"],
        sidebar_inner_deduct=sidebar_inner_deduct,
        col_gap=spacing["col_gap"],
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
