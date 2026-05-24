import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.services.build_llm import build_llm
from src.services.content_refinement_v3.backends.resource import (
    delete_import_record,
    delete_job_description,
    delete_recent_resume,
    get_job_description,
    get_import_record,
    get_recent_resume,
    is_supported_document,
    json_parse_document,
    list_job_descriptions,
    list_import_records,
    list_recent_resumes,
    parse_document_to_text,
    save_job_description,
    save_import_record,
    save_recent_resume,
    update_recent_resume_rendered_output,
)
from src.services.layout_design.service import run_layout_design
from src.utils.context import set_llm_config


router = APIRouter(tags=["AgentResources"])


class BaseResourceRequest(BaseModel):
    llm_config: Dict[str, Any] = Field(default_factory=dict)


class SaveRecentResumeRequest(BaseResourceRequest):
    resume_id: str = ""
    title: str = "Resume Draft"
    status: str = "ready"
    source: str = "builder"
    tags: List[str] = Field(default_factory=list)
    resume_obj: Dict[str, Any] = Field(default_factory=dict)
    output_markdown: str = ""
    output_html: str = ""
    prefer_llm_html: bool = False
    template_name: str = "modern_pro.html"
    layout_preferences: Dict[str, Any] = Field(default_factory=dict)


class RenderRecentResumeRequest(BaseResourceRequest):
    layout_preferences: Dict[str, Any] = Field(default_factory=dict)


class RunImportRequest(BaseResourceRequest):
    import_id: str = ""
    max_iterations: int = Field(default=2, ge=1, le=10)
    use_llm: bool = True
    layout_preferences: Dict[str, Any] = Field(default_factory=dict)


class SaveJobDescriptionRequest(BaseResourceRequest):
    job_description_id: str = ""
    title: str = "Job Description"
    content: str = ""


def _run_resume_pipeline_from_text(
    *,
    raw_text: str,
    layout_preferences: Dict[str, Any],
) -> Dict[str, Any]:
    parsed = json_parse_document(
        doc_type="resume",
        raw_input=raw_text,
        layout_preferences=layout_preferences,
    )
    raw_resume_obj = parsed.get("raw_document_obj", {}) if isinstance(parsed.get("raw_document_obj", {}), dict) else {}
    normalized_resume_obj = (
        parsed.get("normalized_document_obj", {})
        if isinstance(parsed.get("normalized_document_obj", {}), dict)
        else {}
    )
    from src.services.template_editor import auto_remap_json, detect_mismatches

    refined_resume_obj = normalized_resume_obj or raw_resume_obj
    refined_resume_obj = auto_remap_json(refined_resume_obj)

    return {
        "raw_resume_obj": raw_resume_obj,
        "suggestion_resume_obj": {"items": []},
        "refined_resume_obj": refined_resume_obj,
        "resume_obj": refined_resume_obj,
        "quality_report": {},
        "section_quality_map": {},
        "applied_changes": [],
        "design_spec": {},
        "output_markdown": "",
        "output_html": "",
        "parse_warning": parsed.get("parse_warning", ""),
    }


@router.post("/agent/test-llm")
async def test_llm_connectivity_route(payload: BaseResourceRequest) -> Dict[str, Any]:
    set_llm_config(payload.llm_config)
    started = time.perf_counter()
    try:
        llm = build_llm()
        resp = llm.invoke(
            [
                ("system", "You are a connectivity check assistant."),
                ("human", "reply with ok"),
            ]
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        preview = str(getattr(resp, "content", "") or "").strip().replace("\n", " ")
        if len(preview) > 300:
            preview = preview[:300]
        return {
            "ok": True,
            "model": str(getattr(llm, "model", "")),
            "latency_ms": latency_ms,
            "message": "LLM connectivity test succeeded.",
            "provider_response_preview": preview,
        }
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "model": str(payload.llm_config.get("model", "")),
                "latency_ms": latency_ms,
                "message": f"LLM connectivity test failed: {exc}",
                "provider_response_preview": "",
            },
        )


@router.post("/agent/import-file")
async def import_file_route(file: UploadFile = File(...)) -> Dict[str, Any]:
    file_name = file.filename or "resume"
    if not is_supported_document(file_name):
        raise HTTPException(status_code=422, detail="unsupported file type; supported: .pdf, .doc, .docx")

    suffix = Path(file_name).suffix.lower()
    tmp_path = ""
    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        raw_text = parse_document_to_text(tmp_path, use_llm_cleanup=False)
        if not str(raw_text or "").strip():
            raise HTTPException(status_code=422, detail="no text extracted from file")
        return save_import_record(file_name=file_name, raw_text=raw_text)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"import file failed: {exc}")
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass


@router.post("/agent/run-import")
async def run_import_route(payload: RunImportRequest) -> Dict[str, Any]:
    if not payload.import_id.strip():
        raise HTTPException(status_code=422, detail="import_id is required")
    if not payload.use_llm:
        raise HTTPException(status_code=400, detail="LLM execution is required for import build")

    item = get_import_record(payload.import_id.strip(), include_raw_text=True)
    if not item:
        raise HTTPException(status_code=404, detail="import record not found")
    raw_text = str(item.get("raw_text", "") or "").strip()
    if not raw_text:
        raise HTTPException(status_code=422, detail="import record has empty raw_text")

    set_llm_config(payload.llm_config)
    try:
        return _run_resume_pipeline_from_text(
            raw_text=raw_text,
            layout_preferences=payload.layout_preferences,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"build from import failed: {exc}")


@router.get("/agent/imports")
async def list_imports_route(limit: int = 50) -> Dict[str, Any]:
    items = list_import_records(limit=limit)
    return {"items": items}


@router.get("/agent/imports/{import_id}")
async def get_import_route(import_id: str, include_raw_text: bool = True) -> Dict[str, Any]:
    item = get_import_record(import_id, include_raw_text=include_raw_text)
    if not item:
        raise HTTPException(status_code=404, detail="import record not found")
    return item


@router.delete("/agent/imports/{import_id}")
async def delete_import_route(import_id: str) -> Dict[str, Any]:
    deleted = delete_import_record(import_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="import record not found")
    return {"ok": True}


@router.get("/agent/job-descriptions")
async def list_job_descriptions_route(limit: int = 50) -> Dict[str, Any]:
    return {"items": list_job_descriptions(limit=limit)}


@router.get("/agent/job-descriptions/{job_description_id}")
async def get_job_description_route(job_description_id: str, include_content: bool = True) -> Dict[str, Any]:
    item = get_job_description(job_description_id, include_content=include_content)
    if not item:
        raise HTTPException(status_code=404, detail="job description not found")
    return item


@router.post("/agent/job-descriptions/save")
async def save_job_description_route(payload: SaveJobDescriptionRequest) -> Dict[str, Any]:
    if not payload.content.strip():
        raise HTTPException(status_code=422, detail="content is required")
    try:
        return save_job_description(
            job_description_id=payload.job_description_id.strip(),
            title=payload.title,
            content=payload.content,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"save job description failed: {exc}")


@router.delete("/agent/job-descriptions/{job_description_id}")
async def delete_job_description_route(job_description_id: str) -> Dict[str, Any]:
    deleted = delete_job_description(job_description_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="job description not found")
    return {"ok": True}


@router.get("/agent/recent-resumes")
async def list_recent_resumes_route(limit: int = 20) -> Dict[str, Any]:
    items = list_recent_resumes(limit=limit)
    for item in items:
        if isinstance(item, dict) and "doc_type" not in item:
            item["doc_type"] = "resume"
    return {"items": items}


@router.get("/agent/recent-resumes/{resume_id}")
async def get_recent_resume_route(resume_id: str, include_payload: bool = True) -> Dict[str, Any]:
    item = get_recent_resume(resume_id, include_payload=include_payload)
    if not item:
        raise HTTPException(status_code=404, detail="recent resume not found")
    if "doc_type" not in item:
        item["doc_type"] = "resume"
    return item


@router.post("/agent/recent-resumes/save")
async def save_recent_resume_route(payload: SaveRecentResumeRequest) -> Dict[str, Any]:
    set_llm_config(payload.llm_config)
    try:
        item = save_recent_resume(
            resume_obj=payload.resume_obj,
            title=payload.title,
            tags=payload.tags,
            status=payload.status,
            source=payload.source,
            output_markdown=payload.output_markdown,
            output_html=payload.output_html,
            resume_id=payload.resume_id,
            prefer_llm_html=payload.prefer_llm_html,
            template_name=payload.template_name,
            layout_preferences=payload.layout_preferences,
        )
        item["doc_type"] = "resume"
        return item
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"save recent resume failed: {exc}")


@router.post("/agent/recent-resumes/{resume_id}/render")
async def render_recent_resume_route(resume_id: str, payload: RenderRecentResumeRequest) -> Dict[str, Any]:
    set_llm_config(payload.llm_config)
    existing = get_recent_resume(resume_id, include_payload=True)
    if not existing:
        raise HTTPException(status_code=404, detail="recent resume not found")

    resume_obj = existing.get("resume_obj", {})
    if not isinstance(resume_obj, dict) or not resume_obj:
        raise HTTPException(status_code=422, detail="recent resume has empty resume_obj")

    try:
        from src.services.template_editor import align_for_render

        template_name = str(existing.get("template_name", "") or "").strip()
        template_id = template_name.replace(".html", "").replace("_", "-") if template_name else "swiss-single"
        aligned = align_for_render(template_id=template_id, resume_obj=resume_obj, session_id=resume_id)
        resume_obj = aligned["resume_obj"]

        rendered = run_layout_design(
            resume_obj=resume_obj,
            layout_preferences=payload.layout_preferences,
            refined_resume_obj=resume_obj,
        )
        updated = update_recent_resume_rendered_output(
            resume_id=resume_id,
            output_html=str(rendered.get("output_html", "") or ""),
            output_markdown=str(rendered.get("output_markdown", "") or ""),
        )
        if not updated:
            raise HTTPException(status_code=404, detail="recent resume not found")
        updated["doc_type"] = "resume"
        updated["design_spec"] = rendered.get("design_spec", {})
        updated["alignment_report"] = aligned.get("alignment_report", {})
        return updated
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"render recent resume failed: {exc}")


@router.delete("/agent/recent-resumes/{resume_id}")
async def delete_recent_resume_route(resume_id: str) -> Dict[str, Any]:
    deleted = delete_recent_resume(resume_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="recent resume not found")
    return {"ok": True}
