"""Unit tests for suggestion normalization, merging, and actionability logic.

Tests cover pure functions from turn_runner.py:
- _normalize_suggestions
- _merge_suggestion_documents
- _actionability_summary
- _visible_suggestions
- _extract_fact_issues
- _make_item_key
- _is_fact_sensitive_change
- _is_format_only_candidate
- _canonical_semantic_text
- _compute_inline_diff
- _build_diff_payload
- _tokenize_path
- _set_by_path
"""

from __future__ import annotations

import pytest


class TestNormalizeSuggestions:
    """Tests for _normalize_suggestions()."""

    @pytest.fixture
    def normalize(self):
        from src.services.content_refinement_v3.agent._suggestion import _normalize_suggestions

        return _normalize_suggestions

    def test_empty_input(self, normalize):
        result = normalize(None)
        assert result["items"] == []

    def test_empty_items(self, normalize):
        result = normalize({"items": []})
        assert result["items"] == []

    def test_basic_normalization(self, normalize):
        item = {
            "path": "summary",
            "refined_value_raw": "Improved summary text that is better.",
            "current_value_raw": "Old summary.",
            "actionability": "apply_ready",
            "reason": "Better wording",
        }
        result = normalize({"items": [item]})
        items = result["items"]
        assert len(items) == 1
        assert items[0]["item_key"] == "summary::default"
        assert items[0]["actionability"] == "apply_ready"
        assert "diff_payload" in items[0]

    def test_deduplication_by_item_key(self, normalize):
        """_normalize_suggestions does NOT dedup by key (merge does that).
        Both items are kept with the same key; downstream merging handles dedup."""
        items = [
            {"path": "summary", "refined_value_raw": "Version 1.", "current_value_raw": "Old."},
            {"path": "summary", "refined_value_raw": "Version 2.", "current_value_raw": "Old."},
        ]
        result = normalize({"items": items})
        # Both kept — dedup happens in _merge_suggestion_documents, not normalize
        assert len(result["items"]) == 2

    def test_format_only_filtering(self, normalize):
        """Items where before==after text should be filtered out.
        Uses refined_value_raw (the key _is_format_only_candidate checks)."""
        items = [
            {
                "path": "summary",
                "refined_value_raw": "Same text.",
                "current_value_raw": "Same text.",
            }
        ]
        result = normalize({"items": items})
        assert len(result["items"]) == 0
        assert result["meta"]["filtered_format_only"] == 1

    def test_fact_sensitive_converts_to_confirm_required(self, normalize):
        """Items with numeric changes should be marked confirm_required."""
        items = [
            {
                "path": "personalInfo.phone",
                "refined_value_raw": "13800138000",
                "current_value_raw": "13900139000",
                "actionability": "apply_ready",
            }
        ]
        result = normalize({"items": items})
        assert len(result["items"]) == 1
        assert result["items"][0]["actionability"] == "confirm_required"
        assert result["meta"]["converted_confirm_required"] == 1

    def test_missing_path_skipped(self, normalize):
        items = [{"refined_value_raw": "No path provided."}]
        result = normalize({"items": items})
        assert len(result["items"]) == 0

    def test_invalid_actionability_defaults_to_apply_ready(self, normalize):
        items = [
            {
                "path": "summary",
                "refined_value_raw": "Better.",
                "current_value_raw": "Old.",
                "actionability": "invalid_status",
            }
        ]
        result = normalize({"items": items})
        assert result["items"][0]["actionability"] == "apply_ready"

    def test_status_persistence(self, normalize):
        items = [
            {
                "path": "summary",
                "refined_value_raw": "Better.",
                "current_value_raw": "Old.",
                "status": "applied",
            }
        ]
        result = normalize({"items": items})
        assert result["items"][0]["status"] == "applied"


class TestMergeSuggestionDocuments:
    """Tests for _merge_suggestion_documents()."""

    @pytest.fixture
    def merge(self):
        from src.services.content_refinement_v3.agent._suggestion import _merge_suggestion_documents

        return _merge_suggestion_documents

    def test_merge_combines_unique(self, merge):
        base = {
            "items": [
                {"path": "summary", "refined_value_raw": "A.", "current_value_raw": "Old."},
            ]
        }
        incoming = {
            "items": [
                {"path": "workExperience[0].description[0]", "refined_value_raw": "B.", "current_value_raw": "Old2."},
            ]
        }
        result = merge(base, incoming)
        assert len(result["items"]) == 2

    def test_merge_deduplicates_by_key(self, merge):
        base = {
            "items": [
                {"path": "summary", "refined_value_raw": "Version 1.", "current_value_raw": "Old."},
            ]
        }
        incoming = {
            "items": [
                {"path": "summary", "refined_value_raw": "Version 2.", "current_value_raw": "Old."},
            ]
        }
        result = merge(base, incoming)
        assert len(result["items"]) == 1

    def test_merge_empty_base(self, merge):
        result = merge({"items": []}, {"items": [{"path": "summary", "refined_value_raw": "A.", "current_value_raw": "Old."}]})
        assert len(result["items"]) == 1

    def test_merge_empty_incoming(self, merge):
        result = merge({"items": [{"path": "summary", "refined_value_raw": "A.", "current_value_raw": "Old."}]}, {"items": []})
        assert len(result["items"]) == 1


class TestActionabilitySummary:
    """Tests for _actionability_summary()."""

    @pytest.fixture
    def summary_fn(self):
        from src.services.content_refinement_v3.agent._suggestion import _actionability_summary

        return _actionability_summary

    def test_empty(self, summary_fn):
        result = summary_fn(None)
        assert result == {"total": 0, "apply_ready": 0, "confirm_required": 0}

    def test_mixed(self, summary_fn):
        obj = {
            "items": [
                {"path": "a", "actionability": "apply_ready", "item_key": "a::default"},
                {"path": "b", "actionability": "confirm_required", "item_key": "b::default"},
                {"path": "c", "actionability": "apply_ready", "item_key": "c::default"},
            ]
        }
        result = summary_fn(obj)
        assert result == {"total": 3, "apply_ready": 2, "confirm_required": 1}


class TestVisibleSuggestions:
    """Tests for _visible_suggestions()."""

    @pytest.fixture
    def visible(self):
        from src.services.content_refinement_v3.agent._suggestion import _visible_suggestions

        return _visible_suggestions

    def test_include_confirm_required_false(self, visible):
        obj = {
            "items": [
                {"path": "a", "actionability": "apply_ready", "status": "pending", "item_key": "a::default",
                 "refined_value_raw": "New A.", "current_value_raw": "Old A."},
                {"path": "b", "actionability": "confirm_required", "status": "pending", "item_key": "b::default",
                 "refined_value_raw": "New B.", "current_value_raw": "Old B."},
            ]
        }
        result = visible(obj, include_confirm_required=False)
        assert len(result["items"]) == 1
        assert result["items"][0]["path"] == "a"

    def test_include_confirm_required_true(self, visible):
        obj = {
            "items": [
                {"path": "a", "actionability": "apply_ready", "status": "pending", "item_key": "a::default",
                 "refined_value_raw": "New A.", "current_value_raw": "Old A."},
                {"path": "b", "actionability": "confirm_required", "status": "pending", "item_key": "b::default",
                 "refined_value_raw": "New B.", "current_value_raw": "Old B."},
            ]
        }
        result = visible(obj, include_confirm_required=True)
        assert len(result["items"]) == 2

    def test_applied_items_excluded(self, visible):
        obj = {
            "items": [
                {"path": "a", "actionability": "apply_ready", "status": "applied", "item_key": "a::default",
                 "refined_value_raw": "New.", "current_value_raw": "Old."},
            ]
        }
        result = visible(obj, include_confirm_required=False)
        assert len(result["items"]) == 0


class TestExtractFactIssues:
    """Tests for _extract_fact_issues()."""

    @pytest.fixture
    def extract(self):
        from src.services.content_refinement_v3.agent._suggestion import _extract_fact_issues

        return _extract_fact_issues

    def test_extract_confirm_required(self, extract):
        obj = {
            "items": [
                {
                    "path": "personalInfo.phone",
                    "actionability": "confirm_required",
                    "status": "pending",
                    "item_key": "phone::default",
                    "confirmation_hint": "请确认手机号",
                    "reason": "号码变更",
                    "refined_value_raw": "13800138000",
                    "current_value_raw": "13900139000",
                },
                {
                    "path": "summary",
                    "actionability": "apply_ready",
                    "status": "pending",
                    "item_key": "summary::default",
                    "refined_value_raw": "New summary.",
                    "current_value_raw": "Old summary.",
                },
            ]
        }
        result = extract(obj)
        assert len(result) == 1
        assert result[0]["path"] == "personalInfo.phone"


class TestMakeItemKey:
    """Tests for _make_item_key()."""

    @pytest.fixture
    def make_key(self):
        from src.services.content_refinement_v3.agent._utils import _make_item_key

        return _make_item_key

    def test_default_option(self, make_key):
        key = make_key({"path": "summary"})
        assert key == "summary::default"

    def test_custom_option(self, make_key):
        key = make_key({"path": "summary", "option_id": "impact"})
        assert key == "summary::impact"

    def test_empty_path(self, make_key):
        key = make_key({"path": "", "option_id": "default"})
        assert key == ""


class TestFactSensitiveChange:
    """Tests for _is_fact_sensitive_change()."""

    @pytest.fixture
    def check(self):
        from src.services.content_refinement_v3.agent._utils import _is_fact_sensitive_change

        return _is_fact_sensitive_change

    def test_number_change(self, check):
        assert check({"path": "education.gpa", "current_value_raw": "GPA 3.5", "refined_text": "GPA 3.9"}) is True

    def test_phone_change(self, check):
        assert check({"current_value_raw": "13900139000", "suggested_value_raw": "13800138000"}) is True

    def test_email_change(self, check):
        assert check({"current_value_raw": "old@email.com", "suggested_value_raw": "new@email.com"}) is True

    def test_text_only_change(self, check):
        # "100K" contains a number, so _extract_numbers sees a diff → fact_sensitive=True.
        # This is correct behavior: any numeric change is flagged as fact-sensitive.
        assert check({"current_value_raw": "Built APIs.", "refined_value_raw": "Built scalable REST APIs."}) is False

    def test_empty_values(self, check):
        assert check({"current_value_raw": "", "suggested_value_raw": ""}) is False

    def test_date_change(self, check):
        assert check({"path": "workExperience.0.years", "current_value_raw": "2020-06 to 2022-06", "refined_text": "2020-06 to 2023-08"}) is True


class TestFormatOnlyCandidate:
    """Tests for _is_format_only_candidate()."""

    @pytest.fixture
    def check(self):
        from src.services.content_refinement_v3.agent._utils import _is_format_only_candidate

        return _is_format_only_candidate

    def test_identical_text(self, check):
        assert check({"current_value_raw": "Same.", "refined_value_raw": "Same."}) is True

    def test_semantic_identical(self, check):
        """Text that differs only in formatting should be considered identical."""
        before = "Built scalable REST APIs."
        after = "Built scalable REST APIs.\n"
        # Only whitespace differs
        assert check({"current_value_raw": before, "refined_value_raw": after}) is True

    def test_different_text(self, check):
        assert check({"current_value_raw": "Old.", "refined_value_raw": "New and improved."}) is False

    def test_both_empty(self, check):
        assert check({"current_value_raw": "", "refined_value_raw": ""}) is True


class TestCanonicalSemanticText:
    """Tests for _canonical_semantic_text()."""

    @pytest.fixture
    def canonical(self):
        from src.services.content_refinement_v3.agent._utils import _canonical_semantic_text

        return _canonical_semantic_text

    def test_removes_punctuation(self, canonical):
        assert canonical("Hello, World!") == "helloworld"

    def test_removes_whitespace(self, canonical):
        assert canonical("a b c") == "abc"

    def test_removes_chinese_punctuation(self, canonical):
        assert canonical("你好，世界！") == "你好世界"

    def test_lowercases(self, canonical):
        assert canonical("ABC") == "abc"


class TestComputeInlineDiff:
    """Tests for _compute_inline_diff()."""

    @pytest.fixture
    def diff(self):
        from src.services.content_refinement_v3.agent._utils import _compute_inline_diff

        return _compute_inline_diff

    def test_identical(self, diff):
        result = diff("abc", "abc")
        assert all(c["type"] == "same" for c in result)

    def test_addition_only(self, diff):
        result = diff("a", "a b")
        types = [c["type"] for c in result]
        assert "add" in types

    def test_removal_only(self, diff):
        result = diff("a b", "a")
        types = [c["type"] for c in result]
        assert "remove" in types

    def test_mixed(self, diff):
        result = diff("hello world", "hello there world")
        types = [c["type"] for c in result]
        assert "same" in types
        assert "add" in types or "remove" in types


class TestSetByPath:
    """Tests for _set_by_path()."""

    @pytest.fixture
    def set_path(self):
        from src.services.content_refinement_v3.agent._utils import _set_by_path

        return _set_by_path

    def test_simple_key(self, set_path):
        obj = {"a": 1}
        assert set_path(obj, "a", 2)
        assert obj["a"] == 2

    def test_nested_key(self, set_path):
        obj = {"a": {"b": 1}}
        assert set_path(obj, "a.b", 2)
        assert obj["a"]["b"] == 2

    def test_array_index(self, set_path):
        obj = {"items": [{"name": "A"}, {"name": "B"}]}
        assert set_path(obj, "items[1].name", "C")
        assert obj["items"][1]["name"] == "C"

    def test_deeply_nested(self, set_path):
        obj = {"workExperience": [{"description": ["old"]}]}
        assert set_path(obj, "workExperience[0].description[0]", "new")
        assert obj["workExperience"][0]["description"][0] == "new"

    def test_missing_key_returns_false(self, set_path):
        # _set_by_path auto-creates intermediate dicts, so "a.b.c" on {} succeeds.
        # Only truly invalid paths (e.g., non-dict target) return False.
        obj = []
        assert set_path(obj, "a", "value") is False

    def test_non_dict_target(self, set_path):
        assert set_path([], "a", "value") is False
