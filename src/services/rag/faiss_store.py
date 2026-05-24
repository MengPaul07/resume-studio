"""FAISS + SQLite vector store — zero torch dependency, minimal footprint (~30MB)."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .config import RagConfig


class FaissStore:
    """FAISS-backed vector store with SQLite metadata, matching ChromaDB interface."""

    def __init__(self, config: Optional[RagConfig] = None) -> None:
        self.config = config or RagConfig()
        self._index = None
        self._conn = None
        self._embedder = None
        self._dim = None
        self._init_db()

    def _db_path(self) -> str:
        return str(Path(self.config.persist_path) / "faiss_index.db")

    def _init_db(self) -> None:
        Path(self.config.persist_path).mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path())
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT UNIQUE NOT NULL,
                document TEXT NOT NULL,
                metadata_json TEXT DEFAULT '{}',
                embedding BLOB NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS inverted_tags (
                key TEXT NOT NULL,       -- tag key, e.g. "company", "type", "role", "year"
                value TEXT NOT NULL,     -- tag value, e.g. "alibaba", "campus", "backend"
                doc_id TEXT NOT NULL,
                PRIMARY KEY (key, value, doc_id)
            )
        """)
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_key_value ON inverted_tags(key, value)")
        self._conn.commit()

    def _load_index(self) -> None:
        """Load FAISS index from SQLite BLOBs into memory."""
        import faiss  # type: ignore

        rows = self._conn.execute("SELECT embedding FROM embeddings ORDER BY rowid").fetchall()
        if not rows:
            self._index = faiss.IndexFlatIP(self.dim)
            return
        vectors = np.array([np.frombuffer(r[0], dtype=np.float32) for r in rows], dtype=np.float32)
        self._index = faiss.IndexFlatIP(self.dim)
        self._index.add(vectors)

    def _get_index(self):
        if self._index is None:
            self._load_index()
        return self._index

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Embed texts using fastembed (local ONNX, ~120MB, no API dependency)."""
        if self._embedder is None:
            from fastembed import TextEmbedding
            self._embedder = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
            # Auto-detect dimension from first embedding
            test = self._embedder.embed(["test"])
            self._dim = len(list(test)[0])
        return [e.tolist() for e in self._embedder.embed(texts)]

    @property
    def dim(self) -> int:
        if self._dim is None:
            self._embed(["dim probe"])
        return self._dim or 512

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

        embeddings = self._embed(documents)
        vectors = np.array(embeddings, dtype=np.float32)

        for doc_id, doc, meta, vec in zip(ids, documents, metadatas or [{}] * len(ids), vectors):
            meta_dict = meta or {}
            self._conn.execute(
                "INSERT OR REPLACE INTO embeddings (doc_id, document, metadata_json, embedding) VALUES (?, ?, ?, ?)",
                (doc_id, doc, json.dumps(meta_dict, ensure_ascii=False), vec.tobytes()),
            )
            self._clear_tags(doc_id)
            self._write_tags(doc_id, self._extract_tags(meta_dict))
        self._conn.commit()
        self._index = None  # Invalidate cache — rebuild on next query

    @staticmethod
    def _extract_tags(meta: Dict[str, Any]) -> List[tuple]:
        """Extract (key, value) tag pairs from JD metadata.
        Tag keys: company, type, role, year — plus any keyword list entries.
        """
        tags: List[tuple] = []
        for k in ("company", "recruitment_type", "type", "role_direction", "year"):
            v = meta.get(k, "")
            if v:
                tags.append((k, str(v).strip().lower()))
        # Also index individual keywords as searchable tags
        for kw in meta.get("keywords", []) or []:
            kw_str = str(kw).strip().lower()
            if kw_str:
                tags.append(("keyword", kw_str))
        return tags

    def _clear_tags(self, doc_id: str) -> None:
        self._conn.execute("DELETE FROM inverted_tags WHERE doc_id = ?", (doc_id,))

    def _write_tags(self, doc_id: str, tags: List[tuple]) -> None:
        self._conn.executemany(
            "INSERT OR IGNORE INTO inverted_tags (key, value, doc_id) VALUES (?, ?, ?)",
            [(k, v, doc_id) for k, v in tags],
        )

    def clear(self) -> None:
        """Delete all embeddings from the store."""
        self._conn.execute("DELETE FROM embeddings")
        self._conn.commit()
        self._index = None

    def query_with_filter(
        self,
        query_text: str,
        top_k: int = 10,
        filters: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Query with inverted-index filter. filters = {key: value, ...} maps tag keys
        to required values. All keys must match (AND logic). Docs matching ALL filters
        are selected via inverted index, then FAISS searches within that subset.
        """
        k = min(top_k, 50)
        filters = filters or {}

        # 1. Use inverted index to get candidate doc_ids
        if filters:
            clauses = []
            params: list = []
            for key, value in filters.items():
                clauses.append("(key = ? AND value = ?)")
                params.extend([key, str(value).strip().lower()])
            n_filters = len(filters)
            sql = f"""
                SELECT doc_id FROM inverted_tags
                WHERE {' OR '.join(clauses)}
                GROUP BY doc_id HAVING COUNT(DISTINCT key) = ?
            """
            params.append(n_filters)
            rows = self._conn.execute(sql, params).fetchall()
            filtered_ids = {r[0] for r in rows}
            if not filtered_ids:
                return {"ids": [], "documents": [], "metadatas": [], "distances": []}
        else:
            filtered_ids = None

        # 2. Load matching embeddings into temp FAISS index
        if filtered_ids is not None:
            placeholders = ",".join(["?"] * len(filtered_ids))
            sql = f"SELECT rowid, doc_id, document, metadata_json, embedding FROM embeddings WHERE doc_id IN ({placeholders}) ORDER BY rowid"
            rows = self._conn.execute(sql, list(filtered_ids)).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT rowid, doc_id, document, metadata_json, embedding FROM embeddings ORDER BY rowid"
            ).fetchall()
        if not rows:
            return {"ids": [], "documents": [], "metadatas": [], "distances": []}

        vectors = np.array([np.frombuffer(r[4], dtype=np.float32) for r in rows], dtype=np.float32)
        import faiss
        temp = faiss.IndexFlatIP(self.dim)
        temp.add(vectors)

        # 3. FAISS search within filtered set
        qv = np.array(self._embed([query_text])[0], dtype=np.float32).reshape(1, -1)
        D, I = temp.search(qv, min(k, len(rows)))
        results = []
        for dist, idx in zip(D[0], I[0]):
            if idx >= 0 and idx < len(rows):
                r = rows[idx]
                results.append((float(dist), r[1], r[2], json.loads(r[3])))
        return {
            "ids": [r[1] for r in results],
            "documents": [r[2] for r in results],
            "metadatas": [r[3] for r in results],
            "distances": [r[0] for r in results],
        }

    def list_all(self) -> Dict[str, Any]:
        """Return all stored documents without vector search."""
        rows = self._conn.execute(
            "SELECT doc_id, document, metadata_json FROM embeddings ORDER BY rowid"
        ).fetchall()
        return {
            "ids": [r[0] for r in rows],
            "documents": [r[1] for r in rows],
            "metadatas": [json.loads(r[2]) for r in rows],
            "distances": [0.0] * len(rows),
        }

    def query(
        self,
        query_text: str,
        top_k: Optional[int] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        k = top_k or self.config.top_k
        index = self._get_index()

        # Get document count and build id map
        total = self._conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        if total == 0:
            return {"ids": [], "documents": [], "metadatas": [], "distances": []}

        # Apply metadata filter
        if where:
            # Simple $and filter support
            conditions = where.get("$and", [])
            query_sql = "SELECT rowid, doc_id, document, metadata_json, embedding FROM embeddings"
            params: list = []
            if conditions:
                clauses = []
                for cond in conditions:
                    for ck, cv in cond.items():
                        clauses.append(f"json_extract(metadata_json, '$.{ck}') = ?")
                        params.append(str(cv))
                query_sql += " WHERE " + " AND ".join(clauses)
            rows = self._conn.execute(query_sql, params).fetchall()
            if not rows:
                return {"ids": [], "documents": [], "metadatas": [], "distances": []}
            filtered_vectors = np.array(
                [np.frombuffer(r[4], dtype=np.float32) for r in rows], dtype=np.float32
            )
            temp_index = __import__("faiss").IndexFlatIP(self.dim)
            temp_index.add(filtered_vectors)
            query_vec = np.array(self._embed([query_text])[0], dtype=np.float32).reshape(1, -1)
            D, I = temp_index.search(query_vec, min(k, len(rows)))
            results = []
            for dist, idx in zip(D[0], I[0]):
                if idx >= 0 and idx < len(rows):
                    r = rows[idx]
                    results.append((float(dist), r[1], r[2], json.loads(r[3])))
        else:
            query_vec = np.array(self._embed([query_text])[0], dtype=np.float32).reshape(1, -1)
            k_actual = min(k, total)
            D, I = index.search(query_vec, k_actual)
            id_map = self._conn.execute("SELECT doc_id, document, metadata_json FROM embeddings ORDER BY rowid").fetchall()
            results = []
            for dist, idx in zip(D[0], I[0]):
                if idx >= 0 and idx < len(id_map):
                    r = id_map[idx]
                    results.append((float(dist), r[0], r[1], json.loads(r[2])))

        return {
            "ids": [r[1] for r in results],
            "documents": [r[2] for r in results],
            "metadatas": [r[3] for r in results],
            "distances": [r[0] for r in results],
        }
