from typing import Any, Dict, List, Optional

from .jd_repository import JdRepository
from .retriever import JdRetriever


class RagService:
    def __init__(
        self,
        repository: Optional[JdRepository] = None,
        retriever: Optional[JdRetriever] = None,
    ) -> None:
        self.repository = repository or JdRepository()
        self.retriever = retriever or JdRetriever(self.repository)

    def seed_jd_library(self, jd_items: List[Dict[str, Any]]) -> int:
        return self.repository.seed(jd_items)

    def retrieve_jd_context(
        self,
        target_role: str,
        language: str = "zh",
        top_k: int = 15,
    ) -> List[Dict[str, Any]]:
        return self.retriever.retrieve_for_role(
            target_role=target_role,
            language=language,
            top_k=top_k,
        )
