import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4


_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "job_descriptions"
_INDEX_PATH = _DATA_DIR / "job_descriptions_index.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _to_rel_repo_path(path: Path) -> str:
    return str(path.relative_to(_repo_root()))


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


def _content_path(record_id: str) -> Path:
    return _DATA_DIR / f"{record_id}.txt"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception:
        return ""


def list_job_descriptions(limit: int = 50) -> List[Dict[str, Any]]:
    return _read_index()[: max(1, limit)]


def get_job_description(record_id: str, include_content: bool = True) -> Dict[str, Any] | None:
    matched = next((item for item in _read_index() if str(item.get("id", "")) == str(record_id)), None)
    if not matched:
        return None
    item = dict(matched)
    if include_content:
        item["content"] = _read_text((_repo_root() / str(item.get("content_path", ""))).resolve())
    return item


def save_job_description(*, title: str, content: str, job_description_id: str = "") -> Dict[str, Any]:
    _ensure_store()
    items = _read_index()
    matched = (
        next((item for item in items if str(item.get("id", "")) == str(job_description_id)), None)
        if job_description_id
        else None
    )
    now = _utc_now()
    record_id = str(matched.get("id", "")) if matched else (job_description_id or uuid4().hex)
    created_at = str(matched.get("created_at", now)) if matched else now
    clean_title = (title or "Job Description").strip() or "Job Description"
    clean_content = content or ""
    path = _content_path(record_id)
    path.write_text(clean_content, encoding="utf-8")

    item: Dict[str, Any] = {
        "id": record_id,
        "title": clean_title,
        "char_count": len(clean_content),
        "content_preview": clean_content.replace("\n", " ")[:280],
        "content_path": _to_rel_repo_path(path),
        "created_at": created_at,
        "updated_at": now,
    }
    if matched:
        items[items.index(matched)] = item
    else:
        items.insert(0, item)
    items.sort(key=lambda row: str(row.get("updated_at", "")), reverse=True)
    _write_index(items)
    return {**item, "content": clean_content}


def delete_job_description(record_id: str) -> bool:
    items = _read_index()
    matched = next((item for item in items if str(item.get("id", "")) == str(record_id)), None)
    if not matched:
        return False
    try:
        path = (_repo_root() / str(matched.get("content_path", ""))).resolve()
        if path.exists() and path.is_file():
            path.unlink()
    except Exception:
        pass
    items.remove(matched)
    _write_index(items)
    return True
