from typing import Any, Dict, List, Optional


class JdReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3") -> None:
        self._model_name = model_name
        self._model: Any = None
        self._init_error: Optional[str] = None

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        if self._init_error is not None:
            return
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name)
        except Exception as exc:
            self._init_error = str(exc)

    @property
    def available(self) -> bool:
        self._ensure_model()
        return self._model is not None

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        self._ensure_model()

        if self._model is not None:
            return self._cross_encoder_rerank(query, candidates, top_k)
        return self._distance_fallback(candidates, top_k)

    def _cross_encoder_rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        pairs = [(query, str(c.get("text", ""))) for c in candidates]
        try:
            scores = self._model.predict(pairs, show_progress_bar=False)
        except Exception:
            return self._distance_fallback(candidates, top_k)

        for i, c in enumerate(candidates):
            c["rerank_score"] = float(scores[i]) if i < len(scores) else 0.0

        ranked = sorted(candidates, key=lambda c: c.get("rerank_score", 0.0), reverse=True)
        return ranked[:top_k]

    def _distance_fallback(
        self,
        candidates: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        ranked = sorted(candidates, key=lambda c: float(c.get("distance", 1.0) or 1.0))
        for c in ranked:
            c["rerank_score"] = 0.0
        return ranked[:top_k]
