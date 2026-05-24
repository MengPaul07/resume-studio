import html
import json
import re
from typing import Any, Dict, List


def to_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def to_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def escape_text(value: Any) -> str:
    return html.escape(str(value or ""))


def display_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, list):
        parts = [display_text(item).strip() for item in value]
        return " | ".join([part for part in parts if part])
    if isinstance(value, dict):
        parts = [display_text(child).strip() for child in value.values()]
        return " | ".join([part for part in parts if part])
    return str(value)


def flatten_text_entries(value: Any, path: str = "") -> List[Dict[str, str]]:
    if value is None:
        return []
    if isinstance(value, (str, int, float, bool)):
        text = display_text(value).strip()
        return [{"path": path or "root", "text": text}] if text else []
    if isinstance(value, list):
        rows: List[Dict[str, str]] = []
        for index, item in enumerate(value):
            rows.extend(flatten_text_entries(item, f"{path}[{index}]"))
        return rows
    if isinstance(value, dict):
        rows: List[Dict[str, str]] = []
        for key, child in value.items():
            rows.extend(flatten_text_entries(child, f"{path}.{key}" if path else str(key)))
        return rows
    return []


def mark_rendered_path(rendered_paths: set[str], path: str) -> None:
    if not path:
        return
    rendered_paths.add(path)
    current = path
    while "." in current:
        current = ".".join(current.split(".")[:-1])
        if current:
            rendered_paths.add(current)
    current = path
    while re.search(r"\[\d+\]$", current):
        rendered_paths.add(current)
        current = re.sub(r"\[\d+\]$", "", current)
        if current:
            rendered_paths.add(current)


def strip_code_fence(text: str) -> str:
    raw = (text or "").strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if len(lines) >= 2:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw


def extract_json_dict(text: str) -> Dict[str, Any]:
    raw = strip_code_fence(text)
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return {}

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def extract_html_block(text: str) -> str:
    return strip_code_fence(text)


def get_theme(layout_preferences: Dict[str, Any] | None = None) -> str:
    preferences = layout_preferences if isinstance(layout_preferences, dict) else {}
    return str(preferences.get("presentation", {}).get("theme") or preferences.get("theme", "modern"))


def get_metadata(layout_preferences: Dict[str, Any] | None = None) -> Dict[str, Any]:
    preferences = layout_preferences if isinstance(layout_preferences, dict) else {}
    metadata = preferences.get("metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def default_layout_plan(theme: str = "modern") -> Dict[str, Any]:
    return {
        "theme": theme,
        "page": {
            "format": "a4",
            "columns": [
                {"id": "left", "width": "36%"},
                {"id": "right", "width": "64%"},
            ],
            "max_width_px": 820,
            "padding_px": 28,
            "margins_mm": {"top": 16, "right": 16, "bottom": 16, "left": 16},
            "boundary_policy": {
                "enforce_a4": True,
                "overflow_behavior": "forbid",
                "content_must_fit": True,
            },
            "pagination_policy": {
                "page_count_mode": "single-page",
                "target_pages": 1,
            },
        },
        "section_map": {
            "left": ["summary", "technicalSkills", "languages", "certificationsTraining"],
            "right": ["workExperience", "education", "personalProjects", "research", "awards", "customSections"],
        },
        "constraints": {
            "preserve_facts": True,
            "max_items": {"workExperience": 8, "personalProjects": 8, "education": 6, "research": 6},
            "bullet_style": "impact_first",
            "date_style": "ym",
        },
    }


def default_style_options(theme: str = "modern") -> List[Dict[str, Any]]:
    return [
        {
            "id": f"{theme}-clean",
            "name": "Clean",
            "theme": theme,
            "palette": {
                "primary": "#0b3a66",
                "accent": "#1f8a70",
                "text": "#111827",
                "muted": "#4b5563",
                "bg": "#f5f7fb",
                "paper": "#ffffff",
            },
            "typography": {
                "font_family": "'Segoe UI', 'PingFang SC', sans-serif",
                "base_size_px": 14,
                "title_size_px": 28,
            },
            "effects": {
                "title_shadow": "none",
                "card_shadow": "none",
                "section_title_transform": "uppercase",
                "border_radius_px": 10,
            },
        },
        {
            "id": f"{theme}-vivid",
            "name": "Vivid",
            "theme": theme,
            "palette": {
                "primary": "#0f172a",
                "accent": "#db2777",
                "text": "#111827",
                "muted": "#475569",
                "bg": "#f8f4ff",
                "paper": "#ffffff",
            },
            "typography": {
                "font_family": "'Poppins', 'PingFang SC', sans-serif",
                "base_size_px": 14,
                "title_size_px": 30,
            },
            "effects": {
                "title_shadow": "2px 2px 0 rgba(219, 39, 119, 0.18)",
                "card_shadow": "0 1px 0 rgba(15, 23, 42, 0.16)",
                "section_title_transform": "uppercase",
                "border_radius_px": 12,
            },
        },
        {
            "id": f"{theme}-ink",
            "name": "Ink",
            "theme": theme,
            "palette": {
                "primary": "#111827",
                "accent": "#2563eb",
                "text": "#111827",
                "muted": "#374151",
                "bg": "#f3f4f6",
                "paper": "#ffffff",
            },
            "typography": {
                "font_family": "'IBM Plex Sans', 'PingFang SC', sans-serif",
                "base_size_px": 13,
                "title_size_px": 27,
            },
            "effects": {
                "title_shadow": "none",
                "card_shadow": "2px 2px 0 rgba(17, 24, 39, 0.2)",
                "section_title_transform": "uppercase",
                "border_radius_px": 4,
            },
        },
    ]


def safe_hex(value: Any, fallback: str) -> str:
    raw = str(value or "").strip()
    return raw if re.fullmatch(r"#[0-9a-fA-F]{6}", raw) else fallback


def safe_font(value: Any, fallback: str) -> str:
    raw = str(value or "").strip()
    return raw or fallback


def safe_int(value: Any, fallback: int, min_v: int, max_v: int) -> int:
    try:
        number = int(value)
    except Exception:
        number = fallback
    return max(min_v, min(max_v, number))


def safe_shadow(value: Any, fallback: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return fallback
    allowed = set("0123456789pxrem.%,-()# abcdefABCDEFnoneinsetrgba")
    return raw if all(ch in allowed for ch in raw) else fallback


def safe_transform(value: Any, fallback: str) -> str:
    raw = str(value or "").strip().lower()
    return raw if raw in {"uppercase", "none", "capitalize"} else fallback


def normalize_layout_plan(raw_plan: Any, theme: str) -> Dict[str, Any]:
    base = default_layout_plan(theme)
    plan = raw_plan if isinstance(raw_plan, dict) else {}

    page = to_dict(plan.get("page"))
    columns = to_list(page.get("columns"))
    normalized_columns = list(base["page"]["columns"])
    if len(columns) == 1 and isinstance(columns[0], dict):
        normalized_columns = [{"id": str(columns[0].get("id") or "main"), "width": "100%"}]
    elif len(columns) >= 2 and isinstance(columns[0], dict) and isinstance(columns[1], dict):
        normalized_columns = [
            {"id": str(columns[0].get("id") or "left"), "width": str(columns[0].get("width") or "36%")},
            {"id": str(columns[1].get("id") or "right"), "width": str(columns[1].get("width") or "64%")},
        ]

    section_map = to_dict(plan.get("section_map"))
    constraints = to_dict(plan.get("constraints"))
    max_items = to_dict(constraints.get("max_items"))
    margins = to_dict(page.get("margins_mm"))
    boundary_policy = to_dict(page.get("boundary_policy"))
    pagination_policy = to_dict(page.get("pagination_policy"))
    page_count_mode = str(pagination_policy.get("page_count_mode") or "single-page").strip().lower()
    if page_count_mode not in {"single-page", "double-page"}:
        page_count_mode = "single-page"
    target_pages = safe_int(pagination_policy.get("target_pages"), 1, 1, 2)
    if page_count_mode == "single-page":
        target_pages = 1

    return {
        "theme": str(plan.get("theme") or base["theme"]),
        "page": {
            "format": "a4",
            "columns": normalized_columns,
            "max_width_px": safe_int(page.get("max_width_px"), int(base["page"]["max_width_px"]), 760, 1320),
            "padding_px": safe_int(page.get("padding_px"), int(base["page"]["padding_px"]), 12, 64),
            "margins_mm": {
                "top": safe_int(margins.get("top"), 16, 6, 24),
                "right": safe_int(margins.get("right"), 16, 6, 24),
                "bottom": safe_int(margins.get("bottom"), 16, 6, 24),
                "left": safe_int(margins.get("left"), 16, 6, 24),
            },
            "boundary_policy": {
                "enforce_a4": bool(boundary_policy.get("enforce_a4", True)),
                "overflow_behavior": "forbid",
                "content_must_fit": bool(boundary_policy.get("content_must_fit", True)),
            },
            "pagination_policy": {
                "page_count_mode": page_count_mode,
                "target_pages": target_pages,
            },
        },
        "section_map": {
            "left": [str(x) for x in to_list(section_map.get("left"))] or list(base["section_map"]["left"]),
            "right": [str(x) for x in to_list(section_map.get("right"))] or list(base["section_map"]["right"]),
        },
        "constraints": {
            "preserve_facts": bool(constraints.get("preserve_facts", True)),
            "max_items": {
                "workExperience": safe_int(max_items.get("workExperience"), 8, 1, 12),
                "personalProjects": safe_int(max_items.get("personalProjects"), 8, 1, 12),
                "education": safe_int(max_items.get("education"), 6, 1, 10),
            },
            "bullet_style": str(constraints.get("bullet_style") or "impact_first"),
            "date_style": str(constraints.get("date_style") or "ym"),
        },
    }


def normalize_style_options(raw_styles: Any, theme: str) -> List[Dict[str, Any]]:
    defaults = default_style_options(theme)
    source = raw_styles if isinstance(raw_styles, list) else []

    normalized: List[Dict[str, Any]] = []
    for idx, row in enumerate(source):
        if not isinstance(row, dict):
            continue
        fallback = defaults[idx % len(defaults)]
        palette = to_dict(row.get("palette"))
        typography = to_dict(row.get("typography"))
        effects = to_dict(row.get("effects"))
        normalized.append(
            {
                "id": str(row.get("id") or f"style-{idx + 1}"),
                "name": str(row.get("name") or f"Style {idx + 1}"),
                "theme": str(row.get("theme") or fallback["theme"]),
                "palette": {
                    "primary": safe_hex(palette.get("primary"), str(fallback["palette"]["primary"])),
                    "accent": safe_hex(palette.get("accent"), str(fallback["palette"]["accent"])),
                    "text": safe_hex(palette.get("text"), str(fallback["palette"]["text"])),
                    "muted": safe_hex(palette.get("muted"), str(fallback["palette"]["muted"])),
                    "bg": safe_hex(palette.get("bg"), str(fallback["palette"]["bg"])),
                    "paper": safe_hex(palette.get("paper"), str(fallback["palette"]["paper"])),
                },
                "typography": {
                    "font_family": safe_font(typography.get("font_family"), str(fallback["typography"]["font_family"])),
                    "base_size_px": safe_int(typography.get("base_size_px"), int(fallback["typography"]["base_size_px"]), 11, 18),
                    "title_size_px": safe_int(typography.get("title_size_px"), int(fallback["typography"]["title_size_px"]), 22, 40),
                },
                "effects": {
                    "title_shadow": safe_shadow(effects.get("title_shadow"), str(fallback["effects"]["title_shadow"])),
                    "card_shadow": safe_shadow(effects.get("card_shadow"), str(fallback["effects"]["card_shadow"])),
                    "section_title_transform": safe_transform(
                        effects.get("section_title_transform"), str(fallback["effects"]["section_title_transform"])
                    ),
                    "border_radius_px": safe_int(effects.get("border_radius_px"), int(fallback["effects"]["border_radius_px"]), 0, 18),
                },
            }
        )

    deduped: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in normalized:
        style_id = str(item.get("id") or "").strip()
        if not style_id or style_id in seen:
            continue
        deduped.append(item)
        seen.add(style_id)

    for fallback in defaults:
        if len(deduped) >= 4:
            break
        if fallback["id"] in seen:
            continue
        deduped.append(fallback)
        seen.add(fallback["id"])

    return deduped[:4]


def build_json_block(title: str, payload: Dict[str, Any]) -> str:
    return f"## {title}\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```"


def _render_bullet_list(items: List[str]) -> str:
    valid = [escape_text(item) for item in items if str(item or "").strip()]
    if not valid:
        return "<p class='muted'>N/A</p>"
    return "<ul>" + "".join(f"<li>{item}</li>" for item in valid) + "</ul>"


def _ensure_list_or_empty(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(x) for x in value if str(x or "").strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _render_item_cards(
    items: List[Dict[str, Any]],
    *,
    title_key: str,
    subtitle_keys: List[str],
    years_key: str,
    desc_key: str,
) -> str:
    cards: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = escape_text(item.get(title_key) or "")
        subtitle = " | ".join(escape_text(item.get(key) or "") for key in subtitle_keys if item.get(key))
        years = escape_text(item.get(years_key) or "")
        desc = item.get(desc_key)
        desc_html = _render_bullet_list([str(x) for x in desc]) if isinstance(desc, list) else f"<p>{escape_text(desc)}</p>"
        cards.append(
            "<article class='resume-item card'>"
            f"<div class='resume-row'><h3 class='resume-item-title'>{title}</h3><span class='resume-date'>{years}</span></div>"
            f"<p class='resume-item-subtitle muted'>{subtitle}</p>"
            f"{desc_html}"
            "</article>"
        )
    return f"<div class='resume-items'>{''.join(cards)}</div>" if cards else "<p class='muted'>N/A</p>"


def _normalize_url(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return f"https://{raw}"


def render_fallback_html(
    resume_obj: Dict[str, Any],
    active_style: Dict[str, Any],
    *,
    template_id: str = "swiss-two-column",
    column_mode: str = "double",
    page_count_mode: str = "single-page",
    target_pages: int = 1,
) -> str:
    palette = to_dict(active_style.get("palette"))
    typography = to_dict(active_style.get("typography"))
    effects = to_dict(active_style.get("effects"))

    personal = to_dict(resume_obj.get("personalInfo"))
    summary_raw = resume_obj.get("summary")
    summary = ""
    if isinstance(summary_raw, list):
        valid = [escape_text(x) for x in summary_raw if str(x or "").strip()]
        if valid:
            summary = _render_bullet_list(valid)
    elif summary_raw:
        summary = escape_text(summary_raw)
    additional = to_dict(resume_obj.get("additional"))
    work = [x for x in to_list(resume_obj.get("workExperience")) if isinstance(x, dict)]
    education = [x for x in to_list(resume_obj.get("education")) if isinstance(x, dict)]
    projects = [x for x in to_list(resume_obj.get("personalProjects")) if isinstance(x, dict)]
    custom_sections = to_dict(resume_obj.get("customSections"))
    rendered_paths: set[str] = set()

    skills = _ensure_list_or_empty(additional.get("technicalSkills"))
    languages = _ensure_list_or_empty(additional.get("languages"))
    certs = _ensure_list_or_empty(additional.get("certificationsTraining"))
    awards = _ensure_list_or_empty(additional.get("awards"))

    custom_html_parts: List[str] = []
    for key, value in custom_sections.items():
        section = to_dict(value)
        section_type = str(section.get("sectionType", "text"))
        title = escape_text(key.replace("_", " ").title())
        if section_type == "stringList":
            body = _render_bullet_list([str(x) for x in to_list(section.get("items"))])
        elif section_type == "itemList":
            item_rows = [x for x in to_list(section.get("items")) if isinstance(x, dict)]
            body = _render_item_cards(
                item_rows,
                title_key="title",
                subtitle_keys=["subtitle"],
                years_key="years",
                desc_key="description",
            )
        else:
            body = f"<p>{escape_text(section.get('text') or '')}</p>"
        custom_html_parts.append(f"<section data-section='customSections'><h2>{title}</h2>{body}</section>")

    contact_parts: List[str] = []
    email = str(personal.get("email") or "").strip()
    phone = str(personal.get("phone") or "").strip()
    location = str(personal.get("location") or "").strip()
    website = str(personal.get("website") or "").strip()
    linkedin = str(personal.get("linkedin") or "").strip()
    github = str(personal.get("github") or "").strip()
    if email:
        contact_parts.append(f"<a class='resume-link' href='mailto:{escape_text(email)}'>{escape_text(email)}</a>")
    if phone:
        contact_parts.append(f"<a class='resume-link' href='tel:{escape_text(phone)}'>{escape_text(phone)}</a>")
    if location:
        contact_parts.append(f"<span>{escape_text(location)}</span>")
    if website:
        safe = _normalize_url(website)
        contact_parts.append(
            f"<a class='resume-link' href='{escape_text(safe)}' target='_blank' rel='noopener noreferrer'>{escape_text(website)}</a>"
        )
    if linkedin:
        safe = _normalize_url(linkedin)
        contact_parts.append(
            f"<a class='resume-link' href='{escape_text(safe)}' target='_blank' rel='noopener noreferrer'>{escape_text(linkedin)}</a>"
        )
    if github:
        safe = _normalize_url(github)
        contact_parts.append(
            f"<a class='resume-link' href='{escape_text(safe)}' target='_blank' rel='noopener noreferrer'>{escape_text(github)}</a>"
        )

    contact_html = " <span class='dot'>|</span> ".join(contact_parts) if contact_parts else ""

    is_modern_single = template_id == "modern"
    is_modern_double = template_id == "modern-two-column"
    title_class_main = (
        "section-title-accent"
        if is_modern_single
        else "sectionTitleAccent"
        if is_modern_double
        else "resume-section-title"
    )
    title_class_side = "resume-section-title-sm" if column_mode == "double" else title_class_main

    summary_fb = "<p class='muted'>N/A</p>"
    left_col = (
        f"<section data-section='summary' class='resume-section'><h2 class='{title_class_main}'>Summary</h2>{summary or summary_fb}</section>"
        f"<section data-section='technicalSkills' class='resume-section'><h2 class='{title_class_side}'>Technical Skills</h2>{_render_bullet_list(skills)}</section>"
        f"<section data-section='languages' class='resume-section'><h2 class='{title_class_side}'>Languages</h2>{_render_bullet_list(languages)}</section>"
        f"<section data-section='certifications' class='resume-section'><h2 class='{title_class_main}'>Certifications</h2>{_render_bullet_list(certs)}</section>"
        f"<section data-section='awards' class='resume-section'><h2 class='{title_class_side}'>Awards</h2>{_render_bullet_list(awards)}</section>"
    )
    right_col = (
        f"<section data-section='workExperience' class='resume-section'><h2 class='{title_class_main}'>Work Experience</h2>{_render_item_cards(work, title_key='title', subtitle_keys=['company', 'location'], years_key='years', desc_key='description')}</section>"
        f"<section data-section='personalProjects' class='resume-section'><h2 class='{title_class_main}'>Projects</h2>{_render_item_cards(projects, title_key='name', subtitle_keys=['role'], years_key='years', desc_key='description')}</section>"
        f"<section data-section='education' class='resume-section'><h2 class='{title_class_side}'>Education</h2>{_render_item_cards(education, title_key='institution', subtitle_keys=['degree'], years_key='years', desc_key='description')}</section>"
        + "".join(custom_html_parts)
    )

    single_flow = left_col + right_col
    body_content = (
        f"<div class='resume-grid grid' data-layout-columns='resume'><aside class='resume-left mainColumn'>{left_col}</aside><section class='resume-right sidebarColumn'>{right_col}</section></div>"
        if column_mode == "double"
        else f"<div class='resume-single'>{single_flow}</div>"
    )

    name_underline = "<div class='name-underline' aria-hidden='true'></div>" if is_modern_single else ""
    name_extra_class = "nameAccent" if is_modern_double else ""

    return f"""<!doctype html>
<html lang="en" data-style-id="{escape_text(active_style.get('id') or 'fallback')}" data-template-id="{escape_text(template_id)}" data-column-mode="{escape_text(column_mode)}" data-page-count-mode="{escape_text(page_count_mode)}" data-target-pages="{escape_text(target_pages)}">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{escape_text(personal.get('name') or 'Resume')}</title>
<style>
html {{
  --primary: {palette.get('primary', '#0b3a66')};
  --accent: {palette.get('accent', '#1f8a70')};
  --text: {palette.get('text', '#111827')};
  --muted: {palette.get('muted', '#4b5563')};
  --bg: {palette.get('bg', '#f5f7fb')};
  --paper: {palette.get('paper', '#ffffff')};
  --title-shadow: {effects.get('title_shadow', 'none')};
  --card-shadow: {effects.get('card_shadow', '2px 2px 0 rgba(0,0,0,.1)')};
}}
body {{ margin: 0; font-family: {typography.get('font_family', "'IBM Plex Sans', 'PingFang SC', sans-serif")}; background: var(--bg); color: var(--text); }}
.page {{ max-width: 210mm; margin: 0 auto; background: var(--paper); border: 2px solid #000; padding: 8mm 10mm; }}
.resume-header {{ text-align: center; border-bottom: 1px solid #000; padding-bottom: 8px; margin-bottom: 10px; }}
.resume-name {{ margin: 0; color: var(--primary); text-transform: uppercase; letter-spacing: .02em; text-shadow: var(--title-shadow); font-size: {typography.get('title_size_px', 30)}px; line-height: 1.1; }}
.resume-role {{ margin: 4px 0 8px 0; color: #1f2937; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }}
.resume-contact {{ font-size: 11px; color: #374151; line-height: 1.4; }}
.resume-link {{ color: var(--primary); text-decoration: none; border-bottom: 1px solid transparent; }}
.resume-link:hover {{ border-bottom-color: var(--primary); }}
.dot {{ color: #6b7280; }}
.resume-grid {{ display: grid; grid-template-columns: 36% 64%; gap: 14px; }}
.grid {{ display: grid; }}
.mainColumn {{ display: flex; flex-direction: column; gap: 10px; border-right: 1px solid #d1d5db; padding-right: 10px; }}
.sidebarColumn {{ display: flex; flex-direction: column; gap: 10px; padding-left: 8px; min-width: 0; }}
.resume-section {{ margin-bottom: 10px; }}
.resume-section-title {{ margin: 0 0 6px 0; color: var(--accent); text-transform: uppercase; letter-spacing: .09em; font-size: 11px; border-bottom: 1px solid #c7ced8; padding-bottom: 3px; }}
.resume-section-title-sm {{ margin: 0 0 6px 0; color: var(--accent); text-transform: uppercase; letter-spacing: .08em; font-size: 10px; border-bottom: 1px solid #c7ced8; padding-bottom: 3px; }}
.section-title-accent {{ margin: 0 0 6px 0; color: var(--accent); text-transform: uppercase; letter-spacing: .09em; font-size: 11px; border-bottom: 2px solid var(--accent); padding-bottom: 3px; }}
.sectionTitleAccent {{ margin: 0 0 6px 0; color: var(--accent); text-transform: uppercase; letter-spacing: .09em; font-size: 11px; border-bottom: 2px solid var(--accent); padding-bottom: 3px; }}
.name-underline {{ width: 62px; height: 3px; background: var(--accent); margin: 6px auto 0; }}
.nameAccent {{ position: relative; display: inline-block; padding-bottom: 4px; }}
.nameAccent::after {{ content: ''; position: absolute; left: 0; bottom: 0; width: 100%; height: 3px; background: linear-gradient(to right, var(--accent) 0%, var(--accent) 60%, transparent 100%); }}
.resume-text {{ margin: 0; line-height: 1.45; font-size: 13px; }}
.resume-items {{ display: grid; gap: 7px; }}
.resume-row {{ display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }}
.resume-item-title {{ margin: 0; font-size: 13px; font-weight: 700; color: #111827; }}
.resume-item-subtitle {{ margin: 2px 0 4px; font-size: 11px; }}
.resume-date {{ font-size: 11px; color: #475569; white-space: nowrap; }}
.card {{ border: 1px solid #d1d5db; border-left: 3px solid var(--accent); background: #fbfcff; padding: 6px 8px; box-shadow: var(--card-shadow); margin-bottom: 8px; }}
.muted {{ color: var(--muted); }}
ul {{ margin: 0; padding-left: 16px; }}
li {{ margin-bottom: 2px; line-height: 1.4; }}
@media (max-width: 768px) {{ .resume-grid {{ grid-template-columns: 1fr; }} }}
</style>
<script id="resume-style-pack" type="application/json">[{json.dumps(active_style, ensure_ascii=False)}]</script>
<script>
window.applyResumeStyle = function(styleId) {{
  if (!styleId) return;
  document.documentElement.setAttribute('data-style-id', styleId);
}};
</script>
</head>
<body>
<main class="page">
  <header class="resume-header">
    <h1 class="resume-name {name_extra_class}">{escape_text(personal.get('name') or '')}</h1>
    {name_underline}
    <p class="resume-role">{escape_text(personal.get('title') or '')}</p>
    <p class="resume-contact">{contact_html}</p>
  </header>
  {body_content}
</main>
</body>
</html>"""


def _has_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    return value is not None


def _render_simple_section(title: str, data_section: str, body: str) -> str:
    return (
        f"<section data-section='{escape_text(data_section)}' class='resume-section'>"
        f"<h3 class='resume-section-title'>{escape_text(title)}</h3>"
        f"{body}"
        "</section>"
    )


def _render_contact_link(label: str, value: str, prefix: str = "") -> str:
    val = str(value or "").strip()
    if not val:
        return ""
    href_prefix = prefix
    if label in {"Website", "LinkedIn", "GitHub"} and not val.startswith(("http", "//")):
        href_prefix = "https://"
    href = href_prefix + val
    is_link = href_prefix.startswith(("http", "mailto:", "tel:"))
    text = val
    if is_link and label in {"Website", "LinkedIn", "GitHub"}:
        text = re.sub(r"^https?://", "", val)
        text = re.sub(r"^www\\.", "", text)
    if is_link:
        return (
            f"<a class='resume-link' href='{escape_text(href)}' target='_blank' rel='noopener noreferrer'>"
            f"{escape_text(text)}"
            "</a>"
        )
    return f"<span>{escape_text(text)}</span>"


def _render_kv_row(key: str, value: Any) -> str:
    text = display_text(value).strip()
    if not text:
        return ""
    key_label = key.replace("_", " ").replace("-", " ").title()
    return f"<div class='kv'><span class='k'>{escape_text(key_label)}:</span><span>{escape_text(text)}</span></div>"


def _render_comma_list(items: List[str], label: str) -> str:
    valid = [escape_text(x) for x in items if str(x or "").strip()]
    if not valid:
        return ""
    return f"<div class='kv'><span class='k'>{escape_text(label)}</span><span>{', '.join(valid)}</span></div>"


def _render_link_pill(value: str) -> str:
    safe = _normalize_url(value)
    if not safe:
        return ""
    display = re.sub(r"^https?://", "", value).rstrip("/")
    return f"<a class='resume-link-pill' href='{escape_text(safe)}' target='_blank' rel='noopener noreferrer'>{escape_text(display)}</a>"


def _resolve_field(item: Dict[str, Any], aliases: List[str]) -> Any:
    for alias in aliases:
        if alias in item:
            v = item[alias]
            if _has_value(v):
                return v
    return None


# ── Section Render Definitions ──────────────────────────────────────────

SECTION_RENDER_DEFS: Dict[str, Dict[str, Any]] = {
    "personalInfo": {
        "section_type": "flat_object",
        "section_label": None,
        "known_fields": {
            "name":     {"aliases": ["name", "fullName"],                        "role": "header_name"},
            "title":    {"aliases": ["title", "jobTitle"],                       "role": "header_title"},
            "email":    {"aliases": ["email", "emailAddress"],                   "role": "contact_link", "prefix": "mailto:"},
            "phone":    {"aliases": ["phone", "phoneNumber"],                    "role": "contact_link", "prefix": "tel:"},
            "location": {"aliases": ["location", "address"],                     "role": "contact_text"},
            "website":  {"aliases": ["website", "url", "web"],                   "role": "contact_link"},
            "linkedin": {"aliases": ["linkedin", "linkedIn"],                    "role": "contact_link"},
            "github":   {"aliases": ["github", "gitHub"],                        "role": "contact_link"},
        },
        "unknown_field_mode": "key_value_rows",
    },
    "summary": {
        "section_type": "text",
        "section_label": "Summary",
        "known_fields": {},
        "unknown_field_mode": "ignore",
    },
    "workExperience": {
        "section_type": "array_of_objects",
        "section_label": "Work Experience",
        "known_fields": {
            "title":       {"aliases": ["title", "position", "role"],                       "role": "card_title"},
            "company":     {"aliases": ["company", "organization", "employer"],             "role": "card_subtitle"},
            "location":    {"aliases": ["location", "office"],                               "role": "card_subtitle"},
            "years":       {"aliases": ["years", "date", "period", "duration", "startDate", "endDate"], "role": "card_date"},
            "description": {"aliases": ["description", "details", "summary", "responsibilities", "achievements"], "role": "card_bullets"},
        },
        "unknown_field_mode": "key_value_rows",
    },
    "education": {
        "section_type": "array_of_objects",
        "section_label": "Education",
        "known_fields": {
            "institution": {"aliases": ["institution", "school", "university"],            "role": "card_title"},
            "degree":      {"aliases": ["degree", "field", "major"],                        "role": "card_subtitle"},
            "years":       {"aliases": ["years", "date", "period", "graduation", "startDate", "endDate"], "role": "card_date"},
            "description": {"aliases": ["description", "details", "summary", "achievements", "courses", "gpa"], "role": "card_text"},
        },
        "unknown_field_mode": "key_value_rows",
    },
    "personalProjects": {
        "section_type": "array_of_objects",
        "section_label": "Projects",
        "known_fields": {
            "name":        {"aliases": ["name", "title", "projectName"],                   "role": "card_title"},
            "role":        {"aliases": ["role", "position"],                                "role": "card_subtitle"},
            "years":       {"aliases": ["years", "date", "period", "duration", "startDate", "endDate"], "role": "card_date"},
            "description": {"aliases": ["description", "projectDescription", "summary", "details", "technologies"], "role": "card_bullets"},
            "github":      {"aliases": ["github"],                                          "role": "card_link_pill"},
            "website":     {"aliases": ["website", "url", "link"],                          "role": "card_link_pill"},
        },
        "unknown_field_mode": "key_value_rows",
    },
    "research": {
        "section_type": "array_of_objects",
        "section_label": "Research",
        "known_fields": {
            "name":        {"aliases": ["name", "title", "projectName", "topic"],          "role": "card_title"},
            "role":        {"aliases": ["role", "position"],                                "role": "card_subtitle"},
            "institution": {"aliases": ["institution", "school", "university", "lab"],      "role": "card_subtitle"},
            "years":       {"aliases": ["years", "date", "period", "duration", "startDate", "endDate"], "role": "card_date"},
            "description": {"aliases": ["description", "summary", "achievements", "publications", "findings"], "role": "card_bullets"},
        },
        "unknown_field_mode": "key_value_rows",
    },
    "additional": {
        "section_type": "flat_kv",
        "section_label": "Skills & Awards",
        "known_fields": {
            "technicalSkills":        {"aliases": ["technicalSkills", "skills", "technologies"],            "role": "comma_list", "label": "Technical Skills:"},
            "languages":              {"aliases": ["languages", "language"],                                "role": "comma_list", "label": "Languages:"},
            "certificationsTraining": {"aliases": ["certificationsTraining", "certifications", "certification"], "role": "comma_list", "label": "Certifications:"},
            "awards":                 {"aliases": ["awards", "honors"],                                     "role": "comma_list", "label": "Awards:"},
        },
        "unknown_field_mode": "key_value_rows",
    },
    "customSections": {
        "section_type": "custom_sections",
        "section_label": None,
        "known_fields": {},
        "unknown_field_mode": "ignore",
    },
}

# ── Section Renderers ──────────────────────────────────────────────────


def _render_text_section(
    section_key: str,
    section_value: Any,
    defs: Dict[str, Any],
    rendered_paths: set[str],
) -> str:
    if not section_value:
        return ""
    mark_rendered_path(rendered_paths, section_key)
    body = ""
    if isinstance(section_value, list):
        valid = [escape_text(x) for x in section_value if str(x or "").strip()]
        if valid:
            body = _render_bullet_list(valid)
    elif isinstance(section_value, str) and section_value.strip():
        body = f"<p class='resume-text'>{escape_text(section_value)}</p>"
    if not body:
        return ""
    return _render_simple_section(defs["section_label"], section_key, body)


def _render_personal_info_header(
    personal: Dict[str, Any],
    rendered_paths: set[str],
    defs: Dict[str, Any],
) -> str:
    name = ""
    title = ""
    contact_parts: List[str] = []
    extra_rows: List[str] = []

    alias_to_canonical: Dict[str, str] = {}
    for cname, finfo in defs["known_fields"].items():
        for alias in finfo["aliases"]:
            alias_to_canonical[alias] = cname

    for key, raw_value in personal.items():
        value = str(raw_value or "").strip()
        if not value:
            mark_rendered_path(rendered_paths, f"personalInfo.{key}")
            continue
        canonical = alias_to_canonical.get(key, key)
        finfo = defs["known_fields"].get(canonical)
        mark_rendered_path(rendered_paths, f"personalInfo.{key}")
        if not finfo:
            extra_rows.append(_render_kv_row(key, raw_value))
            continue
        role = finfo["role"]
        if role == "header_name":
            name = escape_text(value)
        elif role == "header_title":
            title = escape_text(value)
        elif role == "contact_link":
            prefix = finfo.get("prefix", "")
            contact_parts.append(_render_contact_link(canonical, value, prefix))
        elif role == "contact_text":
            contact_parts.append(f"<span>{escape_text(value)}</span>")
        else:
            extra_rows.append(_render_kv_row(key, raw_value))

    contact_html = "<span class='sep'>,</span>".join(contact_parts)
    extra_html = "".join(extra_rows)
    return (
        "<header class='resume-header' data-section='personalInfo'>"
        f"<h1 class='resume-name'>{name}</h1>"
        f"<h2 class='resume-title'>{title}</h2>"
        f"<div class='resume-meta'>{contact_html}</div>"
        f"{extra_html}"
        "</header>"
    )


def _render_array_of_objects(
    section_key: str,
    items_raw: Any,
    defs: Dict[str, Any],
    rendered_paths: set[str],
) -> str:
    items = [x for x in to_list(items_raw) if isinstance(x, dict)]
    if not items:
        return ""

    alias_to_canonical: Dict[str, str] = {}
    for cname, finfo in defs["known_fields"].items():
        for alias in finfo["aliases"]:
            alias_to_canonical[alias] = cname

    cards: List[str] = []
    for idx, item in enumerate(items):
        base = f"{section_key}[{idx}]"
        mark_rendered_path(rendered_paths, base)
        card_title = ""
        card_subtitles: List[str] = []
        card_date = ""
        card_bullets: List[str] = []
        card_text = ""
        card_link_pills: List[str] = []
        extra_rows: List[str] = []

        consumed_keys: set[str] = set()
        for cname, finfo in defs["known_fields"].items():
            val = _resolve_field(item, finfo["aliases"])
            if val is None:
                continue
            consumed_keys.update(finfo["aliases"])
            role = finfo["role"]
            if role == "card_title":
                card_title = escape_text(val)
            elif role == "card_subtitle":
                text = escape_text(val) if isinstance(val, str) else escape_text(display_text(val))
                if text:
                    card_subtitles.append(text)
            elif role == "card_date":
                if not card_date:
                    card_date = escape_text(val)
            elif role == "card_bullets":
                if not card_bullets:
                    if isinstance(val, list):
                        card_bullets = [escape_text(x) for x in val if str(x or "").strip()]
                    elif val:
                        text = display_text(val).strip()
                        if text:
                            card_bullets = [escape_text(text)]
            elif role == "card_text":
                if not card_text:
                    card_text = escape_text(display_text(val))
            elif role == "card_link_pill":
                raw = str(val or "").strip()
                if raw:
                    card_link_pills.append(_render_link_pill(raw))

        for key, raw_value in item.items():
            if key in consumed_keys or key in ("id",):
                continue
            row = _render_kv_row(key, raw_value)
            if row:
                extra_rows.append(row)

        subtitle_html = ""
        if card_subtitles:
            sub_text = " | ".join(card_subtitles)
            subtitle_html = f"<div class='resume-item-subtitle'>{sub_text}</div>"

        bullets_html = ""
        if card_bullets:
            bullets_html = "<ul class='resume-list'>" + "".join(f"<li>{item}</li>" for item in card_bullets) + "</ul>"

        text_html = ""
        if card_text:
            text_html = f"<p class='resume-text-sm'>{card_text}</p>"

        pills_html = ""
        if card_link_pills:
            pills_html = f"<span class='resume-link-pills'>{''.join(card_link_pills)}</span>"

        extra_html = "".join(extra_rows)

        title_row = f"<div class='resume-row-tight'><h4 class='resume-item-title'>{card_title}</h4>{pills_html}<span class='resume-date'>{card_date}</span></div>"
        cards.append(
            "<article class='resume-item'>"
            f"{title_row}"
            f"{subtitle_html}"
            f"{bullets_html}"
            f"{text_html}"
            f"{extra_html}"
            "</article>"
        )

    return _render_simple_section(
        defs["section_label"],
        section_key,
        f"<div class='resume-items'>{''.join(cards)}</div>",
    )


def _render_flat_kv(
    section_key: str,
    section_value: Any,
    defs: Dict[str, Any],
    rendered_paths: set[str],
) -> str:
    data = to_dict(section_value)

    alias_to_canonical: Dict[str, str] = {}
    for cname, finfo in defs["known_fields"].items():
        for alias in finfo["aliases"]:
            alias_to_canonical[alias] = cname

    blocks: List[str] = []
    consumed_keys: set[str] = set()
    for cname, finfo in defs["known_fields"].items():
        val = _resolve_field(data, finfo["aliases"])
        if val is None:
            continue
        consumed_keys.update(finfo["aliases"])
        role = finfo["role"]
        if role == "comma_list":
            items = _ensure_list_or_empty(val)
            if items:
                for alias in finfo["aliases"]:
                    if alias in data:
                        mark_rendered_path(rendered_paths, f"{section_key}.{alias}")
                        break
                blocks.append(_render_comma_list(items, finfo.get("label", "")))
        else:
            for alias in finfo["aliases"]:
                if alias in data:
                    mark_rendered_path(rendered_paths, f"{section_key}.{alias}")
                    break
            blocks.append(_render_kv_row(cname, val))

    for key, raw_value in data.items():
        if key in consumed_keys or key in ("id",):
            continue
        mark_rendered_path(rendered_paths, f"{section_key}.{key}")
        row = _render_kv_row(key, raw_value)
        if row:
            blocks.append(row)

    if not blocks:
        return ""
    return _render_simple_section(
        defs["section_label"],
        section_key,
        f"<div class='resume-stack'>{''.join(blocks)}</div>",
    )


def _render_custom_sections(
    section_value: Any,
    rendered_paths: set[str],
) -> str:
    custom_sections = to_dict(section_value)
    results: List[str] = []
    for key, value in custom_sections.items():
        mark_rendered_path(rendered_paths, f"customSections.{key}")
        section = to_dict(value)
        section_type = str(section.get("sectionType") or "text")
        title = escape_text(str(key).replace("_", " ").title())
        body = ""
        if section_type == "itemList":
            rows = [x for x in to_list(section.get("items")) if isinstance(x, dict)]
            body = _render_item_cards(rows, title_key="title", subtitle_keys=["subtitle"], years_key="years", desc_key="description")
        elif section_type == "stringList":
            body = _render_bullet_list([str(x) for x in to_list(section.get("items"))])
        else:
            body = f"<p class='resume-text'>{escape_text(section.get('text') or '')}</p>"
        results.append(_render_simple_section(title, "customSections", body))
    return "".join(results)


def _render_unknown_section(
    section_key: str,
    section_value: Any,
    rendered_paths: set[str],
) -> str:
    title = escape_text(section_key.replace("_", " ").replace("-", " ").title())
    if isinstance(section_value, list) and all(isinstance(x, dict) for x in section_value if x is not None):
        items = [x for x in section_value if isinstance(x, dict)]
        if not items:
            return ""
        cards: List[str] = []
        for idx, item in enumerate(items):
            base = f"{section_key}[{idx}]"
            mark_rendered_path(rendered_paths, base)
            item_title = ""
            item_date = ""
            item_desc = ""
            extra_rows: List[str] = []
            keys = list(item.keys())
            for key in keys:
                raw_value = item[key]
                if not item_title and ("title" in key.lower() or "name" in key.lower()):
                    item_title = escape_text(raw_value)
                elif not item_date and ("date" in key.lower() or "year" in key.lower() or "period" in key.lower()):
                    item_date = escape_text(raw_value)
                elif not item_desc and ("description" in key.lower() or "detail" in key.lower() or "summary" in key.lower()):
                    if isinstance(raw_value, list):
                        item_desc = "<ul class='resume-list'>" + "".join(f"<li>{escape_text(x)}</li>" for x in raw_value if str(x or "").strip()) + "</ul>"
                    else:
                        text = escape_text(display_text(raw_value))
                        if text:
                            item_desc = f"<p class='resume-text-sm'>{text}</p>"
            for key in keys:
                if key in ("id",):
                    continue
                raw_value = item[key]
                if item_title and escape_text(raw_value) == item_title:
                    continue
                if item_date and escape_text(raw_value) == item_date:
                    continue
                row = _render_kv_row(key, raw_value)
                if row:
                    extra_rows.append(row)
            cards.append(
                "<article class='resume-item'>"
                f"<div class='resume-row-tight'><h4 class='resume-item-title'>{item_title}</h4><span class='resume-date'>{item_date}</span></div>"
                f"{item_desc}"
                f"{''.join(extra_rows)}"
                "</article>"
            )
        return _render_simple_section(
            title,
            section_key,
            f"<div class='resume-items'>{''.join(cards)}</div>",
        )
    elif isinstance(section_value, dict):
        blocks: List[str] = []
        section_data = to_dict(section_value)
        for key, raw_value in section_data.items():
            mark_rendered_path(rendered_paths, f"{section_key}.{key}")
            row = _render_kv_row(key, raw_value)
            if row:
                blocks.append(row)
        if not blocks:
            return ""
        return _render_simple_section(title, section_key, f"<div class='resume-stack'>{''.join(blocks)}</div>")
    elif isinstance(section_value, (str, list)):
        if isinstance(section_value, list):
            text_val = [escape_text(x) for x in section_value if str(x or "").strip()]
            body = _render_bullet_list(text_val) if text_val else ""
        else:
            body = f"<p class='resume-text'>{escape_text(section_value)}</p>" if section_value else ""
        if not body:
            return ""
        mark_rendered_path(rendered_paths, section_key)
        return _render_simple_section(title, section_key, body)
    return ""


def _render_section(
    section_key: str,
    section_value: Any,
    rendered_paths: set[str],
    defs: Dict[str, Any] | None,
) -> str:
    if defs is not None:
        stype = defs["section_type"]
        if stype == "text":
            return _render_text_section(section_key, section_value, defs, rendered_paths)
        elif stype == "flat_object":
            return _render_personal_info_header(to_dict(section_value), rendered_paths, defs)
        elif stype == "array_of_objects":
            return _render_array_of_objects(section_key, section_value, defs, rendered_paths)
        elif stype == "flat_kv":
            return _render_flat_kv(section_key, section_value, defs, rendered_paths)
        elif stype == "custom_sections":
            return _render_custom_sections(section_value, rendered_paths)
        return ""
    return _render_unknown_section(section_key, section_value, rendered_paths)


def render_single_column_template_html(
    resume_obj: Dict[str, Any],
    active_style: Dict[str, Any],
    *,
    page_count_mode: str = "single-page",
    target_pages: int = 1,
) -> str:
    palette = to_dict(active_style.get("palette"))
    typography = to_dict(active_style.get("typography"))
    effects = to_dict(active_style.get("effects"))

    rendered_paths: set[str] = set()

    personal = to_dict(resume_obj.get("personalInfo"))
    header_def = SECTION_RENDER_DEFS["personalInfo"]
    header_html = _render_personal_info_header(personal, rendered_paths, header_def)

    section_order = ["summary", "workExperience", "education", "personalProjects", "research", "additional", "customSections"]
    known_body_keys = set(section_order)

    body_parts: List[str] = []
    for key in section_order:
        if key not in resume_obj:
            continue
        defs = SECTION_RENDER_DEFS.get(key)
        html = _render_section(key, resume_obj[key], rendered_paths, defs)
        if html:
            body_parts.append(html)

    for key in resume_obj:
        if key in known_body_keys or key == "personalInfo" or key.startswith("_"):
            continue
        html = _render_section(key, resume_obj[key], rendered_paths, None)
        if html:
            body_parts.append(html)

    other_rows: List[str] = []
    for entry in flatten_text_entries(resume_obj):
        path = entry.get("path", "")
        if not path or path in rendered_paths:
            continue
        if any(path.startswith(f"{rendered}.") or path.startswith(f"{rendered}[") for rendered in rendered_paths):
            continue
        other_rows.append(
            "<div class='resume-extra-row'>"
            f"<div class='resume-extra-path'>{escape_text(path)}</div>"
            f"<p class='resume-text-sm'>{escape_text(entry.get('text', ''))}</p>"
            "</div>"
        )
    other_html = _render_simple_section(
        "Other Imported Content",
        "otherImportedContent",
        f"<div class='resume-stack'>{''.join(other_rows)}</div>",
    ) if other_rows else ""

    # ── Pagination (section-level, estimated by line count) ─────────────
    PAGE_LINES = 52

    def _text_lines(text: str, chars_per_line: int = 55) -> int:
        t = str(text or "").strip()
        return max(1, -(-len(t) // chars_per_line)) if t else 0

    def _estimate_section_lines(key: str, val) -> int:
        defs = SECTION_RENDER_DEFS.get(key)
        items = to_list(val) if isinstance(val, list) else []
        if defs and defs.get("section_type") == "array_of_objects" and items:
            n = 2  # heading
            for item in [x for x in items if isinstance(x, dict)]:
                n += 2  # title + margin
                # bullets
                for cname, finfo in defs.get("known_fields", {}).items():
                    if finfo["role"] == "card_bullets":
                        v = _resolve_field(item, finfo["aliases"])
                        n += len(v) if isinstance(v, list) else (_text_lines(str(v)) if v else 0)
                    elif finfo["role"] == "card_text":
                        v = _resolve_field(item, finfo["aliases"])
                        n += _text_lines(str(v)) if v else 0
                n += 1  # gap
            return n
        if key == "summary":
            return 2 + _text_lines(str(val or ""), 65)
        if key == "additional":
            return 2 + len(to_dict(val))
        return 5  # generic

    section_keys_in_order = [k for k in section_order if k in resume_obj]
    page_parts: list[list[str]] = [[]]
    page_line: list[int] = [6]  # header ~6 lines

    for sk in section_keys_in_order:
        est = _estimate_section_lines(sk, resume_obj[sk])
        idx = section_keys_in_order.index(sk)
        if page_line[-1] + est <= PAGE_LINES:
            page_parts[-1].append(body_parts[idx])
            page_line[-1] += est
        else:
            page_parts.append([body_parts[idx]])
            page_line.append(est)

    page_divs = []
    for i, parts in enumerate(page_parts):
        content = "\n".join(parts)
        page_divs.append(f"<div class='page' id='page-{i+1}'>{header_html if i == 0 else ''}{content}</div>")

    body_content = "\n".join(page_divs)

    return f"""<!doctype html>
<html lang="en" data-style-id="{escape_text(active_style.get('id') or 'single-column')}" data-template-id="swiss-single" data-column-mode="single" data-page-count-mode="{escape_text(page_count_mode)}" data-target-pages="{escape_text(target_pages)}">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{escape_text(personal.get('name') or 'Resume')}</title>
<style>
html {{
  --primary: {palette.get('primary', '#0b3a66')};
  --accent: {palette.get('accent', '#1f8a70')};
  --text: {palette.get('text', '#111827')};
  --muted: {palette.get('muted', '#6b7280')};
  --bg: {palette.get('bg', '#f5f7fb')};
  --paper: {palette.get('paper', '#ffffff')};
  --title-shadow: {effects.get('title_shadow', 'none')};
  --card-shadow: {effects.get('card_shadow', 'none')};
}}
body {{ margin: 0; background: var(--bg); color: var(--text); font-family: {typography.get('font_family', "'IBM Plex Sans', 'PingFang SC', sans-serif")}; }}
.page {{ width: 210mm; min-height: 297mm; margin: 0 auto 12px; background: var(--paper); border: 1px solid #111; padding: 10mm 12mm; box-sizing: border-box; position: relative; }}
@media print {{
  body {{ background: white; }}
  .page {{ margin: 0; border: none; page-break-after: always; }}
  .page:last-child {{ page-break-after: auto; }}
}}
.resume-header {{ text-align: center; border-bottom: 1px solid #111; padding-bottom: 8px; margin-bottom: 10px; }}
.resume-name {{ margin: 0; font-size: {typography.get('title_size_px', 30)}px; line-height: 1.1; letter-spacing: .02em; text-transform: uppercase; color: var(--primary); text-shadow: var(--title-shadow); }}
.resume-title {{ margin: 4px 0 10px; text-transform: uppercase; letter-spacing: .08em; font-size: 12px; color: #1f2937; }}
.resume-meta {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 4px; font-size: 11px; color: #374151; }}
.resume-meta .sep {{ color: var(--muted); margin: 0 4px; }}
.resume-section {{ margin-top: 10px; }}
.resume-section-title {{ margin: 0 0 6px; color: var(--accent); border-bottom: 1px solid #d1d5db; font-size: 11px; text-transform: uppercase; letter-spacing: .08em; padding-bottom: 3px; }}
.resume-items {{ display: grid; gap: 8px; }}
.resume-item {{ margin: 0; }}
.resume-row-tight {{ display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }}
.resume-item-title {{ margin: 0; font-size: 13px; font-weight: 700; }}
.resume-date {{ font-size: 11px; color: #4b5563; white-space: nowrap; }}
.resume-item-subtitle {{ margin: 2px 0 4px; display: flex; justify-content: space-between; font-size: 11px; color: #4b5563; }}
.resume-text {{ margin: 0; line-height: 1.45; font-size: 13px; }}
.resume-text-sm {{ margin: 0; line-height: 1.4; font-size: 12px; }}
.resume-list {{ margin: 0; padding-left: 18px; line-height: 1.45; font-size: 12px; }}
.resume-list li {{ margin: 2px 0; }}
.resume-link {{ color: var(--primary); text-decoration: none; }}
.resume-link:hover {{ text-decoration: underline; }}
.resume-link-pills {{ display: inline-flex; gap: 6px; margin-left: 8px; }}
.resume-link-pill {{ font-size: 10px; border: 1px solid #cbd5e1; border-radius: 999px; padding: 1px 6px; text-decoration: none; color: var(--primary); }}
.resume-stack {{ display: grid; gap: 4px; font-size: 12px; }}
.kv {{ display: flex; gap: 8px; }}
.kv .k {{ width: 124px; font-weight: 700; flex-shrink: 0; }}
.resume-project-title {{ display: flex; align-items: baseline; gap: 6px; min-width: 0; }}
</style>
<script id="resume-style-pack" type="application/json">[{json.dumps(active_style, ensure_ascii=False)}]</script>
<script>
window.applyResumeStyle = function(styleId) {{
  if (!styleId) return;
  document.documentElement.setAttribute('data-style-id', styleId);
}};
</script>
</head>
<body>
{body_content}
{other_html}
</body>
</html>"""


# ── LaTeX Template ────────────────────────────────────────────────────────


def _latex_escape(text: str) -> str:
    return str(text or "").replace("\\", "\\textbackslash ").replace("&", "\\&").replace("%", "\\%").replace("$", "\\$").replace("#", "\\#").replace("_", "\\_").replace("{", "\\{").replace("}", "\\}").replace("~", "\\textasciitilde{}").replace("^", "\\textasciicircum{}")


def render_latex_template(resume_obj: Dict[str, Any], active_style: Dict[str, Any] | None = None) -> str:
    palette = to_dict((active_style or {}).get("palette", {}))
    primary = palette.get("primary", "#0b3a66")

    personal = to_dict(resume_obj.get("personalInfo", {}))
    name = _latex_escape(str(personal.get("name", "Resume")))
    title = _latex_escape(str(personal.get("title", "")))
    email = _latex_escape(str(personal.get("email", "")))
    phone = _latex_escape(str(personal.get("phone", "")))
    location = _latex_escape(str(personal.get("location", "")))
    linkedin = _latex_escape(str(personal.get("linkedin", "")))
    github = _latex_escape(str(personal.get("github", "")))
    website = _latex_escape(str(personal.get("website", "")))

    # Contact line
    contacts = [x for x in [email, phone, location] if x]
    contact_line = " \\textbar{} ".join(contacts)
    links = [x for x in [website, linkedin, github] if x]
    if links:
        contact_line += " \\\\ " + " \\textbar{} ".join(links)

    # ── Sections ──
    def _render_latex_entries(items: list, fields: dict, section_label: str) -> str:
        """Render array-of-objects as LaTeX entries with inline bullets."""
        if not items:
            return ""
        entries = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title_val = ""
            subtitle_parts = []
            date_val = ""
            bullets = []
            text_val = ""

            for cname, finfo in fields.items():
                val = _resolve_field(item, finfo["aliases"])
                if val is None:
                    continue
                role = finfo["role"]
                if role == "card_title":
                    title_val = _latex_escape(str(val))
                elif role == "card_subtitle":
                    subtitle_parts.append(_latex_escape(str(val)))
                elif role == "card_date":
                    date_val = _latex_escape(str(val))
                elif role == "card_bullets":
                    if isinstance(val, list):
                        bullets = [_latex_escape(str(x)) for x in val if str(x or "").strip()]
                    elif val:
                        bullets = [_latex_escape(str(val))]
                elif role == "card_text":
                    text_val = _latex_escape(str(val))

            # Build entry: title on first line, date | subtitle on second line
            lines = []
            lines.append(f"  \\item \\textbf{{{title_val}}}")

            sub_parts = []
            if date_val:
                sub_parts.append(f"\\textit{{{date_val}}}")
            sub_parts.extend(subtitle_parts)
            sub = " \\textbar{} ".join(sub_parts)
            if sub:
                lines.append(f"  {sub} \\\\")

            if bullets:
                lines.append("  \\begin{itemize}[leftmargin=12pt, label=$\\bullet$, itemsep=1pt, topsep=2pt]")
                for b in bullets:
                    lines.append(f"    \\item {b}")
                lines.append("  \\end{itemize}")
            elif text_val:
                lines.append(f"  {text_val} \\\\")

            entries.append("\n".join(lines))

        header = f"\\section{{{_latex_escape(section_label)}}}"
        return header + "\n\\begin{itemize}[leftmargin=0pt, label={}]\n" + "\n".join(entries) + "\n\\end{itemize}"

    # Work Experience
    work_items = [x for x in to_list(resume_obj.get("workExperience", [])) if isinstance(x, dict)]
    work_defs = SECTION_RENDER_DEFS.get("workExperience", {}).get("known_fields", {})
    work_latex = _render_latex_entries(work_items, work_defs, "Work Experience") if work_items and work_defs else ""

    # Education
    edu_items = [x for x in to_list(resume_obj.get("education", [])) if isinstance(x, dict)]
    edu_defs = SECTION_RENDER_DEFS.get("education", {}).get("known_fields", {})
    edu_latex = _render_latex_entries(edu_items, edu_defs, "Education") if edu_items and edu_defs else ""

    # Projects
    proj_items = [x for x in to_list(resume_obj.get("personalProjects", [])) if isinstance(x, dict)]
    proj_defs = SECTION_RENDER_DEFS.get("personalProjects", {}).get("known_fields", {})
    proj_latex = _render_latex_entries(proj_items, proj_defs, "Projects") if proj_items and proj_defs else ""

    # Research
    research_items = [x for x in to_list(resume_obj.get("research", [])) if isinstance(x, dict)]
    research_defs = SECTION_RENDER_DEFS.get("research", {}).get("known_fields", {})
    research_latex = _render_latex_entries(research_items, research_defs, "Research") if research_items and research_defs else ""

    # Summary
    summary_text = _latex_escape(str(resume_obj.get("summary", "")))
    summary_latex = f"\\section{{Summary}}\n  {summary_text}" if summary_text.strip() else ""

    # Additional (skills, languages, etc.)
    additional = to_dict(resume_obj.get("additional", {}))
    skills_latex = ""
    skills = to_list(additional.get("technicalSkills", []))
    if skills:
        skills_str = " \\textbar{} ".join(_latex_escape(str(s)) for s in skills if str(s).strip())
        skills_latex = f"\\section{{Skills}}\n  {skills_str}"

    langs = to_list(additional.get("languages", []))
    langs_latex = ""
    if langs:
        langs_str = " \\textbar{} ".join(_latex_escape(str(l)) for l in langs if str(l).strip())
        langs_latex = f"\\section{{Languages}}\n  {langs_str}"

    # ── Assemble document ──
    body = "\n\n".join(x for x in [
        summary_latex,
        work_latex,
        edu_latex,
        proj_latex,
        research_latex,
        skills_latex,
        langs_latex,
    ] if x)

    return f"""% !TEX program = xelatex
% ⚠️  This file requires XeLaTeX (LuaLaTeX does not support xeCJK).
%     Overleaf: Menu → Compiler → XeLaTeX
%     Local:    xelatex main.tex
\\documentclass[11pt,a4paper]{{article}}
\\usepackage{{fontspec}}
\\usepackage{{xeCJK}}
\\setmainfont{{Latin Modern Roman}}
\\setCJKmainfont{{Noto Serif CJK SC}}[AutoFakeBold=2.5]
\\usepackage{{geometry}}
\\geometry{{left=18mm, right=18mm, top=18mm, bottom=18mm}}
\\usepackage{{enumitem}}
\\usepackage{{hyperref}}
\\usepackage{{xcolor}}
\\usepackage{{titlesec}}

% ── Colors ──
\\definecolor{{primary}}{{HTML}}{{{primary.replace('#', '')}}}

% ── Section formatting ──
\\titleformat{{\\section}}{{\\Large\\bfseries\\color{{primary}}}}{{}}{{0em}}{{}}[\\titlerule]
\\titlespacing*{{\\section}}{{0pt}}{{10pt}}{{4pt}}

% ── Compact lists ──
\\setlist{{itemsep=0pt, parsep=0pt, topsep=3pt, partopsep=0pt}}

\\begin{{document}}

% ── Header ──
\\begin{{center}}
  {{\\Huge\\bfseries {name}}}\\\\[4pt]
  {{\\large {title}}}\\\\[2pt]
  {{\\small {contact_line}}}
\\end{{center}}
\\vspace{{-6pt}}

{body}

\\end{{document}}
"""
