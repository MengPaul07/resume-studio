"""Tests for intent classification — migrated to direct_edit self-classification.

IntentResolver and ChainPlanner were removed per architecture simplification.
Intent classification is now handled by the direct_edit LLM prompt itself.
"""

from __future__ import annotations

import pytest


def test_direct_edit_prompt_has_intent_self_classification():
    """Verify the agent system prompt includes intent self-classification."""
    from src.services.content_refinement_v3.prompts.agent import build_agent_system_prompt

    prompt = build_agent_system_prompt("resume")
    assert "INTENT SELF-CLASSIFICATION" in prompt
    assert "FACT CORRECTIONS" in prompt
    assert "EDIT:" in prompt
    assert "ANALYSIS ONLY" in prompt


def test_direct_edit_prompt_handles_vague_requests():
    """Verify the prompt handles vague/ambiguous requests."""
    from src.services.content_refinement_v3.prompts.agent import build_agent_system_prompt, available_doc_types

    prompt = build_agent_system_prompt("resume")
    assert "VAGUE" in prompt.upper()
    assert "too vague" in prompt.lower()
