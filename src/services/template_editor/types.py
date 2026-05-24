from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal


@dataclass
class FieldSlot:
    path: str
    jinja2_expr: str
    render_hint: str  # "text" | "list" | "link" | "date" | "card"


@dataclass
class TemplateSection:
    name: str
    section_type: Literal["static", "loop", "conditional"]
    fields: List[FieldSlot] = field(default_factory=list)
    item_fields: List[str] = field(default_factory=list)
    html_anchor: str = ""


@dataclass
class TemplateStructure:
    template_id: str
    sections: List[TemplateSection] = field(default_factory=list)


@dataclass
class JsonField:
    path: str
    json_type: str
    sample: Any = None
    parent_section: str = ""


@dataclass
class JsonStructure:
    session_id: str
    fields: List[JsonField] = field(default_factory=list)


@dataclass
class MismatchItem:
    kind: Literal["missing_in_template", "missing_in_json", "type_conflict", "name_mismatch"]
    json_path: str = ""
    template_path: str = ""
    json_type: str = ""
    template_type: str = ""
    severity: Literal["error", "warn", "info"] = "warn"
    suggested_fix: str = ""
    auto_fixable: bool = False


@dataclass
class MismatchReport:
    template_id: str
    session_id: str
    mismatches: List[MismatchItem] = field(default_factory=list)


@dataclass
class EditResult:
    success: bool
    operation: str
    message: str
    affected_path: str = ""
    preview_html: str = ""
