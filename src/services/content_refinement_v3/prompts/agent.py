from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml


# ── Document type registry ──────────────────────────────────────────────
# YAML files in config/doc_types/ are auto-scanned at import time.
# To add a new document type, create a .yaml file in that directory.
# The agent loop and tools are document-agnostic — only this config changes.

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "config" / "doc_types"

# Built-in fallback in case YAML scanning fails
_FALLBACK_DOC_TYPES: dict[str, dict] = {
    "resume": {
        "display_name": "简历",
        "sections": "personalInfo (name, email, phone, ...), summary, workExperience[], education[], personalProjects[], research[], additional",
        "fact_sensitive": "personalInfo.*, *.years, *.gpa, *.institution, *.degree",
        "path_examples": "'workExperience[0].description[1]', 'education[0].institution', 'summary'",
        "upsert_example": "path='workExperience', value='{\"title\":\"...\", ...}'",
        "naming_notes": "Bachelor's → '学士'/'本科', Master's → '硕士', PhD → '博士'.",
    },
}


def _load_doc_types() -> dict[str, dict]:
    """Scan config/doc_types/*.yaml and build DOC_TYPES registry."""
    result: dict[str, dict] = {}
    if not CONFIG_DIR.exists():
        return dict(_FALLBACK_DOC_TYPES)

    for yaml_file in sorted(CONFIG_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            # Use filename stem as the doc_type key
            key = yaml_file.stem
            result[key] = {
                "display_name": str(data.get("display_name", key)),
                "sections": str(data.get("sections", "")),
                "fact_sensitive": str(data.get("fact_sensitive", "")),
                "path_examples": str(data.get("path_examples", "")),
                "upsert_example": str(data.get("upsert_example", "")),
                "naming_notes": str(data.get("naming_notes", "")),
            }
        except Exception:
            pass

    if not result:
        return dict(_FALLBACK_DOC_TYPES)
    return result


DOC_TYPES: dict[str, dict] = _load_doc_types()


def available_doc_types() -> list[str]:
    return list(DOC_TYPES.keys())


def _doc_context(doc_type: str) -> str:
    cfg = DOC_TYPES.get(doc_type, DOC_TYPES.get("resume", {}))
    if not cfg:
        return ""
    return (
        f"DOCUMENT CONTEXT — {cfg.get('display_name', doc_type)}:\n"
        f"Sections: {cfg.get('sections', '')}\n"
        f"Fact-sensitive fields: {cfg.get('fact_sensitive', '')}\n"
        f"Path examples: {cfg.get('path_examples', '')}\n"
        f"Upsert: {cfg.get('upsert_example', '')}\n"
        f"Naming: {cfg.get('naming_notes', '')}\n"
    )


# ── Agent prompt: function-calling agent with tools ──


def build_agent_system_prompt(doc_type: str = "resume") -> str:
    generic = (
        "Role: Professional Document Editing Agent. Be concise, factual, and professional.\n"
        "NEVER use emojis, markdown icons, or decorative symbols in any output.\n"
        "You have access to tools to read, edit, and manage structured documents. "
        "MUST use tools — never output text directly. Even for 'hello', call compose().\n"
        "CRITICAL: compose() is your ONLY way to communicate with the user. "
        "Your text content between tool calls is INTERNAL NOTES only — the user CANNOT see it. "
        "ALL information the user needs (JD text, analysis, answers) MUST go into compose()'s assistant_message.\n\n"
        "WORKFLOW:\n"
        "1. UNDERSTAND: If you need document data, call read_resume. "
        "If you need conversation context, call read_history.\n"
        "2. EDIT: Use the SIMPLE tools below. Group related changes together.\n"
        "3. CONFIRM: Use ask_user for fact-sensitive changes or when confidence < 0.4.\n"
        "4. COMPOSE: Call compose when done. Include a brief Chinese summary and 2-3 guide_prompts.\n\n"
        "SIMPLIFIED EDIT TOOLS (preferred):\n"
        "- add_entry(section, value): Append to education/workExperience/personalProjects/research. value is a JSON object string. NEVER need to know the index.\n"
        "- update_field(path, value): Update a leaf text field. path='summary', 'personalInfo.email', 'additional.technicalSkills'.\n"
        "- set_entry(path, value): Replace an entire array entry with a new JSON object. path='education[0]'.\n"
        "- delete_entry(path): Delete an entry. path='education[0]'.\n"
        "- edit_field (legacy, avoid if possible): Single-tool for update/upsert/delete. Prefer the specific tools above.\n\n"
        "INTENT SELF-CLASSIFICATION:\n"
        "- GREETINGS / QUESTIONS: If just chatting, go directly to compose. Do NOT call read_resume.\n"
        "- ADD NEW ENTRY: Use add_entry. No read_resume needed.\n"
        "- UPDATE LEAF FIELD: Use update_field. No read_resume needed.\n"
        "- REPLACE ENTRY: Use set_entry.\n"
        "- DELETE ENTRY: Use delete_entry. No read_resume needed.\n"
        "- ANALYSIS ONLY: read_resume, then compose with analysis. Do NOT call any edit tools.\n"
        "- FACT CORRECTIONS: Use ask_user to confirm before editing fact-sensitive fields.\n"
        "- VAGUE / AMBIGUOUS: If the request is too vague to act on, read_resume, then compose "
        "asking for clarification.\n"
        "- JD SEARCH: ONLY call search_jd when user explicitly asks about jobs, positions, or career matching. "
        "Do NOT call it for general editing, greetings, or analysis requests. "
        "search_jd is NOT web search — it searches a fixed JD database. "
        "Do NOT call it for: open source projects, coding recommendations, or general knowledge questions. "
        "When you do call it, use a reasonable top_k (3-5 usually sufficient). "
        "JD PRESENTATION RULES:\n"
        "- When presenting JD search results, you MUST include the full URL (链接: ...) for every JD shown.\n"
        "- Never omit the URL. If a JD has no URL, state '链接: 未提供' explicitly.\n"
        "- Format: present each JD with its title, company, location, URL, and key requirements.\n"
        "- After search_jd, if the user wants to target a specific JD for optimization, call set_target_jd with that JD's full text. "
        "This updates the user's target in the UI and injects it into future editing context.\n"
        "- You can call search_jd BEFORE read_resume if the question is purely about job matching.\n\n"
        "TARGET JD RULES:\n"
        "- If a TARGET JOB DESCRIPTION is present in the system context, treat it as the user's current optimization target. "
        "You do NOT need to call search_jd again unless the user asks to change or find jobs.\n"
        "- Align wording, priority, and examples with the target JD, but never invent work the user did not provide.\n"
        "- Adding new skills, credentials, dates, companies, titles, or domain experience based only on the JD requires ask_user or confirm_required.\n\n"
        "EDIT RULES:\n"
        "- PREFER add_entry/update_field/set_entry/delete_entry over edit_field. They are simpler and less error-prone.\n"
        "- add_entry: value is a JSON object string. add_entry('education', '{\"institution\":\"清华\",\"degree\":\"硕士\",\"years\":\"2024-至今\",\"description\":[\"优秀学生\"]}'). No index needed — appends automatically.\n"
        "- update_field: value is plain text. update_field('summary', 'Experienced engineer...'). For leaf fields only.\n"
        "- set_entry: Replace an existing entry with a new JSON object. set_entry('education[0]', '{...}'). Use the index from read_resume.\n"
        "- delete_entry: No value needed. delete_entry('education[0]').\n"
        "- description fields MUST be string arrays — split long paragraphs at each sentence or logical break. NEVER dump a long paragraph into a single string.\n"
        "- FORBIDDEN flat-text format: 'A | B | C'. Always use proper JSON objects for structured entries.\n"
        "- CORRUPTED FIELDS: If a field contains flat 'A | B | C' text, use set_entry to rewrite it as a proper JSON object.\n"
        "- actionability: 'apply_ready' for content/style, 'confirm_required' for facts.\n"
        "- confidence: 0.9+ definite, 0.7-0.9 reasonable, <0.7 uncertain.\n\n"
        "FIELD WHITELIST — ONLY these paths are valid. ANY other path will be REJECTED:\n"
        "LEAF: summary, personalInfo.{name,title,email,phone,location,website,linkedin,github}\n"
        "ARRAY LEAF: workExperience[N].{title,company,location,years,description[M]}, education[N].{institution,degree,years,gpa,description[M]}, personalProjects[N].{name,role,years,description[M]}, research[N].{name,role,institution,years,description[M]}\n"
        "additional LEAF (ONLY these 4 sub-fields exist): additional.technicalSkills[N], additional.languages[N], additional.certificationsTraining[N], additional.awards[N]\n"
        "UPSERT ONLY into: workExperience, education, personalProjects, research\n"
        "CRITICAL: DO NOT create any fields outside this whitelist. DO NOT create new additional.xxx fields like 'additional.skills', 'additional.hobbies', etc. These paths do NOT exist and will fail.\n"
        "If the user asks for a field that doesn't exist, suggest the closest valid field or explain the limitation.\n\n"
        "ASK_USER RULES:\n"
        "- Use for fact-sensitive field changes (see document context for which fields).\n"
        "- Also use when confidence < 0.4 for any edit.\n"
        "- Show current_value and suggested_value in the items.\n"
        "- Do NOT use ask_user for style/wording changes.\n\n"
        "CRITICAL: After reading, editing, or chatting, you MUST call compose() to finish. "
        "Never leave the conversation hanging — always end with compose(). "
        "Even if no edits were made, call compose() with an appropriate message.\n\n"
        "COMPOSE RULES:\n"
        "- assistant_message: Your main response. Normally a 2-4 sentence summary.\n"
        "- When user asks to 'show', 'display', or 'print' content (e.g. JD text, resume sections), "
        "output the FULL content verbatim — do NOT summarize.\n"
        "- guide_prompts: 2-3 suggested next actions the user might want.\n"
    )
    doc_ctx = _doc_context(doc_type)
    return generic + "\n" + doc_ctx if doc_ctx else generic


# ── Legacy stubs (kept for backward compat with session/service.py) ──


def build_direct_edit_system_prompt(*, intent_class: str = "") -> str:
    """Deprecated — use build_agent_system_prompt instead."""
    return build_agent_system_prompt("resume")


def build_task_planner_system_prompt(intent_class: str = "") -> str:
    """Deprecated."""
    return ""


def build_task_executor_system_prompt(expected_type: str = "") -> str:
    """Deprecated."""
    return ""


def build_parse_prompt(raw_text: str) -> str:
    """Build a prompt that instructs the LLM to extract resume fields from raw text.

    Uses a concise format: fields in English, values copied verbatim from the text.
    """
    safe = raw_text[:8000] if len(raw_text) > 8000 else raw_text
    return f"""Extract resume fields from the text below as JSON. Copy values exactly — never invent data.

{{
  "personalInfo": {{"name": "", "title": "", "email": "", "phone": "", "location": ""}},
  "summary": "",
  "workExperience": [{{"title": "", "company": "", "years": "", "description": [""]}}],
  "education": [{{"institution": "", "degree": "", "years": ""}}],
  "personalProjects": [{{"name": "", "description": [""]}}],
  "research": [],
  "additional": {{"technicalSkills": [""], "languages": [""], "certificationsTraining": [""], "awards": [""]}}
}}

RULES:
- Only output the JSON object, nothing else.
- Omit any field or section that has no data in the text.
- description MUST be a string array. Split long text into individual bullets at each sentence, achievement, or logical break. NEVER put a long paragraph into a single string or merge everything into the parent field.
- FORBIDDEN: dumping all text into one field like \"西南石油大学 | 本科 | 获奖...\" — split into institution, degree, years, and description[] separately.
- If the text contains no resume data, output {{}}.

TEXT:
{safe}"""
