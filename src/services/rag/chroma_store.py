from typing import Any, Dict, List, Optional
from pathlib import Path

from .config import RagConfig


class ChromaStore:
    def __init__(self, config: Optional[RagConfig] = None) -> None:
        self.config = config or RagConfig()
        self._collection = None

    def _get_collection(self):
        if self._collection is not None:
            return self._collection

        try:
            import chromadb
            from chromadb.config import Settings
        except Exception as exc:
            raise RuntimeError("chromadb is not installed. Please install `chromadb`.") from exc

        Path(self.config.persist_path).mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(
            path=self.config.persist_path,
            settings=Settings(anonymized_telemetry=self.config.telemetry_enabled),
        )
        self._collection = client.get_or_create_collection(name=self.config.collection_name)
        return self._collection

    def upsert(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        if len(ids) != len(documents):
            raise ValueError("ids and documents length mismatch.")
        if metadatas is not None and len(metadatas) != len(documents):
            raise ValueError("metadatas and documents length mismatch.")
        collection = self._get_collection()
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    def query(
        self,
        query_text: str,
        top_k: Optional[int] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        collection = self._get_collection()
        result = collection.query(
            query_texts=[query_text],
            n_results=top_k or self.config.top_k,
            where=where,
        )
        return {
            "ids": (result.get("ids") or [[]])[0],
            "documents": (result.get("documents") or [[]])[0],
            "metadatas": (result.get("metadatas") or [[]])[0],
            "distances": (result.get("distances") or [[]])[0],
        }
