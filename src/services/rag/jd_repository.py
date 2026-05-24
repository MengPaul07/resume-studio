from typing import Any, Dict, List, Optional

from .faiss_store import FaissStore
from .job_description_schema import flatten_job_description_item_for_rag


class JdRepository:
	def __init__(self, store: Optional[FaissStore] = None) -> None:
		self.store = store or FaissStore()

	def _jd_to_text(self, item: Dict[str, Any]) -> str:
		parts = [item.get("title", "")]
		parts.append(f"{item.get('company', '')} | {item.get('location', '')} | {item.get('type', '')}{item.get('year', '')}")
		parts.append(f"类别: {item.get('category', '')}")
		url = item.get("url", "")
		if url:
			parts.append(f"链接: {url}")
		kw = item.get("keywords", [])
		if kw:
			parts.append(f"关键词: {', '.join(kw)}")
		resp = item.get("responsibilities", [])
		if resp:
			parts.append("职责: " + "; ".join(resp))
		reqs = item.get("requirements", [])
		if reqs:
			parts.append("要求: " + "; ".join(reqs))
		return "\n".join(parts)

	def seed(self, jd_items: List[Dict[str, Any]]) -> int:
		rows: List[Dict[str, Any]] = []
		for item in jd_items:
			meta = dict(item.get("metadata", {}))
			for key in ("title", "company", "location", "category", "url"):
				value = str(item.get(key, "")).strip()
				if value and not meta.get(key):
					meta[key] = value
			if not meta.get("company"):
				meta["company"] = str(item.get("company", "")).strip()
			jd_type = str(item.get("type", "")).strip()
			if "实习" in jd_type:
				meta["recruitment_type"] = "intern"
			elif "校招" in jd_type:
				meta["recruitment_type"] = "campus"
			elif "社招" in jd_type:
				meta["recruitment_type"] = "experienced"
			if jd_type:
				meta["type"] = jd_type
			category = str(item.get("category", "")).lower()
			title = str(item.get("title", "")).lower()
			search_text = category + " " + title
			ROLE_MAP = {
				"backend": ["后端", "后台", "服务端", "backend", "back-end"],
				"frontend": ["前端", "frontend", "front-end"],
				"algorithm": ["算法", "algorithm", "machine learning", "ai", "人工智能"],
				"product": ["产品", "product"],
				"data": ["数据", "大数据", "data"],
				"embedded": ["嵌入式", "embedded", "硬件"],
				"security": ["安全", "security"],
				"mobile": ["移动端", "客户端", "ios", "android", "mobile"],
				"testing": ["测试", "test", "qa"],
				"devops": ["运维", "devops", "sre", "基础设施", "infrastructure"],
			}
			for direction, terms in ROLE_MAP.items():
				if any(t in search_text for t in terms):
					meta["role_direction"] = direction
					break
			y = item.get("year", "")
			if y:
				meta["year"] = str(y)
			rows.append({
				"id": item.get("id", ""),
				"text": self._jd_to_text(item),
				"metadata": meta,
			})
		if not rows:
			return 0
		self.store.upsert(
			ids=[r["id"] for r in rows],
			documents=[r["text"] for r in rows],
			metadatas=[r["metadata"] for r in rows],
		)
		return len(rows)

	def query(
		self,
		target_role: str,
		top_k: int = 10,
		filters: Optional[Dict[str, str]] = None,
	) -> List[Dict[str, Any]]:
		result = self.store.query_with_filter(
			query_text=target_role,
			top_k=top_k,
			filters=filters,
		)

		rows: List[Dict[str, Any]] = []
		for i, doc in enumerate(result.get("documents", [])):
			rows.append({
				"id": (result.get("ids") or [None] * len(result.get("documents", [])))[i],
				"text": doc,
				"metadata": (result.get("metadatas") or [None] * len(result.get("documents", [])))[i],
				"distance": (result.get("distances") or [None] * len(result.get("documents", [])))[i],
			})
		return rows
