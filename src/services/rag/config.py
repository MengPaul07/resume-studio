import os
from dataclasses import dataclass
from pathlib import Path


_BACKEND_SRC_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_FAISS_PATH = _BACKEND_SRC_DIR / "data" / "faiss"
_DEFAULT_JD_LIBRARY_PATH = _BACKEND_SRC_DIR / "data" / "rag" / "job_descriptions.json"


@dataclass
class RagConfig:
    persist_path: str = os.getenv("RAG_FAISS_PATH", str(_DEFAULT_FAISS_PATH))
    collection_name: str = os.getenv("RAG_COLLECTION_NAME", "resume_jd_library")
    job_description_library_path: str = os.getenv("RAG_JD_LIBRARY_PATH", str(_DEFAULT_JD_LIBRARY_PATH))
    top_k: int = int(os.getenv("RAG_TOP_K", "5"))
