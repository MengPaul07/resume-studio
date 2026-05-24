from fastapi.testclient import TestClient

from src.api import routes_resources
from src.main import app


def test_import_run_save_recent_flow(monkeypatch):
    client = TestClient(app)
    imports = {}
    recent = {}

    def fake_parse_document_to_text(file_path: str, use_llm_cleanup: bool = False) -> str:
        assert use_llm_cleanup is False
        return "张三 13800000000 Python FastAPI"

    def fake_save_import_record(file_name: str, raw_text: str):
        item = {
            "id": "imp_1",
            "file_name": file_name,
            "file_ext": ".docx",
            "char_count": len(raw_text),
            "raw_text_preview": raw_text[:80],
            "raw_text_path": "mock/import.txt",
            "created_at": "2026-04-30T00:00:00+00:00",
            "raw_text": raw_text,
        }
        imports[item["id"]] = item
        return item

    def fake_get_import_record(import_id: str, include_raw_text: bool = False):
        item = imports.get(import_id)
        if not item:
            return None
        return dict(item)

    def fake_parse_document(**kwargs):
        return {
            "raw_document_obj": {"personalInfo": {"name": "张三"}},
            "normalized_document_obj": {"personalInfo": {"name": "张三"}, "summary": "Python FastAPI"},
        }

    def fake_save_recent_resume(**kwargs):
        item = {
            "id": "res_1",
            "title": kwargs["title"],
            "status": kwargs["status"],
            "source": kwargs["source"],
            "tags": kwargs["tags"],
            "created_at": "2026-04-30T00:00:00+00:00",
            "updated_at": "2026-04-30T00:00:00+00:00",
            "resume_obj_path": "mock/resume.json",
            "output_markdown_path": "mock/resume.md",
            "output_html_path": "mock/resume.html",
            "resume_obj": kwargs["resume_obj"],
            "output_markdown": kwargs["output_markdown"],
            "output_html": kwargs["output_html"],
        }
        recent[item["id"]] = item
        return item

    def fake_list_recent_resumes(limit: int = 20):
        return list(recent.values())[:limit]

    monkeypatch.setattr(routes_resources, "parse_document_to_text", fake_parse_document_to_text)
    monkeypatch.setattr(routes_resources, "save_import_record", fake_save_import_record)
    monkeypatch.setattr(routes_resources, "get_import_record", fake_get_import_record)
    monkeypatch.setattr(routes_resources, "json_parse_document", fake_parse_document)
    monkeypatch.setattr(routes_resources, "save_recent_resume", fake_save_recent_resume)
    monkeypatch.setattr(routes_resources, "list_recent_resumes", fake_list_recent_resumes)

    import_response = client.post(
        "/api/v1/agent/import-file",
        files={"file": ("resume.docx", b"fake-docx-content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert import_response.status_code == 200
    imported = import_response.json()
    assert imported["id"] == "imp_1"
    assert "Python" in imported["raw_text"]

    run_response = client.post(
        "/api/v1/agent/run-import",
        json={"import_id": imported["id"], "use_llm": True, "layout_preferences": {}},
    )
    assert run_response.status_code == 200
    built = run_response.json()
    assert built["resume_obj"]["summary"] == "Python FastAPI"
    assert built["output_html"] == ""
    assert built["output_markdown"] == ""

    save_response = client.post(
        "/api/v1/agent/recent-resumes/save",
        json={
            "title": "resume",
            "status": "ready",
            "source": "import",
            "tags": ["import"],
            "resume_obj": built["resume_obj"],
            "output_markdown": built["output_markdown"],
            "output_html": built["output_html"],
        },
    )
    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["id"] == "res_1"
    assert saved["doc_type"] == "resume"

    list_response = client.get("/api/v1/agent/recent-resumes?limit=20")
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == "res_1"
