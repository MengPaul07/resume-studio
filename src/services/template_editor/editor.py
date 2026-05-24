"""Template HTML CRUD: add/remove Jinja2 field placeholders with section anchors."""

import html
import re
from pathlib import Path
from typing import Any, Dict, List

from .inspector import _read_template_html
from .types import EditResult

TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates"

# Jinja2 expression templates by render_hint
EXPR_TEMPLATES: Dict[str, str] = {
    "text": '<p class="resume-field">{{ {field_path} }}</p>',
    "link": '<a class="resume-link" href="{{ {field_path} }}">{{ {field_path} }}</a>',
    "date": '<span class="resume-date">{{ {field_path} }}</span>',
    "list": (
        '{% if {field_path} %}<ul>'
        '{% for item in {field_path} %}<li>{{ item }}</li>{% endfor %}'
        '</ul>{% endif %}'
    ),
    "conditional_text": '{% if {field_path} %}<p>{{ {field_path} }}</p>{% endif %}',
}


def edit_template_slot(
    template_id: str,
    section: str,
    operation: str,  # "add_field" | "remove_field" | "add_section" | "remove_section"
    field_path: str = "",
    jinja2_expr: str | None = None,
    render_hint: str = "text",
    section_config: Dict[str, Any] | None = None,
) -> EditResult:
    """
    Modify a template HTML file by adding or removing Jinja2 placeholder slots.

    Uses data-section anchors to locate the correct insertion point.
    """
    html_text = _read_template_html(template_id)

    if operation == "add_field":
        return _add_field(html_text, template_id, section, field_path, jinja2_expr, render_hint)
    elif operation == "remove_field":
        return _remove_field(html_text, template_id, section, field_path)
    elif operation == "add_section":
        return _add_section(html_text, template_id, section, section_config or {})
    elif operation == "remove_section":
        return _remove_section(html_text, template_id, section)
    else:
        return EditResult(success=False, operation=operation, message=f"Unknown operation: {operation}")


def _add_field(
    html_text: str,
    template_id: str,
    section: str,
    field_path: str,
    jinja2_expr: str | None,
    render_hint: str,
) -> EditResult:
    # Locate the section anchor
    section_pattern = re.compile(
        rf'(<[^>]*data-section="{re.escape(section)}"[^>]*>.*?)(</(?:section|header|article)>)',
        re.DOTALL,
    )
    match = section_pattern.search(html_text)
    if not match:
        return EditResult(
            success=False,
            operation="add_field",
            message=f"Section '{section}' not found in template '{template_id}'",
            affected_path=field_path,
        )

    if jinja2_expr is None:
        jinja2_expr = EXPR_TEMPLATES.get(
            render_hint, EXPR_TEMPLATES["conditional_text"]
        ).format(field_path=field_path)

    # Insert the new expression before the closing tag
    section_content = match.group(1)
    section_close = match.group(2)

    # For static sections, add to the end of the section content
    # For loop sections, add inside each loop item
    if re.search(r'\{%\s*for\s+\w+\s+in\s+' + section, html_text):
        # Loop section: find the loop body and add field inside
        loop_body_pattern = re.compile(
            rf'(\{{%\s*for\s+\w+\s+in\s+{re.escape(section)}\s*%\}}.*?)(\{{%\s*endfor\s*%\}})',
            re.DOTALL,
        )
        loop_match = loop_body_pattern.search(html_text)
        if loop_match:
            insert_pos = loop_match.start(2)
            new_html = html_text[:insert_pos] + f"\n        {jinja2_expr}\n      " + html_text[insert_pos:]
            _save_template(template_id, new_html)
            return EditResult(
                success=True,
                operation="add_field",
                message=f"Added field '{field_path}' to loop section '{section}'",
                affected_path=field_path,
                preview_html=f"<!-- preview: {jinja2_expr} -->",
            )
    else:
        # Static section: insert before closing tag
        insert_pos = match.start(2)
        new_html = html_text[:insert_pos] + f"\n      {jinja2_expr}\n    " + html_text[insert_pos:]
        _save_template(template_id, new_html)
        return EditResult(
            success=True,
            operation="add_field",
            message=f"Added field '{field_path}' to section '{section}'",
            affected_path=field_path,
            preview_html=f"<!-- preview: {jinja2_expr} -->",
        )

    return EditResult(
        success=False,
        operation="add_field",
        message=f"Could not find insertion point in section '{section}'",
        affected_path=field_path,
    )


def _remove_field(
    html_text: str,
    template_id: str,
    section: str,
    field_path: str,
) -> EditResult:
    # Find and remove the Jinja2 expression for this field
    escaped_path = re.escape(field_path)
    pattern = re.compile(
        rf'[ \t]*\{{%.*?{escaped_path}.*?%\}}[ \t]*\n?|'
        rf'[ \t]*\{{\{{\s*{escaped_path}\s*[^}}]*\}}\}}[ \t]*\n?',
        re.DOTALL,
    )

    count = 0
    new_html = pattern.sub("", html_text, count=1)
    if new_html == html_text:
        return EditResult(
            success=False,
            operation="remove_field",
            message=f"Field '{field_path}' not found in section '{section}'",
            affected_path=field_path,
        )

    _save_template(template_id, new_html)
    return EditResult(
        success=True,
        operation="remove_field",
        message=f"Removed field '{field_path}' from section '{section}'",
        affected_path=field_path,
    )


def _add_section(
    html_text: str,
    template_id: str,
    section: str,
    section_config: Dict[str, Any],
) -> EditResult:
    section_title = section_config.get("title", section.replace("_", " ").title())
    section_type = section_config.get("type", "static")

    if section_type == "loop":
        item_fields = section_config.get("item_fields", ["title", "description"])
        field_lines = "\n".join(
            f"          <p>{{{{ item.{f} }}}}</p>" for f in item_fields
        )
        new_section = f"""
    {{% if {section} %}}
    <section data-section="{html.escape(section)}">
      <h3>{html.escape(section_title)}</h3>
      {{% for item in {section} %}}
      <article>
{field_lines}
      </article>
      {{% endfor %}}
    </section>
    {{% endif %}}"""
    else:
        fields = section_config.get("fields", [])
        field_lines = "\n".join(
            f"      <p>{{{{ {section}.{f} }}}}</p>" for f in fields
        ) if fields else f"      <p>{{{{ {section} }}}}</p>"
        new_section = f"""
    {{% if {section} %}}
    <section data-section="{html.escape(section)}">
      <h3>{html.escape(section_title)}</h3>
{field_lines}
    </section>
    {{% endif %}}"""

    # Insert before </main> or </body>
    main_close = re.search(r"</main>", html_text)
    if main_close:
        new_html = html_text[:main_close.start()] + new_section + "\n  " + html_text[main_close.start():]
        _save_template(template_id, new_html)
        return EditResult(
            success=True,
            operation="add_section",
            message=f"Added section '{section}' to template '{template_id}'",
            affected_path=section,
        )

    return EditResult(
        success=False,
        operation="add_section",
        message=f"Could not find insertion point in template '{template_id}'",
        affected_path=section,
    )


def _remove_section(
    html_text: str,
    template_id: str,
    section: str,
) -> EditResult:
    pattern = re.compile(
        rf'[ \t]*\{{%.*?{re.escape(section)}.*?%\}}.*?'
        rf'<section[^>]*data-section="{re.escape(section)}"[^>]*>.*?</section>'
        r'[ \t]*\{{%.*?end(for|if).*?%\}}[ \t]*\n?',
        re.DOTALL,
    )
    new_html = pattern.sub("", html_text, count=1)
    if new_html == html_text:
        return EditResult(
            success=False,
            operation="remove_section",
            message=f"Section '{section}' not found in template '{template_id}'",
            affected_path=section,
        )

    _save_template(template_id, new_html)
    return EditResult(
        success=True,
        operation="remove_section",
        message=f"Removed section '{section}' from template '{template_id}'",
        affected_path=section,
    )


def _save_template(template_id: str, html_text: str) -> None:
    from .inspector import _load_template_ids

    manifest = _load_template_ids()
    for entry in manifest:
        if entry.get("id") == template_id:
            file_path = TEMPLATES_DIR / entry["file"]
            file_path.write_text(html_text, encoding="utf-8")
            return
    raise FileNotFoundError(f"Template not found for save: {template_id}")
