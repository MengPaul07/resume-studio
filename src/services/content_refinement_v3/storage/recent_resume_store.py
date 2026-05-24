import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

try:
    from src.services.layout_design.service import run_layout_design
except Exception:
    run_layout_design = None  # type: ignore


_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "recent_resumes"
_INDEX_PATH = _DATA_DIR / "recent_resumes_index.json"


def _ensure_store() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _INDEX_PATH.exists():
        _INDEX_PATH.write_text("[]", encoding="utf-8")


def _read_index() -> List[Dict[str, Any]]:
    _ensure_store()
    try:
        data = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = []
    return data if isinstance(data, list) else []


def _write_index(items: List[Dict[str, Any]]) -> None:
    _ensure_store()
    _INDEX_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _to_rel_repo_path(path: Path) -> str:
    return str(path.relative_to(_repo_root()))


def _read_text_if_exists(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception:
        return ""


def _read_json_if_exists(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _resolve_artifact_paths(record_id: str) -> Dict[str, Path]:
    return {
        "resume_obj": _DATA_DIR / f"{record_id}.resume.json",
        "markdown": _DATA_DIR / f"{record_id}.md",
        "html": _DATA_DIR / f"{record_id}.html",
    }


def _fallback_markdown_from_resume_obj(resume_obj: Dict[str, Any], title: str) -> str:
    personal = (resume_obj.get("personalInfo") or {}) if isinstance(resume_obj, dict) else {}
    name = str(personal.get("name", "Candidate") or "Candidate")
    role = str(personal.get("title", "Resume Draft") or "Resume Draft")
    summary = str(resume_obj.get("summary", "") or "")

    lines: List[str] = [f"# {title or 'Resume'}", "", f"## {name}", f"**{role}**", ""]
    if summary:
        lines.extend(["### Summary", summary, ""])

    return "\n".join(lines).strip() + "\n"


def save_recent_resume(
    *,
    resume_obj: Dict[str, Any],
    title: str,
    tags: List[str] | None = None,
    status: str = "ready",
    source: str = "builder",
    output_markdown: str = "",
    output_html: str = "",
    resume_id: str = "",
    prefer_llm_html: bool = False,
    template_name: str = "modern_pro.html",
    layout_preferences: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    _ensure_store()

    now = datetime.now(timezone.utc).isoformat()
    items = _read_index()
    matched = next((item for item in items if str(item.get("id", "")) == str(resume_id)), None) if resume_id else None

    record_id = str(matched.get("id", "")) if matched else (resume_id or uuid4().hex)
    created_at = str(matched.get("created_at", now)) if matched else now
    clean_tags = [str(t).strip() for t in (tags or []) if str(t).strip()]
    title_text = (title or "Resume Draft").strip() or "Resume Draft"

    paths = _resolve_artifact_paths(record_id)

    previous_markdown = _read_text_if_exists(paths["markdown"])
    previous_html = _read_text_if_exists(paths["html"])

    final_markdown = output_markdown if output_markdown else (previous_markdown or _fallback_markdown_from_resume_obj(resume_obj or {}, title_text))
    final_html = output_html if output_html else previous_html

    if prefer_llm_html and not output_html and run_layout_design is not None:
        try:
            layout_result = run_layout_design(
                resume_obj=resume_obj or {},
                layout_preferences=layout_preferences or {},
            )
            final_html = str(layout_result.get("output_html", "")) or final_html
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("[recent_resume_store] layout_design failed: %s", exc)

    paths["resume_obj"].write_text(json.dumps(resume_obj or {}, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["markdown"].write_text(final_markdown or "", encoding="utf-8")
    paths["html"].write_text(final_html or "", encoding="utf-8")

    item: Dict[str, Any] = {
        "id": record_id,
        "title": title_text,
        "status": status,
        "source": source,
        "tags": clean_tags,
        "template_name": template_name or "swiss-single",
        "layout_preferences": layout_preferences or {},
        "created_at": created_at,
        "updated_at": now,
        "resume_obj_path": _to_rel_repo_path(paths["resume_obj"]),
        "output_markdown_path": _to_rel_repo_path(paths["markdown"]),
        "output_html_path": _to_rel_repo_path(paths["html"]),
    }

    if matched:
        idx = items.index(matched)
        items[idx] = item
    else:
        items.insert(0, item)

    items.sort(key=lambda row: str(row.get("updated_at", "")), reverse=True)
    _write_index(items)

    return {
        **item,
        "resume_obj": resume_obj or {},
        "output_markdown": final_markdown or "",
        "output_html": final_html or "",
    }


def update_recent_resume_rendered_output(
    *,
    resume_id: str,
    output_html: str,
    output_markdown: str = "",
) -> Dict[str, Any] | None:
    items = _read_index()
    matched = next((item for item in items if str(item.get("id", "")) == str(resume_id)), None)
    if not matched:
        return None

    record_id = str(matched.get("id", ""))
    now = datetime.now(timezone.utc).isoformat()
    paths = _resolve_artifact_paths(record_id)

    if output_markdown:
        paths["markdown"].write_text(output_markdown, encoding="utf-8")
    paths["html"].write_text(output_html or "", encoding="utf-8")

    updated = {
        **matched,
        "updated_at": now,
    }
    idx = items.index(matched)
    items[idx] = updated
    items.sort(key=lambda row: str(row.get("updated_at", "")), reverse=True)
    _write_index(items)

    resume_obj = _read_json_if_exists(paths["resume_obj"])
    markdown = _read_text_if_exists(paths["markdown"])
    html = _read_text_if_exists(paths["html"])

    return {
        **updated,
        "resume_obj": resume_obj,
        "output_markdown": markdown,
        "output_html": html,
    }


def list_recent_resumes(limit: int = 20) -> List[Dict[str, Any]]:
    items = _read_index()
    return items[: max(1, limit)]


def get_recent_resume(resume_id: str, include_payload: bool = True) -> Dict[str, Any] | None:
    items = _read_index()
    matched = next((item for item in items if str(item.get("id", "")) == str(resume_id)), None)
    if not matched:
        return None

    item = dict(matched)
    if include_payload:
        repo_root = _repo_root()
        resume_obj_path = (repo_root / str(item.get("resume_obj_path", ""))).resolve()
        md_path = (repo_root / str(item.get("output_markdown_path", ""))).resolve()
        html_path = (repo_root / str(item.get("output_html_path", ""))).resolve()
        item["resume_obj"] = _read_json_if_exists(resume_obj_path)
        item["output_markdown"] = _read_text_if_exists(md_path)
        item["output_html"] = _read_text_if_exists(html_path)
    return item


def delete_recent_resume(resume_id: str) -> bool:
    items = _read_index()
    matched = next((item for item in items if str(item.get("id", "")) == str(resume_id)), None)
    if not matched:
        return False

    record_id = str(matched.get("id", ""))
    paths = _resolve_artifact_paths(record_id)
    for path in paths.values():
        if path.exists() and path.is_file():
            path.unlink()

    items.remove(matched)
    _write_index(items)
    return True
