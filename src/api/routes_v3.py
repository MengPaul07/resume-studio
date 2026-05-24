from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.services.content_refinement_v3.backends.session import get_session, get_session_content, start_session
from src.services.content_refinement_v3.session.store import delete_sessions_by_resume_id
from src.services.content_refinement_v3.agent.turn_runner import (
    apply_changes,
    reject_changes,
    rollback_changes,
    run_turn_sse,
    resume_turn_sse,
)
from src.utils.context import set_llm_config

router = APIRouter(tags=["AgentV3"])
logger = logging.getLogger(__name__)


class V3BaseRequest(BaseModel):
    llm_config: Dict[str, Any] = Field(default_factory=dict)
    layout_preferences: Dict[str, Any] = Field(default_factory=dict)


class V3CreateSessionRequest(V3BaseRequest):
    title: str = "Tailor Session"
    window_size: int = Field(default=10, ge=1, le=50)
    resume_id: str = ""
    raw_document_obj: Dict[str, Any] = Field(default_factory=dict)
    normalized_document_obj: Dict[str, Any] = Field(default_factory=dict)
    refined_document_obj: Dict[str, Any] = Field(default_factory=dict)


class V3RunTurnRequest(V3BaseRequest):
    message: str
    allow_mutation: bool = True
    target_jd: str = ""
    mode: str = "refine"  # "refine" or "interview" or "build"
    interview_config: Dict[str, Any] = Field(default_factory=dict)


class V3ApplyRequest(V3BaseRequest):
    human_review_decision: Dict[str, Any] = Field(default_factory=dict)
    suggestion_document_obj: Dict[str, Any] = Field(default_factory=dict)


class V3RejectRequest(V3BaseRequest):
    rejected_item_keys: List[str] = Field(default_factory=list)
    reject_all: bool = False
    suggestion_document_obj: Dict[str, Any] = Field(default_factory=dict)


class V3RollbackRequest(BaseModel):
    version_id: str
    note: str = ""


@router.post("/agent/v3/sessions")
async def create_session(payload: V3CreateSessionRequest) -> Dict[str, Any]:
    set_llm_config(payload.llm_config)
    try:
        session = start_session(
            doc_type="resume",
            title=payload.title,
            window_size=payload.window_size,
            resume_id=payload.resume_id,
            raw_resume_obj=payload.raw_document_obj,
            normalized_resume_obj=payload.normalized_document_obj,
            refined_resume_obj=payload.refined_document_obj,
        )
        state = session.get("state", {}) if isinstance(session.get("state", {}), dict) else {}
        return {
            "session_id": str(session.get("id", "")),
            "doc_type": str(session.get("doc_type", "resume")),
            "title": str(session.get("title", "")),
            "status": str(session.get("status", "active")),
            "window_size": int(session.get("window_size", 10) or 10),
            "created_at": str(session.get("created_at", "")),
            "updated_at": str(session.get("updated_at", "")),
            "state": state,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"create session failed: {exc}")


@router.get("/agent/v3/sessions/{session_id}")
async def get_session_state(session_id: str, message_limit: int = 5, event_limit: int = 200) -> Dict[str, Any]:
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    try:
        return get_session_content(session_id=session_id, message_limit=message_limit, event_limit=event_limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"get session failed: {exc}")


@router.post("/agent/v3/sessions/{session_id}/turns:run")
async def run_turn(session_id: str, payload: V3RunTurnRequest):
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    set_llm_config(payload.llm_config)
    logger.info(
        "[v3][route.turn] session=%s allow_mutation=%s message=%s",
        session_id,
        bool(payload.allow_mutation),
        str(payload.message or "")[:120],
    )
    generator = run_turn_sse(
        session_id=session_id,
        message=payload.message,
        allow_mutation=bool(payload.allow_mutation),
        layout_preferences=payload.layout_preferences,
        target_jd=payload.target_jd,
        mode=payload.mode,
        interview_config=payload.interview_config or {},
    )
    return StreamingResponse(generator, media_type="text/event-stream")


class V3ResumeTurnRequest(BaseModel):
    llm_config: Dict[str, Any] = Field(default_factory=dict)
    turn_id: str = ""
    user_response: str = "Confirmed."


@router.post("/agent/v3/sessions/{session_id}/turns:resume")
async def resume_turn(session_id: str, payload: V3ResumeTurnRequest) -> Dict[str, Any]:
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    set_llm_config(payload.llm_config)
    logger.info(
        "[v3][route.resume] session=%s turn=%s response=%s",
        session_id, payload.turn_id, str(payload.user_response or "")[:80],
    )
    try:
        # Collect all SSE events, extract the final turn.completed payload
        final_payload = None
        for event_str in resume_turn_sse(
            session_id=session_id,
            turn_id=payload.turn_id,
            user_response=payload.user_response,
        ):
            if event_str.startswith("event: turn.completed"):
                # Parse the data line
                for line in event_str.split("\n"):
                    if line.startswith("data: "):
                        import json as _json
                        final_payload = _json.loads(line[6:])
        if final_payload:
            return final_payload
        raise HTTPException(status_code=500, detail="resume produced no result")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"resume failed: {exc}")


@router.delete("/agent/v3/sessions/by-resume/{resume_id}")
async def delete_sessions_for_resume(resume_id: str) -> Dict[str, Any]:
    """Clean up all sessions associated with a resume."""
    try:
        count = delete_sessions_by_resume_id(resume_id)
        return {"deleted_sessions": count}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"cleanup failed: {exc}")


@router.post("/agent/v3/sessions/{session_id}/actions:apply")
async def apply_action(session_id: str, payload: V3ApplyRequest) -> Dict[str, Any]:
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    set_llm_config(payload.llm_config)
    try:
        accepted_item_keys = (
            payload.human_review_decision.get("accepted_item_keys", [])
            if isinstance(payload.human_review_decision.get("accepted_item_keys", []), list)
            else []
        )
        if not accepted_item_keys:
            raise HTTPException(status_code=422, detail="accepted_item_keys is required")
        logger.info("[v3][route.apply] session=%s accepted_keys=%s", session_id, accepted_item_keys)
        return apply_changes(
            session_id=session_id,
            human_review_decision=payload.human_review_decision,
            suggestion_document_obj=payload.suggestion_document_obj,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"actions apply failed: {exc}")


@router.post("/agent/v3/sessions/{session_id}/actions:reject")
async def reject_action(session_id: str, payload: V3RejectRequest) -> Dict[str, Any]:
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    set_llm_config(payload.llm_config)
    try:
        if not payload.reject_all and not payload.rejected_item_keys:
            raise HTTPException(status_code=422, detail="rejected_item_keys is required when reject_all is false")
        logger.info(
            "[v3][route.reject] session=%s reject_all=%s rejected_keys=%s",
            session_id,
            bool(payload.reject_all),
            payload.rejected_item_keys,
        )
        return reject_changes(
            session_id=session_id,
            rejected_item_keys=payload.rejected_item_keys,
            reject_all=bool(payload.reject_all),
            suggestion_document_obj=payload.suggestion_document_obj,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"actions reject failed: {exc}")


@router.post("/agent/v3/sessions/{session_id}/rollback")
async def rollback(session_id: str, payload: V3RollbackRequest) -> Dict[str, Any]:
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    try:
        return rollback_changes(
            session_id=session_id,
            version_id=payload.version_id.strip(),
            note=payload.note.strip(),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"rollback failed: {exc}")


# ── Template alignment endpoints ──────────────────────────────────────


class TemplateInspectRequest(BaseModel):
    template_id: str = "swiss-single"
    session_id: str = ""
    resume_obj: Dict[str, Any] = Field(default_factory=dict)


class TemplateAlignRequest(BaseModel):
    template_id: str = "swiss-single"
    resume_obj: Dict[str, Any] = Field(default_factory=dict)
    operation: str = "auto_remap"
    # For edit_template_slot
    section: str = ""
    field_path: str = ""
    jinja2_expr: str = ""
    render_hint: str = "text"
    # For remap_json_field
    source_path: str = ""
    target_path: str = ""
    transform: str = "direct"


class TemplatePreviewRequest(BaseModel):
    template_id: str = "swiss-single"
    section: str
    resume_obj: Dict[str, Any] = Field(default_factory=dict)


@router.post("/agent/v3/template:inspect")
async def template_inspect(payload: TemplateInspectRequest) -> Dict[str, Any]:
    from src.services.template_editor import detect_mismatches, inspect_template
    try:
        template = inspect_template(payload.template_id)
        mismatches_list: List[Dict[str, Any]] = []
        if payload.resume_obj:
            report = detect_mismatches(payload.template_id, payload.resume_obj, payload.session_id)
            mismatches_list = [
                {
                    "kind": m.kind,
                    "json_path": m.json_path,
                    "template_path": m.template_path,
                    "json_type": m.json_type,
                    "severity": m.severity,
                    "suggested_fix": m.suggested_fix,
                    "auto_fixable": m.auto_fixable,
                }
                for m in report.mismatches
            ]
        return {
            "template_id": template.template_id,
            "sections": [
                {
                    "name": s.name,
                    "section_type": s.section_type,
                    "fields": [{"path": f.path, "render_hint": f.render_hint} for f in s.fields],
                    "item_fields": s.item_fields,
                }
                for s in template.sections
            ],
            "mismatches": mismatches_list,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"template inspect failed: {exc}")


@router.post("/agent/v3/template:align")
async def template_align(payload: TemplateAlignRequest) -> Dict[str, Any]:
    from src.services.template_editor import edit_template_slot, remap_json_field, auto_remap_json
    try:
        resume_obj = dict(payload.resume_obj or {})
        if payload.operation == "auto_remap":
            patched = auto_remap_json(resume_obj)
            return {"success": True, "operation": "auto_remap", "resume_obj": patched}
        elif payload.operation in ("add_field", "remove_field", "add_section", "remove_section"):
            result = edit_template_slot(
                template_id=payload.template_id,
                section=payload.section,
                operation=payload.operation,
                field_path=payload.field_path,
                jinja2_expr=payload.jinja2_expr or None,
                render_hint=payload.render_hint or "text",
            )
            return {
                "success": result.success,
                "operation": result.operation,
                "message": result.message,
                "affected_path": result.affected_path,
                "preview_html": result.preview_html,
            }
        elif payload.operation == "remap_json":
            patched = remap_json_field(
                resume_obj=resume_obj,
                source_path=payload.source_path,
                target_path=payload.target_path,
                transform=payload.transform or "direct",
            )
            return {"success": True, "operation": "remap_json", "resume_obj": patched}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown operation: {payload.operation}")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"template align failed: {exc}")


@router.post("/agent/v3/template:preview-section")
async def template_preview_section(payload: TemplatePreviewRequest) -> Dict[str, Any]:
    from src.services.template_editor import preview_section
    try:
        html = preview_section(
            template_id=payload.template_id,
            section=payload.section,
            resume_obj=dict(payload.resume_obj or {}),
        )
        return {"section": payload.section, "preview_html": html}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"template preview failed: {exc}")


@router.post("/agent/v3/template:export-latex")
async def template_export_latex(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Export resume as LaTeX source."""
    from src.services.layout_design.nodes.common import render_latex_template
    try:
        resume_obj = dict(payload.get("resume_obj", {}))
        active_style = dict(payload.get("active_style", {}))
        latex = render_latex_template(resume_obj, active_style)
        return {"latex": latex}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"latex export failed: {exc}")


@router.post("/agent/v3/template:render")
async def template_render(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Render resume JSON to paginated HTML using backend layout engine."""
    from src.services.layout_design.nodes.common import render_single_column_template_html
    try:
        resume_obj = dict(payload.get("resume_obj", {}))
        active_style = dict(payload.get("active_style", {}))
        page_count_mode = str(payload.get("page_count_mode", "single-page"))
        target_pages = int(payload.get("target_pages", 1))
        html = render_single_column_template_html(
            resume_obj,
            active_style,
            page_count_mode=page_count_mode,
            target_pages=target_pages,
        )
        return {"html": html}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"template render failed: {exc}")


# ── LaTeX PDF Generation ────────────────────────────────────────────


class LatexPdfRequest(BaseModel):
    resume_obj: Dict[str, Any] = Field(default_factory=dict)
    guidance: Dict[str, Any] = Field(default_factory=dict)
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    personal_info: Dict[str, Any] = Field(default_factory=dict)
    html_source: str = ""


@router.post("/latex/tex")
async def generate_latex_tex(payload: LatexPdfRequest) -> Dict[str, Any]:
    """Generate LaTeX source from resume data (no PDF compilation).

    Useful for debugging or for users who want to compile on Overleaf.
    """
    from src.services.latex_gen import render_tex

    try:
        resume_obj = dict(payload.resume_obj or {})
        guidance = dict(payload.guidance or {})
        sections = list(payload.sections or [])
        personal_info = dict(payload.personal_info or {}) or None
        html_source = str(payload.html_source or "")

        if not resume_obj:
            raise HTTPException(status_code=400, detail="resume_obj is required")

        tex = render_tex(resume_obj, guidance, sections, personal_info, html_source)
        return {"tex": tex}

    except Exception as exc:
        logger.error("[latex] tex generation error: %s", exc)
        raise HTTPException(status_code=500, detail=f"latex tex generation failed: {exc}")
