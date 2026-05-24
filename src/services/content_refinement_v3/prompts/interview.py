"""Mock interview prompt wrapper."""

from .interview_presets import (
    DEFAULT_PRESET,
    PRESETS,
    build_interview_prompt_with_params,
    build_interviewer_prompt,
)


def build_interview_prompt(
    target_jd: str = "",
    preset_id: str | None = None,
    company: str | None = None,
    role: str | None = None,
    level: str | None = None,
    style: str | None = None,
    depth: str | None = None,
    focus: dict | None = None,
    rounds: int | None = None,
    language: str | None = None,
    time_pressure: str | None = None,
    user_preferences: str | None = None,
) -> str:
    """Build interview prompt from a named interviewer or legacy parameters."""
    if preset_id:
        return build_interviewer_prompt(
            target_jd=target_jd,
            preset_id=preset_id,
            rounds=rounds,
            user_preferences=user_preferences,
        )

    preset = next((p for p in PRESETS if p["id"] == DEFAULT_PRESET), None)
    return build_interview_prompt_with_params(
        target_jd=target_jd,
        company=company or "enterprise",
        role=role or "general",
        level=level or "mid",
        style=style or "balanced",
        depth=depth or "moderate",
        focus=focus,
        rounds=rounds or 8,
        language=language or (preset["language"] if preset else "zh"),
        time_pressure=time_pressure or "standard",
        user_preferences=user_preferences,
    )
