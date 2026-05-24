from typing import Any, Dict, List, Optional

from .jd_repository import JdRepository


class JdRetriever:
    def __init__(self, repository: Optional[JdRepository] = None) -> None:
        self.repository = repository or JdRepository()

    def retrieve_for_role(
        self,
        target_role: str,
        language: str = "zh",
        top_k: int = 15,
    ) -> List[Dict[str, Any]]:
        if not target_role.strip():
            return []
        return self._dedup(
            self.repository.query(
                target_role=target_role,
                language=language,
                top_k=top_k,
            )
        )

    @staticmethod
    def _dedup(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen: set = set()
        unique: List[Dict[str, Any]] = []
        for c in candidates:
            key = str(c.get("text", "")).strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(c)
        return unique
