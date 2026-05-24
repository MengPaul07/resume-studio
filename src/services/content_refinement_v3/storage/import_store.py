import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4


_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "imports"
_INDEX_PATH = _DATA_DIR / "imports_index.json"


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


def save_import_record(file_name: str, raw_text: str) -> Dict[str, Any]:
    _ensure_store()

    record_id = uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()
    suffix = Path(file_name or "").suffix.lower()

    text_path = _DATA_DIR / f"{record_id}.txt"
    text_path.write_text(raw_text or "", encoding="utf-8")

    item: Dict[str, Any] = {
        "id": record_id,
        "file_name": file_name,
        "file_ext": suffix,
        "char_count": len(raw_text or ""),
        "raw_text_preview": (raw_text or "").replace("\n", " ")[:280],
        "raw_text_path": str(text_path.relative_to(Path(__file__).resolve().parents[3])),
        "created_at": created_at,
    }

    items = _read_index()
    items.insert(0, item)
    _write_index(items)

    # Return full raw_text for immediate frontend display/usage.
    return {
        **item,
        "raw_text": raw_text or "",
    }


def list_import_records(limit: int = 50) -> List[Dict[str, Any]]:
    items = _read_index()
    return items[: max(1, limit)]


def get_import_record(record_id: str, include_raw_text: bool = False) -> Dict[str, Any] | None:
    items = _read_index()
    matched = next((item for item in items if str(item.get("id", "")) == str(record_id)), None)
    if not matched:
        return None

    item = dict(matched)
    if include_raw_text:
        repo_root = Path(__file__).resolve().parents[3]
        rel_path = item.get("raw_text_path", "")
        try:
            text_path = (repo_root / rel_path).resolve()
            item["raw_text"] = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
        except Exception:
            item["raw_text"] = ""
    return item


def delete_import_record(record_id: str) -> bool:
    items = _read_index()
    matched = next((item for item in items if str(item.get("id", "")) == str(record_id)), None)
    if not matched:
        return False

    repo_root = Path(__file__).resolve().parents[3]
    rel_path = str(matched.get("raw_text_path", ""))
    try:
        text_path = (repo_root / rel_path).resolve()
        if text_path.exists() and text_path.is_file():
            text_path.unlink()
    except Exception:
        pass

    items.remove(matched)
    _write_index(items)
    return True
