from fastapi.testclient import TestClient

from src.api import routes_resources
from src.main import app


def test_import_run_save_recent_flow(monkeypatch):
    client = TestClient(app)

    def fake_parse_document_to_text(file_path: str, use_llm_cleanup: bool = False) -> str:
        assert use_llm_cleanup is False
        return "张三 13800000000 Python FastAPI"

    def fake_parse_document(**kwargs):
        return {
            "raw_document_obj": {"personalInfo": {"name": "张三"}},
            "normalized_document_obj": {"personalInfo": {"name": "张三"}, "summary": "Python FastAPI"},
        }

    monkeypatch.setattr(routes_resources, "parse_document_to_text", fake_parse_document_to_text)
    monkeypatch.setattr(routes_resources, "json_parse_document", fake_parse_document)

    import_response = client.post(
        "/api/v1/agent/import-file",
        files={"file": ("resume.docx", b"fake-docx-content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert import_response.status_code == 200
    imported = import_response.json()
    assert imported["id"]
    assert imported["raw_text_path"] == ""
    assert "Python" in imported["raw_text"]

    run_response = client.post(
        "/api/v1/agent/run-import",
        json={"raw_text": imported["raw_text"], "file_name": imported["file_name"], "use_llm": True, "layout_preferences": {}},
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
    assert save_response.status_code == 403


def test_personal_resource_mutations_are_disabled():
    client = TestClient(app)
    assert client.delete("/api/v1/agent/imports/example").status_code == 403
    assert client.post(
        "/api/v1/agent/job-descriptions/save",
        json={"title": "private", "content": "private content"},
    ).status_code == 403
    assert client.delete("/api/v1/agent/job-descriptions/example").status_code == 403
    assert client.delete("/api/v1/agent/recent-resumes/example").status_code == 403
