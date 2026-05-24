"""Single-section preview rendering for alignment verification."""

import html
from typing import Any, Dict, List

from .inspector import inspect_template
from .types import TemplateSection


def preview_section(
    template_id: str,
    section: str,
    resume_obj: Dict[str, Any],
) -> str:
    """Render a single template section against the resume JSON as an HTML fragment."""
    template = inspect_template(template_id)
    ts: TemplateSection | None = next(
        (s for s in template.sections if s.name == section), None
    )

    if ts is None:
        return f"<!-- Section '{section}' not found in template '{template_id}' -->"

    section_data = resume_obj.get(section, {})
    if section_data is None:
        section_data = {}

    if ts.section_type == "loop":
        return _preview_loop_section(section, ts, section_data)
    else:
        return _preview_static_section(section, ts, section_data)


def _preview_static_section(
    section: str, ts: TemplateSection, data: Any
) -> str:
    parts: List[str] = []
    parts.append(f'<section data-section="{html.escape(section)}" class="preview-section">')
    parts.append(f'<h3 class="preview-section-title">{html.escape(section)}</h3>')

    if isinstance(data, dict):
        for field in ts.fields:
            leaf = field.path.split(".")[-1]
            value = data.get(leaf, "")
            rendered = _render_field_value(leaf, value)
            parts.append(
                f'<div class="preview-field" data-field="{html.escape(leaf)}">'
                f'<span class="field-label">{html.escape(leaf)}</span>: {rendered}'
                f'</div>'
            )

        # Show extra fields NOT in template
        template_field_names = {f.path.split(".")[-1] for f in ts.fields}
        for key, value in data.items():
            if key not in template_field_names:
                rendered = _render_field_value(key, value)
                parts.append(
                    f'<div class="preview-field unmatched" data-field="{html.escape(key)}" '
                    f'title="Field not in template">'
                    f'<span class="field-label">&#x26A0; {html.escape(key)}</span>: {rendered}'
                    f'</div>'
                )
    elif isinstance(data, str):
        parts.append(f"<p>{html.escape(data)}</p>")

    parts.append("</section>")
    return "\n".join(parts)


def _preview_loop_section(
    section: str, ts: TemplateSection, data: Any
) -> str:
    parts: List[str] = []
    parts.append(f'<section data-section="{html.escape(section)}" class="preview-section">')
    parts.append(f'<h3 class="preview-section-title">{html.escape(section)}</h3>')

    if not isinstance(data, list):
        parts.append(f"<p class='preview-empty'>No items</p>")
        parts.append("</section>")
        return "\n".join(parts)

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        parts.append(f'<div class="preview-item" data-index="{idx}">')
        for field_name in ts.item_fields:
            value = item.get(field_name, "")
            rendered = _render_field_value(field_name, value)
            parts.append(
                f'<div class="preview-field" data-field="{html.escape(field_name)}">'
                f'<span class="field-label">{html.escape(field_name)}</span>: {rendered}'
                f'</div>'
            )

        # Show extra fields
        for key, value in item.items():
            if key not in ts.item_fields:
                rendered = _render_field_value(key, value)
                parts.append(
                    f'<div class="preview-field unmatched" data-field="{html.escape(key)}" '
                    f'title="Field not in template">'
                    f'<span class="field-label">&#x26A0; {html.escape(key)}</span>: {rendered}'
                    f'</div>'
                )
        parts.append("</div>")

    parts.append("</section>")
    return "\n".join(parts)


def _render_field_value(name: str, value: Any) -> str:
    if value is None:
        return '<span class="preview-null">(empty)</span>'
    if isinstance(value, list):
        items = "".join(f"<li>{html.escape(str(v))}</li>" for v in value[:10])
        more = f"<li class='preview-more'>... +{len(value) - 10} more</li>" if len(value) > 10 else ""
        return f"<ul>{items}{more}</ul>"
    if isinstance(value, dict):
        return f"<pre>{html.escape(str(value))}</pre>"
    return f"<span>{html.escape(str(value))}</span>"
