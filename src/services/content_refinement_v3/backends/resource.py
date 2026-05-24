"""V3-facing resource/import facade.

Resource routes are part of the current v3 UI surface. The concrete stores are
kept reusable here so the API layer no longer imports legacy v2 modules.
"""

from src.services.content_refinement_v3.domain.parser import (
    is_supported_document,
    parse_document_to_text,
)
from src.services.content_refinement_v3.storage.import_store import (
    delete_import_record,
    get_import_record,
    list_import_records,
    save_import_record,
)
from src.services.content_refinement_v3.storage.job_description_store import (
    delete_job_description,
    get_job_description,
    list_job_descriptions,
    save_job_description,
)
from src.services.content_refinement_v3.storage.recent_resume_store import (
    delete_recent_resume,
    get_recent_resume,
    list_recent_resumes,
    save_recent_resume,
    update_recent_resume_rendered_output,
)
from src.services.content_refinement_v3.pipeline.orchestrator import json_parse_document

__all__ = [
    "delete_import_record",
    "delete_job_description",
    "delete_recent_resume",
    "get_job_description",
    "get_import_record",
    "get_recent_resume",
    "is_supported_document",
    "json_parse_document",
    "list_job_descriptions",
    "list_import_records",
    "list_recent_resumes",
    "parse_document_to_text",
    "save_job_description",
    "save_import_record",
    "save_recent_resume",
    "update_recent_resume_rendered_output",
]
