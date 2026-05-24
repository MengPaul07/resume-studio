"""Inspect template HTML structure and resume JSON structure, detect mismatches."""

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Set

from .field_mappings import FIELD_ALIASES, SIMPLE_RENDER_FIELDS, STANDARD_SECTIONS, lookup_alias
from .types import (
    EditResult,
    FieldSlot,
    JsonField,
    JsonStructure,
    MismatchItem,
    MismatchReport,
    TemplateSection,
    TemplateStructure,
)

TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates"
MANIFEST_PATH = TEMPLATES_DIR / "template-manifest.json"


def _load_template_ids() -> List[Dict[str, str]]:
    if not MANIFEST_PATH.exists():
        return [{"id": "swiss-single", "file": "resume-single-column.template.html"}]
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_template_html(template_id: str) -> str:
    manifest = _load_template_ids()
    for entry in manifest:
        if entry.get("id") == template_id:
            file_path = TEMPLATES_DIR / entry["file"]
            if file_path.exists():
                return file_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Template not found: {template_id}")


def inspect_template(template_id: str) -> TemplateStructure:
    """Parse a template HTML file and extract all sections and field slots."""
    html = _read_template_html(template_id)
    sections: List[TemplateSection] = []

    section_pattern = re.compile(
        r'<(\w+)[^>]*data-section="([^"]+)"[^>]*>(.*?)</\1>',
        re.DOTALL,
    )

    for match in section_pattern.finditer(html):
        tag_name = match.group(1)
        section_name = match.group(2)
        section_html = match.group(3)

        if section_name in {"personalInfo"} and "resume-header" in html:
            anchor_start = html.find(f'data-section="{section_name}"')
            anchor = html[max(0, anchor_start - 50):anchor_start + 80].strip()
        else:
            anchor = match.group(0)[:120].strip()

        var_pattern = re.compile(r'\{\{\s*(\w+(?:\.\w+)*)\s*(?:\|\s*\w+(?:\([^)]*\))?)*\s*\}\}')
        field_names: Set[str] = set()
        for var_match in var_pattern.finditer(section_html):
            field_names.add(var_match.group(1))

        # Jinja2 for-loop: {% for item in sectionName %}
        is_loop = bool(re.search(r'\{%\s*for\s+\w+\s+in\s+' + section_name, html))

        item_fields: List[str] = []
        if is_loop:
            item_var_pattern = re.compile(r'\{\{\s*(\w+)\.(\w+)\s*[^}]*\}\}')
            item_field_set: Set[str] = set()
            for m in item_var_pattern.finditer(section_html):
                item_field_set.add(m.group(2))
            item_fields = sorted(item_field_set)

        is_conditional = bool(re.search(r'\{%\s*if\s+' + section_name, html))

        field_slots = [
            FieldSlot(path=f, jinja2_expr=f"{{{{ {f} }}}}", render_hint="text")
            for f in sorted(field_names)
        ]

        section_type = "loop" if is_loop else "conditional" if is_conditional else "static"
        sections.append(
            TemplateSection(
                name=section_name,
                section_type=section_type,
                fields=field_slots,
                item_fields=item_fields,
                html_anchor=anchor,
            )
        )

    return TemplateStructure(template_id=template_id, sections=sections)


def inspect_resume_json(session_id: str, resume_obj: Dict[str, Any]) -> JsonStructure:
    """Extract all fields from the resume JSON with their types and sample values."""
    fields: List[JsonField] = []

    def _walk(obj: Any, prefix: str) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{prefix}.{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    _walk(value, current_path)
                else:
                    parent = prefix.split(".")[0] if prefix else key
                    # Extract item fields from list sections
                    fields.append(
                        JsonField(
                            path=current_path,
                            json_type=type(value).__name__,
                            sample=_safe_sample(value),
                            parent_section=parent,
                        )
                    )
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                if isinstance(item, dict):
                    _walk(item, f"{prefix}[{idx}]")
                    break  # Only sample first item

    _walk(resume_obj, "")
    return JsonStructure(session_id=session_id, fields=fields)


def _safe_sample(value: Any) -> Any:
    if isinstance(value, str) and len(value) > 80:
        return value[:77] + "..."
    return value


def detect_mismatches(
    template_id: str, resume_obj: Dict[str, Any], session_id: str = ""
) -> MismatchReport:
    """Compare template expectations against actual JSON fields."""
    template = inspect_template(template_id)
    json_structure = inspect_resume_json(session_id, resume_obj)

    mismatches: List[MismatchItem] = []

    # Build sets for comparison
    template_sections = {s.name for s in template.sections}
    json_sections: Set[str] = set()
    for f in json_structure.fields:
        section = f.path.split(".")[0]
        section = re.sub(r'\[\d+\]', '', section)  # strip array indices
        if section:
            json_sections.add(section)

    # Check sections present in JSON but missing in template
    for section in json_sections:
        if section not in template_sections and section not in ("customSections",):
            mismatches.append(
                MismatchItem(
                    kind="missing_in_template",
                    json_path=f"{section}.*",
                    severity="warn",
                    suggested_fix=f"Add a template section for '{section}' or move fields to customSections",
                    auto_fixable=False,
                )
            )

    # Check individual fields
    for jf in json_structure.fields:
        section = jf.path.split(".")[0]
        section = re.sub(r'\[\d+\]', '', section)  # strip array indices
        if section in ("customSections",):
            continue

        ts = next((s for s in template.sections if s.name == section), None)

        if ts is None:
            continue

        # Extract the leaf field name and path within section
        # Normalize: strip array indices from path for comparison
        clean_path = re.sub(r'\[\d+\]\.', '.', jf.path)
        clean_path = re.sub(r'\[\d+\]', '', clean_path)
        field_tail = clean_path[len(section) + 1:] if clean_path.startswith(section + ".") else clean_path

        if not field_tail or field_tail == section:
            continue
        if field_tail in ("id",):
            continue  # skip metadata fields

        # Check alias (use clean_path without array indices)
        alias = lookup_alias(clean_path)
        if alias:
            mismatches.append(
                MismatchItem(
                    kind="name_mismatch",
                    json_path=jf.path,
                    template_path=f"{section}.{alias['target'].split('.')[-1]}",
                    json_type=jf.json_type,
                    suggested_fix=f"Remap {jf.path} -> {alias['target']} (transform={alias['transform']})",
                    auto_fixable=True,
                )
            )
            continue

        # Check if field exists in template (all section types)
        # Normalize template field paths to leaf names for comparison
        template_leaf_names = {f.path.split(".")[-1] for f in ts.fields} | set(ts.item_fields)
        if field_tail and field_tail not in template_leaf_names:
            mismatches.append(
                MismatchItem(
                    kind="missing_in_template",
                    json_path=jf.path,
                    severity="warn",
                    suggested_fix=f"Add field '{field_tail}' to template section '{section}'",
                    auto_fixable=True,
                )
            )

    return MismatchReport(
        template_id=template_id,
        session_id=session_id,
        mismatches=mismatches,
    )


def _has_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    return value is not None


def auto_remap_json(resume_obj: Dict[str, Any]) -> Dict[str, Any]:
    """Apply known field aliases automatically (LLM-free). Returns patched copy."""
    patched = deepcopy(resume_obj)

    # Resolve alias chains in object
    for alias_path, mapping in FIELD_ALIASES.items():
        parts = alias_path.split(".")
        if len(parts) < 2:
            continue
        target_parts = mapping["target"].split(".")
        transform = mapping.get("transform", "direct")
        source_key = parts[-1]
        target_key = target_parts[-1]

        # Determine if the parent section is an array (loop section)
        section_name = parts[0]
        if section_name in patched and isinstance(patched[section_name], list):
            # Apply to each item in the array
            for item in patched[section_name]:
                if not isinstance(item, dict):
                    continue
                if source_key not in item:
                    continue
                if target_key in item and _has_value(item[target_key]):
                    continue  # preserve existing target value
                value = item[source_key]
                value = _apply_transform(value, transform)
                item[target_key] = value
                del item[source_key]
        else:
            # Static section
            container = patched
            for part in parts[:-1]:
                if isinstance(container, dict) and part in container:
                    container = container[part]
                else:
                    container = None
                    break
            if container is None or not isinstance(container, dict):
                continue
            if source_key not in container:
                continue

            target_container = patched
            for part in target_parts[:-1]:
                if isinstance(target_container, dict):
                    target_container = target_container.setdefault(part, {})
                else:
                    break
            if not isinstance(target_container, dict):
                continue

            value = container[source_key]
            value = _apply_transform(value, transform)
            if target_key in target_container and _has_value(target_container[target_key]):
                continue  # preserve existing target value
            target_container[target_key] = value
            if container is target_container and source_key != target_key:
                del container[source_key]
            elif source_key in container:
                del container[source_key]

    return patched


def _apply_transform(value: Any, transform: str) -> Any:
    if transform == "split_to_list" and isinstance(value, str):
        return [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]
    elif transform == "join_list" and isinstance(value, list):
        return "\n".join(str(v) for v in value)
    elif transform == "wrap_text" and isinstance(value, str):
        return [value]
    return value


def align_for_render(
    template_id: str, resume_obj: Dict[str, Any], session_id: str = ""
) -> Dict[str, Any]:
    """Full pre-render alignment: remap + auto-add template slots for unmatched fields.

    Returns {resume_obj, alignment_report} where resume_obj is patched and
    template has been updated with any missing field placeholders.
    """
    from .editor import edit_template_slot

    report = detect_mismatches(template_id, resume_obj, session_id)
    patched = auto_remap_json(resume_obj)
    auto_added: List[Dict[str, str]] = []

    for m in report.mismatches:
        if m.kind != "missing_in_template":
            continue
        section = m.json_path.split(".")[0]
        section = re.sub(r'\[\d+\]', '', section)
        field_tail = re.sub(r'\[\d+\]\.', '.', m.json_path)
        field_tail = re.sub(r'\[\d+\]', '', field_tail)
        field_tail = field_tail[len(section) + 1:] if field_tail.startswith(section + ".") else field_tail
        if not field_tail:
            continue

        result = edit_template_slot(
            template_id=template_id,
            section=section,
            operation="add_field",
            field_path=f"{section}.{field_tail}",
            render_hint=m.json_type if m.json_type in ("str", "list") else "text",
        )
        if result.success:
            auto_added.append({"section": section, "field": field_tail, "json_path": m.json_path})

    return {
        "resume_obj": patched,
        "alignment_report": {
            "auto_remapped": len([m for m in report.mismatches if m.auto_fixable and m.kind == "name_mismatch"]),
            "auto_added_to_template": auto_added,
            "remaining_issues": len([
                m for m in report.mismatches
                if not m.auto_fixable and m.kind not in ("missing_in_template",)
            ]),
        },
    }
