from typing import Any, Dict, List

from .config import RagConfig


def get_job_description_library_path() -> str:
    return RagConfig().job_description_library_path


def job_description_schema_template() -> Dict[str, Any]:
    return {
        "version": "jd_library.v1",
        "language": "zh",
        "items": [
            {
                "id": "jd_example_001",
                "title": "人力资源专员",
                "company": "示例公司",
                "location": "",
                "employment_type": "full_time",
                "seniority": "mid",
                "keywords": [
                    "招聘",
                    "绩效",
                    "员工关系",
                    "数据分析",
                ],
                "requirements": [
                    "3年以上人力资源相关经验",
                    "熟悉劳动法与用工合规",
                ],
                "responsibilities": [
                    "负责招聘全流程与渠道维护",
                    "输出月度人力数据分析报告",
                ],
                "preferred": [
                    "有项目管理经验优先",
                ],
                "notes": "用于 RAG 检索的 JD 结构化字段，可按需扩展。",
                "metadata": {
                    "source": "manual_file",
                    "role": "hr_specialist",
                    "section": "workExperience",
                    "path_key": "workExperience.description",
                    "lang": "zh",
                },
            }
        ],
    }


def flatten_job_description_item_for_rag(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    item_id = str(item.get("id", "")).strip() or "jd_item"
    role = str(((item.get("metadata", {}) or {}).get("role", ""))).strip()
    lang = str(((item.get("metadata", {}) or {}).get("lang", ""))).strip() or "zh"
    section = str(((item.get("metadata", {}) or {}).get("section", ""))).strip() or "workExperience"
    path_key = str(((item.get("metadata", {}) or {}).get("path_key", ""))).strip() or "workExperience.description"
    title = str(item.get("title", "")).strip()
    company = str(item.get("company", "")).strip()

    rows: List[Dict[str, Any]] = []
    field_keys = [
        "keywords",
        "requirements",
        "responsibilities",
        "preferred",
    ]
    for field_key in field_keys:
        values = item.get(field_key, [])
        if not isinstance(values, list):
            continue
        for idx, value in enumerate(values):
            text = str(value or "").strip()
            if not text:
                continue
            rows.append(
                {
                    "id": f"{item_id}:{field_key}:{idx}",
                    "text": text,
                    "metadata": {
                        "source": "jd_library",
                        "source_id": item_id,
                        "title": title,
                        "company": company,
                        "role": role,
                        "lang": lang,
                        "section": section,
                        "path_key": path_key,
                        "field": field_key,
                    },
                }
            )
    return rows
