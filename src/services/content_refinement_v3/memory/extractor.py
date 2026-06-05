"""Background memory extraction — runs after each turn to update user memory.

Uses a lightweight LLM call to analyze the turn and decide whether to
persist new preferences or key facts. Only updates if useful information
was found.
"""

from __future__ import annotations

import json
import logging

from .preference_store import upsert_preference

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a memory extraction agent. Analyze this conversation turn and extract any NEW user preferences worth remembering across sessions.

Return ONLY a JSON object, no explanation:
{
  "updates": [
    {"type": "preference", "key": "writing_style", "value": "prefers concise bullet points with quantified results"}
  ]
}

RULES:
- Only extract NEW or CHANGED preferences not already in existing_memory.
- Preference: user's style/tone/format/language preferences, things they like or dislike, patterns they want you to follow or avoid.
- If the user corrects or contradicts a previous preference, include the updated version.
- If the turn is just greetings, simple edits, or contains no useful long-term information, return {"updates": []}.
- Keep values concise (under 80 chars), in the user's language.
- Key names should be short English identifiers: writing_style, tone, avoid_topics, etc.
- Do NOT extract facts about the resume content (job_target, career_goal, education, skills, etc.) — the agent already reads the full conversation history.
"""


def extract_memory(
    *,
    user_message: str,
    assistant_message: str,
    accepted_items: list[dict] | None = None,
    rejected_items: list[dict] | None = None,
    existing_memory: dict | None = None,
    resume_brief: dict | None = None,
) -> list[dict]:
    """Run the extraction LLM call. Returns list of updates, or empty list on failure.

    Each update: {"type": "preference"|"fact", "key": "...", "value": "..."}
    """
    try:
        from litellm import completion
        from src.services.build_llm import build_llm

        llm = build_llm()

        # Build context
        context = f"USER MESSAGE: {user_message[:500]}\n"
        if assistant_message:
            context += f"ASSISTANT RESPONSE: {assistant_message[:300]}\n"
        if accepted_items:
            accepted_summary = "; ".join(
                f"accepted {i.get('path','?')}: {i.get('reason','')[:60]}"
                for i in (accepted_items or [])[:5]
            )
            context += f"ACCEPTED CHANGES: {accepted_summary}\n"
        if resume_brief and any(resume_brief.values()):
            context += f"RESUME CONTEXT: title={resume_brief.get('title','')}, summary={resume_brief.get('summary','')}, skills={resume_brief.get('skills','')}\n"
        if rejected_items:
            rejected_summary = "; ".join(
                f"rejected {i.get('path','?')}: {i.get('reason','')[:60]}"
                for i in (rejected_items or [])[:5]
            )
            context += f"REJECTED CHANGES: {rejected_summary}\n"

        existing_str = json.dumps(existing_memory or {}, ensure_ascii=False)
        context += f"\nExisting memory (do NOT repeat these):\n{existing_str}"

        resp = completion(
            model=llm.model,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": context},
            ],
            api_key=llm.api_key or None,
            api_base=llm.api_base or None,
            temperature=0.1,
            max_tokens=1024,
            timeout=30,
            response_format={"type": "json_object"},
        )

        raw = getattr(resp.choices[0].message, "content", "") or ""
        data = json.loads(raw.strip())
        updates = data.get("updates", []) if isinstance(data, dict) else []
        # Only persist preferences — facts are already in the agent's full conversation history
        return [u for u in updates if isinstance(u, dict) and u.get("type") == "preference" and u.get("key") and u.get("value")]

    except Exception as exc:
        logger.warning("[memory] extraction failed: %s", exc)
        return []


def apply_updates(user_id: str, updates: list[dict]) -> int:
    """Apply extracted preference updates. Returns number of changes."""
    count = 0
    for u in updates:
        try:
            if upsert_preference(user_id, u["key"], u["value"]):
                count += 1
        except Exception as exc:
            logger.warning("[memory] upsert failed for key=%s: %s", u.get("key"), exc)
    return count


def update_memory_after_turn(
    *,
    user_id: str,
    user_message: str,
    assistant_message: str,
    accepted_items: list[dict] | None = None,
    rejected_items: list[dict] | None = None,
    resume_brief: dict | None = None,
) -> int:
    """Called after each turn to extract and persist preferences. Non-blocking.

    Only preferences are persisted. Facts are not stored separately — the agent
    already has full conversation history for per-resume context.
    """
    if not user_id or not user_message.strip():
        return 0

    from .preference_store import load_memory

    existing = load_memory(user_id)
    updates = extract_memory(
        user_message=user_message,
        assistant_message=assistant_message,
        accepted_items=accepted_items,
        rejected_items=rejected_items,
        existing_memory=existing,
        resume_brief=resume_brief,
    )
    return apply_updates(user_id, updates) if updates else 0
