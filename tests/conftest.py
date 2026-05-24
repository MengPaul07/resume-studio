from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_runtime_stores(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests from writing runtime data into the checked-out repository."""
    import src.services.content_refinement_v3.session.store as session_store
    import src.services.content_refinement_v3.storage.import_store as import_store
    import src.services.content_refinement_v3.storage.recent_resume_store as recent_store

    session_dir = tmp_path / "session_memory"
    imports_dir = tmp_path / "imports"
    recent_dir = tmp_path / "recent_resumes"

    monkeypatch.setattr(session_store, "_DATA_DIR", session_dir)
    monkeypatch.setattr(session_store, "_DB_PATH", session_dir / "session_memory.sqlite3")

    monkeypatch.setattr(import_store, "_DATA_DIR", imports_dir)
    monkeypatch.setattr(import_store, "_INDEX_PATH", imports_dir / "imports_index.json")

    monkeypatch.setattr(recent_store, "_DATA_DIR", recent_dir)
    monkeypatch.setattr(recent_store, "_INDEX_PATH", recent_dir / "recent_resumes_index.json")
