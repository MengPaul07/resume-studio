from pathlib import Path


def test_session_store_uses_memory_without_creating_data_directory(tmp_path: Path, monkeypatch):
    import src.services.content_refinement_v3.session.store as store

    data_dir = tmp_path / "must-not-exist"
    monkeypatch.setattr(store, "_DATA_DIR", data_dir)
    monkeypatch.setattr(store, "_DB_PATH", data_dir / "session.sqlite3")
    monkeypatch.setattr(store.settings, "PERSONAL_DATA_STORAGE", "memory")
    monkeypatch.setattr(store, "_memory_keeper", None)

    session = store.create_session(title="Private", raw_resume_obj={"name": "Alice"})
    loaded = store.get_session(session["id"], include_state=True)

    assert loaded is not None
    assert loaded["state"]["raw_resume_obj"] == {"name": "Alice"}
    assert not data_dir.exists()
