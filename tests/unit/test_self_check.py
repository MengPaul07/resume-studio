"""Tests for compose_and_self_check — code-based verdict system.

TargetedSelfChecker was removed per architecture simplification.
Self-check is now handled by _compose_and_self_check in turn_runner.py
using a deterministic code-based fast path.
"""

from __future__ import annotations


def test_compose_verdict_pass_when_items_exist():
    """Verdict should be 'pass' when items are present."""
    from src.services.content_refinement_v3.agent.turn_runner import _compose_and_self_check

    payload = {
        "full_suggestion_document_obj": {"items": [{"path": "summary", "reason": "test"}]},
        "assistant_message": "done",
        "target_scopes": ["summary"],
    }
    result = _compose_and_self_check(
        message="test",
        latest_refine_payload=payload,
        session_id="",
    )
    assert result["verdict"] == "pass"
    assert "items" in result["reason"]


def test_compose_verdict_pass_when_no_items():
    """Verdict should still be 'pass' when no items (general chat/analysis)."""
    from src.services.content_refinement_v3.agent.turn_runner import _compose_and_self_check

    payload = {
        "full_suggestion_document_obj": {"items": []},
        "assistant_message": "",
        "target_scopes": [],
    }
    result = _compose_and_self_check(
        message="hello",
        latest_refine_payload=payload,
        session_id="",
    )
    assert result["verdict"] == "pass"
    assert result["assistant_message"] != ""


def test_low_confidence_items_extracted():
    """_extract_low_confidence_items should find low-confidence items."""
    from src.services.content_refinement_v3.agent._suggestion import _extract_low_confidence_items

    suggestions = {
        "items": [
            {
                "path": "summary", "status": "pending", "actionability": "apply_ready",
                "low_confidence": True, "confidence": 0.5, "reason": "test",
                "refined_text": "changed summary text",
                "item_key": "summary::suggested",
                "current_value": "old summary",
                "suggested_value": "changed summary text",
                "current_value_raw": "old summary",
                "suggested_value_raw": "changed summary text",
            },
            {
                "path": "workExperience[0].description", "status": "pending",
                "actionability": "apply_ready", "low_confidence": False,
                "refined_text": "unchanged",
                "item_key": "we0::suggested",
                "current_value": "same",
                "suggested_value": "same",
                "current_value_raw": "same",
                "suggested_value_raw": "same",
            },
        ]
    }
    result = _extract_low_confidence_items(suggestions)
    assert len(result) == 1
    assert result[0]["path"] == "summary"


def test_fact_issues_extracted():
    """_extract_fact_issues should find confirm_required items."""
    from src.services.content_refinement_v3.agent._suggestion import _extract_fact_issues

    suggestions = {
        "items": [
            {"path": "personalInfo.phone", "status": "pending", "actionability": "confirm_required", "reason": "test", "refined_text": "x"},
            {"path": "summary", "status": "pending", "actionability": "apply_ready"},
        ]
    }
    result = _extract_fact_issues(suggestions)
    assert len(result) == 1
    assert result[0]["path"] == "personalInfo.phone"
