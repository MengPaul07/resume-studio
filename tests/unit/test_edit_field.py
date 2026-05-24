"""Comprehensive tests for edit_field tool, path utilities, and parse prompt."""

import json
import pytest


# ═══════════════════════════════════════════════════════════════════
# _set_by_path_local / _get_by_path_local
# ═══════════════════════════════════════════════════════════════════

class TestSetByPathLocal:
    @pytest.fixture
    def set_by_path(self):
        from src.services.content_refinement_v3.session.service import _set_by_path_local
        return _set_by_path_local

    @pytest.fixture
    def get_by_path(self):
        from src.services.content_refinement_v3.session.service import _get_by_path_local
        return _get_by_path_local

    def test_set_simple_key(self, set_by_path, get_by_path):
        obj = {"summary": "old"}
        assert set_by_path(obj, "summary", "new")
        assert get_by_path(obj, "summary") == "new"

    def test_set_nested_key(self, set_by_path, get_by_path):
        obj = {"personalInfo": {"name": "old"}}
        assert set_by_path(obj, "personalInfo.name", "Li Yan")
        assert get_by_path(obj, "personalInfo.name") == "Li Yan"

    def test_set_array_index(self, set_by_path, get_by_path):
        obj = {"workExperience": [{"title": "SDE"}]}
        assert set_by_path(obj, "workExperience[0].title", "Senior SDE")
        assert get_by_path(obj, "workExperience[0].title") == "Senior SDE"

    def test_set_nonexistent_path_returns_false(self, set_by_path):
        obj = {"summary": "x"}
        assert set_by_path(obj, "workExperience[0].title", "x") is False

    def test_set_nonexistent_nested_key_returns_false(self, set_by_path):
        obj = {"summary": "x"}
        assert set_by_path(obj, "personalInfo.name", "x") is False

    def test_get_nonexistent_path_returns_none(self, get_by_path):
        obj = {"summary": "x"}
        assert get_by_path(obj, "personalInfo.name") is None

    def test_upsert_append_to_array(self, set_by_path, get_by_path):
        obj = {"workExperience": [{"title": "first"}]}
        assert set_by_path(obj, "workExperience[1]", {"title": "second"}, upsert=True)
        assert len(obj["workExperience"]) == 2
        assert get_by_path(obj, "workExperience[1].title") == "second"

    def test_upsert_skip_index_fails_without_upsert(self, set_by_path):
        obj = {"workExperience": [{"title": "first"}]}
        assert set_by_path(obj, "workExperience[1]", {"title": "second"}) is False

    def test_upsert_beyond_length_fails(self, set_by_path):
        obj = {"workExperience": [{"title": "first"}]}
        assert set_by_path(obj, "workExperience[3]", {"title": "skip"}, upsert=True) is False

    def test_upsert_new_key_in_dict(self, set_by_path, get_by_path):
        obj: dict = {"education": []}
        assert set_by_path(obj, "education", [{"institution": "Tsinghua"}], upsert=True)
        assert get_by_path(obj, "education[0].institution") == "Tsinghua"

    def test_set_dict_value(self, set_by_path, get_by_path):
        obj = {"additional": {}}
        assert set_by_path(obj, "additional", {"technicalSkills": "Python, Go"})
        assert get_by_path(obj, "additional.technicalSkills") == "Python, Go"

    def test_set_deeply_nested(self, set_by_path, get_by_path):
        obj = {"workExperience": [{"title": "SDE", "description": ["a", "b"]}]}
        assert set_by_path(obj, "workExperience[0].description[1]", "modified b")
        assert get_by_path(obj, "workExperience[0].description[1]") == "modified b"


# ═══════════════════════════════════════════════════════════════════
# _tokenize_path_local
# ═══════════════════════════════════════════════════════════════════

class TestTokenizePath:
    @pytest.fixture
    def tokenize(self):
        from src.services.content_refinement_v3.session.service import _tokenize_path_local
        return _tokenize_path_local

    def test_simple_key(self, tokenize):
        assert tokenize("summary") == ["summary"]

    def test_nested_key(self, tokenize):
        assert tokenize("personalInfo.name") == ["personalInfo", "name"]

    def test_array_index(self, tokenize):
        assert tokenize("workExperience[0].title") == ["workExperience", 0, "title"]

    def test_multi_level(self, tokenize):
        assert tokenize("workExperience[2].description[1]") == ["workExperience", 2, "description", 1]

    def test_empty_string(self, tokenize):
        assert tokenize("") == []


# ═══════════════════════════════════════════════════════════════════
# edit_field tool — JSON auto-parse and flat-text rejection
# ═══════════════════════════════════════════════════════════════════

class TestEditFieldJsonParsing:
    @pytest.fixture
    def tool(self):
        from src.services.content_refinement_v3.agent._tools import tool_edit_field
        return tool_edit_field

    def _make_session_with_resume(self, resume: dict):
        """Create a session and store a resume in it, returning session_id."""
        from src.services.content_refinement_v3.session.store import (
            create_session, save_session_state, _DATA_DIR, _DB_PATH,
        )
        import tempfile, os
        # ensure isolated dirs exist
        os.makedirs(str(_DATA_DIR), exist_ok=True)
        s = create_session(title="test", window_size=10, doc_type="resume", resume_id="test-123")
        sid = str(s["id"])
        save_session_state(session_id=sid, refined_resume_obj=resume)
        return sid

    def test_parses_json_object_value(self, tool):
        sid = self._make_session_with_resume({"education": []})
        result = tool(
            session_id=sid, path="education[0]",
            value='{"institution":"Tsinghua","degree":"Master","years":"2024-2026","description":["excellent student"]}',
            op="upsert", reason="add education",
        )
        assert result.success
        written = result.data.get("written")
        assert isinstance(written, dict)
        assert written["institution"] == "Tsinghua"
        assert written["degree"] == "Master"
        assert written["description"] == ["excellent student"]

    def test_parses_json_list_value(self, tool):
        sid = self._make_session_with_resume({"personalProjects": []})
        result = tool(
            session_id=sid, path="personalProjects[0]",
            value='{"name":"Open Source Tool","description":["built X","deployed Y"]}',
            op="upsert", reason="add project",
        )
        assert result.success
        written = result.data.get("written")
        assert isinstance(written, dict)
        assert written["description"] == ["built X", "deployed Y"]

    def test_plain_text_value_remains_string(self, tool):
        sid = self._make_session_with_resume({"summary": ""})
        result = tool(
            session_id=sid, path="summary",
            value="Experienced backend engineer with 5 years in distributed systems.",
            op="update", reason="set summary",
        )
        assert result.success
        assert result.data.get("written") == "Experienced backend engineer with 5 years in distributed systems."

    def test_upsert_creates_new_array_entry(self, tool):
        sid = self._make_session_with_resume({"education": []})
        result = tool(
            session_id=sid, path="education",
            value='{"institution":"Tsinghua","degree":"Master","years":"2024-2026"}',
            op="upsert", reason="add first education",
        )
        assert result.success
        # read back to verify
        from src.services.content_refinement_v3.session.service import _get_by_path_local
        from src.services.content_refinement_v3.backends.session import get_session
        session = get_session(sid, include_state=True)
        state = (session or {}).get("state", {}) or {}
        resume = state.get("refined_resume_obj", {})
        edu = _get_by_path_local(resume, "education")
        assert isinstance(edu, list)
        assert len(edu) == 1
        assert _get_by_path_local(resume, "education[0].institution") == "Tsinghua"

    def test_delete_entry(self, tool):
        sid = self._make_session_with_resume({"workExperience": [{"title": "SDE"}, {"title": "TL"}]})
        result = tool(
            session_id=sid, path="workExperience[0]", value="",
            op="delete", reason="remove first",
        )
        assert result.success
        from src.services.content_refinement_v3.session.service import _get_by_path_local
        from src.services.content_refinement_v3.backends.session import get_session
        session = get_session(sid, include_state=True)
        state = (session or {}).get("state", {}) or {}
        resume = state.get("refined_resume_obj", {})
        we = _get_by_path_local(resume, "workExperience")
        assert len(we) == 1
        assert _get_by_path_local(resume, "workExperience[0].title") == "TL"

    def test_no_resume_loaded_returns_error(self, tool):
        result = tool(
            session_id="nonexistent", path="summary",
            value="test", op="update",
        )
        assert result.success is False
        assert "session" in (result.error or "").lower() or "resume" in (result.error or "").lower()


# ═══════════════════════════════════════════════════════════════════
# edit_field — flat-text detection for object paths
# ═══════════════════════════════════════════════════════════════════

class TestEditFieldFlatTextObjectPaths:
    """Verify that when a JSON value is provided for an object path, it is
    correctly parsed. Flat text (without JSON) is accepted as-is by the tool
    (the prompt is what prevents flat text — tested separately)."""

    @pytest.fixture
    def tool(self):
        from src.services.content_refinement_v3.agent._tools import tool_edit_field
        return tool_edit_field

    def _make_session(self, resume: dict):
        from src.services.content_refinement_v3.session.store import create_session, save_session_state, _DATA_DIR
        import os; os.makedirs(str(_DATA_DIR), exist_ok=True)
        s = create_session(title="test", window_size=10, doc_type="resume", resume_id="test-456")
        sid = str(s["id"])
        save_session_state(session_id=sid, refined_resume_obj=resume)
        return sid

    def test_object_path_with_json_value_parses_correctly(self, tool):
        """Path 'education[0]' with JSON object value → parsed as dict."""
        sid = self._make_session({"education": []})
        result = tool(
            session_id=sid, path="education[0]",
            value='{"institution":"Tsinghua","degree":"Master","years":"2024-2026","description":["优秀学生"]}',
            op="upsert", reason="add structured education",
        )
        assert result.success
        written = result.data.get("written")
        assert isinstance(written, dict), f"Expected dict, got {type(written)}: {written}"
        assert written["institution"] == "Tsinghua"
        assert isinstance(written["description"], list)

    def test_flat_text_to_object_path_still_accepted_by_tool(self, tool):
        """Flat text for an object path is accepted by the tool (no code-level
        rejection). The prompt is responsible for preventing this pattern."""
        sid = self._make_session({"education": []})
        result = tool(
            session_id=sid, path="education[0]",
            value="Tsinghua | Master | 2024-2026",
            op="upsert", reason="add flat education",
        )
        assert result.success
        written = result.data.get("written")
        # tool allows it — stored as plain string at the path
        assert isinstance(written, str)
        assert "Tsinghua" in written

    def test_empty_json_object_for_new_entry(self, tool):
        sid = self._make_session({"education": []})
        result = tool(
            session_id=sid, path="education[0]",
            value='{}', op="upsert", reason="add empty entry",
        )
        assert result.success


# ═══════════════════════════════════════════════════════════════════
# build_parse_prompt
# ═══════════════════════════════════════════════════════════════════

class TestBuildParsePrompt:
    @pytest.fixture
    def build(self):
        from src.services.content_refinement_v3.prompts.agent import build_parse_prompt
        return build_parse_prompt

    def test_returns_non_empty_string(self, build):
        result = build("John Doe\nSoftware Engineer\nWorked at Google")
        assert len(result) > 50

    def test_includes_raw_text(self, build):
        raw = "John Doe\nSoftware Engineer\nWorked at Google"
        result = build(raw)
        assert raw in result

    def test_includes_required_json_fields(self, build):
        result = build("Some resume text")
        assert "personalInfo" in result
        assert "workExperience" in result
        assert "education" in result
        assert "personalProjects" in result
        assert "additional" in result

    def test_includes_description_array_rule(self, build):
        result = build("Some resume text")
        assert "description" in result.lower()
        assert "array" in result.lower()

    def test_includes_flat_text_forbidden_rule(self, build):
        result = build("Some resume text")
        assert "FORBIDDEN" in result or "forbidden" in result.lower()

    def test_truncates_long_text(self, build):
        long_text = "word " * 10000
        result = build(long_text)
        assert len(result) < 12000  # 8000 text + prompt overhead < ~12000 chars

    def test_handles_empty_text(self, build):
        result = build("")
        assert len(result) > 0
        assert "TEXT:" in result


# ═══════════════════════════════════════════════════════════════════
# Path utilities — end-to-end with realistic resume JSON
# ═══════════════════════════════════════════════════════════════════

class TestPathUtilsWithRealResume:
    @pytest.fixture
    def set_by_path(self):
        from src.services.content_refinement_v3.session.service import _set_by_path_local
        return _set_by_path_local

    @pytest.fixture
    def get_by_path(self):
        from src.services.content_refinement_v3.session.service import _get_by_path_local
        return _get_by_path_local

    @pytest.fixture
    def resume(self):
        return {
            "personalInfo": {"name": "Li Yan", "title": "Backend Engineer", "email": "li@example.com"},
            "summary": "Experienced engineer",
            "workExperience": [
                {
                    "title": "SDE",
                    "company": "TechCorp",
                    "years": "2020-2023",
                    "description": ["Built APIs", "Led migration"],
                },
                {
                    "title": "Senior SDE",
                    "company": "StartupX",
                    "years": "2023-present",
                    "description": ["Architected platform"],
                },
            ],
            "education": [
                {
                    "institution": "Tsinghua University",
                    "degree": "Master",
                    "years": "2024-2026",
                    "description": ["Excellent student award"],
                },
            ],
            "personalProjects": [],
            "additional": {"technicalSkills": "Python, Go, React"},
        }

    # ── read operations ──

    def test_read_simple_key(self, get_by_path, resume):
        assert get_by_path(resume, "summary") == "Experienced engineer"

    def test_read_nested_key(self, get_by_path, resume):
        assert get_by_path(resume, "personalInfo.name") == "Li Yan"

    def test_read_array_item_field(self, get_by_path, resume):
        assert get_by_path(resume, "workExperience[0].title") == "SDE"

    def test_read_array_item_description(self, get_by_path, resume):
        desc = get_by_path(resume, "workExperience[0].description[1]")
        assert desc == "Led migration"

    def test_read_second_array_item(self, get_by_path, resume):
        assert get_by_path(resume, "workExperience[1].company") == "StartupX"

    def test_read_education_field(self, get_by_path, resume):
        assert get_by_path(resume, "education[0].institution") == "Tsinghua University"

    def test_read_additional_field(self, get_by_path, resume):
        assert get_by_path(resume, "additional.technicalSkills") == "Python, Go, React"

    # ── write operations ──

    def test_write_simple_key(self, set_by_path, get_by_path, resume):
        assert set_by_path(resume, "summary", "Updated summary")
        assert get_by_path(resume, "summary") == "Updated summary"

    def test_write_nested_object_field(self, set_by_path, get_by_path, resume):
        assert set_by_path(resume, "personalInfo.title", "Staff Engineer")
        assert get_by_path(resume, "personalInfo.title") == "Staff Engineer"

    def test_write_array_description_item(self, set_by_path, get_by_path, resume):
        assert set_by_path(resume, "workExperience[0].description[0]", "Built scalable APIs")
        assert get_by_path(resume, "workExperience[0].description[0]") == "Built scalable APIs"

    def test_write_full_array_object(self, set_by_path, get_by_path, resume):
        new_obj = {"title": "CTO", "company": "NewCo", "years": "2024-present", "description": ["Led team"]}
        assert set_by_path(resume, "workExperience[1]", new_obj)
        assert get_by_path(resume, "workExperience[1].title") == "CTO"

    def test_upsert_append_to_array_in_real_resume(self, set_by_path, get_by_path, resume):
        assert set_by_path(resume, "personalProjects[0]", {"name": "Open Source Tool", "description": ["built"]}, upsert=True)
        assert get_by_path(resume, "personalProjects[0].name") == "Open Source Tool"

    def test_write_additional_skills(self, set_by_path, get_by_path, resume):
        assert set_by_path(resume, "additional.technicalSkills", "Python, Go, Rust, React")
        assert "Rust" in get_by_path(resume, "additional.technicalSkills")

    # ── invalid paths ──

    def test_invalid_array_index_returns_false(self, set_by_path, resume):
        assert set_by_path(resume, "workExperience[5].title", "x") is False

    def test_invalid_key_returns_false(self, set_by_path, resume):
        assert set_by_path(resume, "nonexistent.field", "x") is False

    def test_get_nonexistent_returns_none(self, get_by_path, resume):
        assert get_by_path(resume, "workExperience[99].title") is None
