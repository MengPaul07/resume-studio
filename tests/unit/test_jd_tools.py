from __future__ import annotations


def test_set_target_jd_persists_to_rag_context(monkeypatch):
    from src.services.content_refinement_v3.agent import _tools

    saved = {}

    def fake_get_session_content(*, session_id, message_limit, event_limit):
        return {"state": {"rag_context_by_path": {"existing": {"keep": True}}}}

    def fake_save_session_state(**kwargs):
        saved.update(kwargs)

    import src.services.content_refinement_v3.session.service as session_service

    monkeypatch.setattr(session_service, "get_session_content", fake_get_session_content)
    monkeypatch.setattr(session_service, "save_session_state", fake_save_session_state)

    result = _tools.tool_set_target_jd(
        session_id="s1",
        jd_id="jd_backend",
        jd_text="Backend Engineer\nRequirements: Python, Redis, distributed systems.",
        metadata={"title": "Backend Engineer", "company": "Acme"},
    )

    assert result.success
    rag = saved["rag_context_by_path"]
    assert rag["existing"] == {"keep": True}
    assert rag["target_jd"]["id"] == "jd_backend"
    assert rag["target_jd"]["text"].startswith("Backend Engineer")
    assert "Backend Engineer" in rag["target_jd"]["card_summary"]


def test_search_jd_returns_card_summary(monkeypatch):
    from src.services.content_refinement_v3.agent import _tools

    class FakeRepo:
        def query(self, target_role, top_k, filters=None):
            return [
                {
                    "id": "jd_1",
                    "text": "Backend Engineer\nResponsibilities: Build APIs.\nRequirements: Python and Redis.",
                    "metadata": {
                        "title": "Backend Engineer",
                        "company": "Acme",
                        "role_direction": "backend",
                        "recruitment_type": "experienced",
                    },
                    "distance": 0.42,
                }
            ]

    import src.services.rag.jd_repository as jd_repository

    monkeypatch.setattr(jd_repository, "JdRepository", lambda: FakeRepo())

    result = _tools.tool_search_jd(query="backend python", top_k=3)

    assert result.success
    match = result.data["matches"][0]
    assert match["id"] == "jd_1"
    assert match["text"] == match["full_text"]
    assert "Backend Engineer" in match["card_summary"]
    assert match["metadata"]["company"] == "Acme"
