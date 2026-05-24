"""Unit tests for turn runner helper functions and orchestration logic.

Tests cover:
- Intent detection helpers (_infer_scope_from_message, _is_edit_intent, etc.)
- Tokenize path and set by path
- Resolve target scopes
- Merge suggestion documents
- ChainPlanner integration with IntentResult
"""

from __future__ import annotations

import pytest


class TestInferScopeFromMessage:
    """Tests for _infer_scope_from_message()."""

    @pytest.fixture
    def infer(self):
        from src.services.content_refinement_v3.agent._utils import _infer_scope_from_message

        return _infer_scope_from_message

    def test_summary_chinese(self, infer):
        assert infer("优化个人总结部分") == "summary"

    def test_summary_english(self, infer):
        assert infer("Improve my summary section") == "summary"

    def test_work_experience_chinese(self, infer):
        assert infer("修改工作经历") == "workExperience"

    def test_work_experience_english(self, infer):
        assert infer("Update my work experience") == "workExperience"

    def test_education(self, infer):
        assert infer("丰富教育经历") == "education"

    def test_skills(self, infer):
        assert infer("更新技术栈") == "additional"

    def test_projects(self, infer):
        assert infer("优化个人项目") == "personalProjects"

    def test_contact(self, infer):
        assert infer("改一下手机号") == "personalInfo"

    def test_email(self, infer):
        assert infer("更新邮箱地址") == "personalInfo"

    def test_empty_message(self, infer):
        assert infer("") == ""

    def test_no_keywords(self, infer):
        assert infer("帮我看一下") == ""


class TestIsGlobalEditIntent:
    """Tests for _is_global_edit_intent()."""

    @pytest.fixture
    def check(self):
        from src.services.content_refinement_v3.agent._utils import _is_global_edit_intent

        return _is_global_edit_intent

    def test_global_chinese(self, check):
        assert check("整体优化一下简历") is True

    def test_global_token_quanpian(self, check):
        assert check("全篇润色") is True

    def test_global_token_quanju(self, check):
        assert check("全局调整格式") is True

    def test_not_global(self, check):
        assert check("优化 summary 部分") is False

    def test_entire_english(self, check):
        assert check("Polish the entire resume") is True


class TestIsAnalysisOnlyIntent:
    """Tests for _is_analysis_only_intent()."""

    @pytest.fixture
    def check(self):
        from src.services.content_refinement_v3.agent._utils import _is_analysis_only_intent

        return _is_analysis_only_intent

    def test_chinese_analysis_only(self, check):
        assert check("分析简历不要修改") is True

    def test_english_analysis_only(self, check):
        assert check("analyze my resume but don't modify") is True

    def test_edit_not_analysis(self, check):
        assert check("优化 summary") is False

    def test_analyze_without_refusal(self, check):
        # Has "分析" but no "不修改" — not analysis_only
        assert check("帮我分析一下简历") is False


class TestIsEditIntent:
    """Tests for _is_edit_intent()."""

    @pytest.fixture
    def check(self):
        from src.services.content_refinement_v3.agent._utils import _is_edit_intent

        return _is_edit_intent

    def test_optimize(self, check):
        assert check("优化简历") is True

    def test_polish(self, check):
        assert check("润色一下") is True

    def test_modify(self, check):
        assert check("修改工作经历") is True

    def test_add(self, check):
        assert check("添加技能") is True

    def test_greeting_not_edit(self, check):
        assert check("你好") is False

    def test_analysis_only_not_edit(self, check):
        assert check("分析简历不要修改内容") is False


class TestIsFactEditIntent:
    """Tests for _is_fact_edit_intent()."""

    @pytest.fixture
    def check(self):
        from src.services.content_refinement_v3.agent._utils import _is_fact_edit_intent

        return _is_fact_edit_intent

    def test_phone(self, check):
        assert check("手机号改成 138") is True

    def test_email(self, check):
        assert check("邮箱更新为 new@email.com") is True

    def test_date(self, check):
        assert check("日期改一下") is True

    def test_gpa(self, check):
        assert check("GPA 3.9") is True

    def test_not_fact(self, check):
        assert check("优化 summary 表达") is False


class TestTokenizePath:
    """Tests for _tokenize_path()."""

    @pytest.fixture
    def tokenize(self):
        from src.services.content_refinement_v3.agent._utils import _tokenize_path

        return _tokenize_path

    def test_simple(self, tokenize):
        assert tokenize("summary") == ["summary"]

    def test_nested(self, tokenize):
        assert tokenize("personalInfo.name") == ["personalInfo", "name"]

    def test_array_index(self, tokenize):
        assert tokenize("workExperience[0].title") == ["workExperience", 0, "title"]

    def test_deep_array(self, tokenize):
        assert tokenize("workExperience[0].description[2]") == ["workExperience", 0, "description", 2]


class TestBuildDiffPayload:
    """Tests for _build_diff_payload()."""

    @pytest.fixture
    def build_diff(self):
        from src.services.content_refinement_v3.agent._utils import _build_diff_payload

        return _build_diff_payload

    def test_diff_structure(self, build_diff):
        item = {
            "current_value_raw": "Before text.",
            "refined_text": "After text is better.",
        }
        result = build_diff(item)
        assert result["diff_type"] == "text"
        assert result["before_text"] == "Before text."
        assert result["after_text"] == "After text is better."
        assert isinstance(result["chunks"], list)
        assert len(result["chunks"]) > 0


class TestResolveTargetScopes:
    """Tests for _resolve_target_scopes()."""

    @pytest.fixture
    def resolve(self):
        from src.services.content_refinement_v3.agent._suggestion import _resolve_target_scopes

        return _resolve_target_scopes

    def test_state_scope_global(self, resolve):
        observed = {"intent_state": {"active_scope": "global", "confidence": 0.9}}
        result = resolve("优化简历", observed)
        assert len(result) == 7  # all GLOBAL_SCOPES

    def test_state_scope_specific(self, resolve):
        observed = {"intent_state": {"active_scope": "summary", "confidence": 0.9}}
        result = resolve("优化 summary", observed)
        assert result == ["summary"]

    def test_low_confidence_falls_back_to_message_inference(self, resolve):
        observed = {"intent_state": {"active_scope": "summary", "confidence": 0.3}}
        result = resolve("优化工作经历", observed)
        assert "workExperience" in result

    def test_global_message_override(self, resolve):
        # When intent_state has low confidence, the message's global token wins
        observed = {"intent_state": {"active_scope": "summary", "confidence": 0.3}}
        result = resolve("整体优化简历", observed)
        assert len(result) == 7  # global intent from message token overrides low-confidence scope

    def test_default_scopes_for_edit_intent(self, resolve):
        observed = {}
        result = resolve("优化一下", observed)
        assert len(result) == 5  # summary, workExperience, education, personalProjects, research
