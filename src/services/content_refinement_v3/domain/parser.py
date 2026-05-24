from pathlib import Path

try:
    from ...build_llm import build_llm
except Exception:
    from build_llm import build_llm


# Single source of truth for document import support.
SUPPORTED_DOC_EXTENSIONS = (".pdf", ".doc", ".docx")


def is_supported_document(file_name: str) -> bool:
    suffix = Path(file_name or "").suffix.lower()
    return suffix in SUPPORTED_DOC_EXTENSIONS


def _extract_raw_text(file_path: str, ext: str) -> str:
    del ext  # reserved for future extension-specific handling
    from markitdown import MarkItDown

    return MarkItDown(enable_plugins=False).convert(file_path).text_content.strip()


def parse_document_to_text(file_path: str, use_llm_cleanup: bool = True) -> str:
    path = Path(file_path)
    raw_text = _extract_raw_text(file_path, path.suffix.lower())
    llm = build_llm() if use_llm_cleanup else None

    if not llm or not raw_text:
        return raw_text

    response = llm.invoke(
        [
            (
                "system",
                "You clean text extracted from resumes. Fix broken lines and OCR noise while preserving facts.",
            ),
            ("human", f"Please clean this extracted text:\n\n{raw_text}"),
        ]
    )
    return getattr(response, "content", raw_text)
