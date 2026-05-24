"""Pure utility functions — text diff, numbers, paths, intent helpers."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List


def _to_display_text(value: Any) -> str:
    def _format_structured(v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, (int, float, bool)):
            return str(v)
        if isinstance(v, str):
            text = v.strip()
            if not text:
                return ""
            if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
                try:
                    parsed = json.loads(text)
                    return _format_structured(parsed)
                except Exception:
                    return text
            return text
        if isinstance(v, list):
            lines = [_format_structured(item) for item in v]
            lines = [line for line in lines if line]
            return "\n".join(lines)
        if isinstance(v, dict):
            ordered_keys = ["institution", "degree", "years", "title", "company", "role", "name", "description"]
            parts: List[str] = []
            used = set()
            for key in ordered_keys:
                if key in v:
                    used.add(key)
                    part = _format_structured(v.get(key))
                    if part:
                        parts.append(part)
            for key, raw in v.items():
                if key in used:
                    continue
                part = _format_structured(raw)
                if part:
                    parts.append(part)
            return " | ".join(parts) if parts else ""
        try:
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return str(v)

    return _format_structured(value)


def _canonical_semantic_text(value: Any) -> str:
    text = _to_display_text(value).lower()
    if not text:
        return ""
    return re.sub(r"[`~!@#$%^&*()_+=\[\]{}\\|;:'\",.<>/?\-，。！？；：、“”‘’（）【】《》\s]+", "", text)


def _extract_numbers(text: str) -> List[str]:
    return re.findall(r"\d+(?:\.\d+)?%?", str(text or ""))


def _looks_like_phone_or_email(text: str) -> bool:
    raw = str(text or "")
    if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", raw):
        return True
    if re.search(r"(?:\+?\d[\d\-\s]{7,}\d)", raw):
        return True
    return False


def _is_format_only_candidate(item: Dict[str, Any]) -> bool:
    before_raw = item.get("current_value_raw", item.get("current_value"))
    after_raw = item.get("refined_value_raw", item.get("suggested_value_raw", item.get("suggested_value")))
    before_text = _to_display_text(before_raw)
    after_text = _to_display_text(after_raw)
    if not before_text and not after_text:
        return True
    if before_text == after_text:
        return True
    return _canonical_semantic_text(before_text) == _canonical_semantic_text(after_text)


def _is_fact_sensitive_change(item: Dict[str, Any]) -> bool:
    before_text = _to_display_text(item.get("current_value_raw", item.get("current_value")))
    after_text = _to_display_text(
        item.get("refined_text", item.get("refined_value_raw", item.get("suggested_value_raw", item.get("suggested_value"))))
    )
    if not before_text and not after_text:
        return False

    # Path-based: only flag number/date changes on fields that are inherently factual
    path = str(item.get("path", "")).strip().lower()
    fact_sensitive_paths = [
        r"personalinfo\.name",
        r"personalinfo\.email",
        r"personalinfo\.phone",
        r"personalinfo\.location",
        r"personalinfo\.linkedin",
        r"personalinfo\.github",
        r"\.years$",
        r"\.gpa",
        r"\.institution",
        r"\.degree",
    ]
    is_fact_field = any(re.search(pattern, path) for pattern in fact_sensitive_paths)

    if is_fact_field:
        if _extract_numbers(before_text) != _extract_numbers(after_text):
            return True

        date_like = re.compile(r"(?:19|20)\d{2}[./-]?\d{0,2}[./-]?\d{0,2}")
        before_dates = date_like.findall(before_text)
        after_dates = date_like.findall(after_text)
        if before_dates != after_dates:
            return True

        if _looks_like_phone_or_email(before_text) or _looks_like_phone_or_email(after_text):
            return _canonical_semantic_text(before_text) != _canonical_semantic_text(after_text)

        return _canonical_semantic_text(before_text) != _canonical_semantic_text(after_text)

    # Content fields (summary, description, skills, etc.): number/date changes alone
    # are not fact-sensitive — they may be restructured from context for impact.
    # Still flag explicit phone/email changes even in content fields.
    if _looks_like_phone_or_email(before_text) or _looks_like_phone_or_email(after_text):
        return _canonical_semantic_text(before_text) != _canonical_semantic_text(after_text)

    return False


def _tokenize_diff_text(source: str) -> List[str]:
    tokens: List[str] = []
    buffer = ""

    def _is_cjk(ch: str) -> bool:
        return bool(re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", ch))

    for ch in str(source or ""):
        if _is_cjk(ch) or ch.isspace():
            if buffer:
                tokens.append(buffer)
                buffer = ""
            tokens.append(ch)
            continue
        buffer += ch
    if buffer:
        tokens.append(buffer)
    return tokens


def _compute_inline_diff(old_text: str, new_text: str) -> List[Dict[str, str]]:
    a = _tokenize_diff_text(old_text)
    b = _tokenize_diff_text(new_text)
    n = len(a)
    m = len(b)
    dp = [[0 for _ in range(m + 1)] for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            dp[i][j] = dp[i + 1][j + 1] + 1 if a[i] == b[j] else max(dp[i + 1][j], dp[i][j + 1])

    result: List[Dict[str, str]] = []
    i = 0
    j = 0
    while i < n and j < m:
        if a[i] == b[j]:
            result.append({"type": "same", "text": a[i]})
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            result.append({"type": "remove", "text": a[i]})
            i += 1
        else:
            result.append({"type": "add", "text": b[j]})
            j += 1
    while i < n:
        result.append({"type": "remove", "text": a[i]})
        i += 1
    while j < m:
        result.append({"type": "add", "text": b[j]})
        j += 1

    merged: List[Dict[str, str]] = []
    for item in result:
        if merged and merged[-1].get("type") == item.get("type"):
            merged[-1]["text"] = f"{merged[-1].get('text', '')}{item.get('text', '')}"
        else:
            merged.append(dict(item))
    return merged


def _build_diff_payload(item: Dict[str, Any]) -> Dict[str, Any]:
    before_text = _to_display_text(item.get("current_value_raw", item.get("current_value")))
    after_text = _to_display_text(
        item.get("refined_text", item.get("refined_value_raw", item.get("suggested_value_raw", item.get("suggested_value"))))
    )
    chunks = _compute_inline_diff(before_text, after_text)
    return {
        "diff_type": "text",
        "before_text": before_text,
        "after_text": after_text,
        "chunks": chunks,
    }


def _infer_scope_from_message(message: str) -> str:
    text = str(message or "").strip().lower()
    if not text:
        return ""
    mapping = [
        ("personalInfo", [r"phone", r"email", r"contact", r"name", r"手机号", r"电话", r"邮箱", r"联系方式", r"姓名"]),
        ("summary", [r"summary", r"总结", r"摘要", r"自我评价"]),
        ("education", [r"education", r"教育", r"学历", r"学校"]),
        ("workExperience", [r"work", r"experience", r"工作", r"经历"]),
        ("personalProjects", [r"project", r"projects", r"项目", r"实习项目", r"个人项目"]),
        ("research", [r"research", r"科研", r"研究", r"论文", r"实验室", r"publication", r"课题"]),
        ("additional", [r"skill", r"skills", r"证书", r"语言", r"awards", r"获奖", r"技术栈", r"编程", r"技能"]),
    ]
    for scope, patterns in mapping:
        for pattern in patterns:
            if re.search(pattern, text):
                return scope
    return ""


def _is_global_edit_intent(message: str) -> bool:
    text = str(message or "").strip().lower()
    if not text:
        return False
    global_tokens = [
        "整体",
        "全局",
        "全篇",
        "整份",
        "全文",
        "整份简历",
        "overall",
        "entire",
        "full resume",
    ]
    return any(token in text for token in global_tokens)


def _is_analysis_only_intent(message: str) -> bool:
    text = str(message or "").strip().lower()
    if not text:
        return False
    has_analyze = any(token in text for token in ["analy", "review", "assess", "分析", "评估", "点评"])
    has_no_edit = any(token in text for token in ["don't modify", "do not modify", "不修改", "不要修改", "别修改"])
    return has_analyze and has_no_edit


def _is_edit_intent(message: str) -> bool:
    text = str(message or "").strip().lower()
    if not text:
        return False
    if _is_analysis_only_intent(text):
        return False
    edit_tokens = [
        "modify",
        "revise",
        "rewrite",
        "refine",
        "optimize",
        "improve",
        "update",
        "add",
        "change",
        "润色",
        "优化",
        "修改",
        "改",
        "改写",
        "强调",
        "调整",
        "补充",
        "增加",
        "添加",
    ]
    return any(token in text for token in edit_tokens)


def _is_fact_edit_intent(message: str) -> bool:
    text = str(message or "").strip().lower()
    if not text:
        return False
    fact_tokens = [
        "phone",
        "email",
        "date",
        "salary",
        "绩效",
        "比例",
        "百分比",
        "手机号",
        "邮箱",
        "日期",
        "人数",
        "gpa",
    ]
    return any(token in text for token in fact_tokens)


def _tokenize_path(path: str) -> List[str | int]:
    tokens: List[str | int] = []
    for part in str(path or "").split("."):
        if not part:
            continue
        key_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)", part)
        if key_match:
            tokens.append(key_match.group(1))
        for idx in re.findall(r"\[(\d+)\]", part):
            tokens.append(int(idx))
    return tokens


def _set_by_path(obj: Any, path: str, value: Any) -> bool:
    tokens = _tokenize_path(path)
    if not tokens or not isinstance(obj, dict):
        return False

    current: Any = obj
    for index, token in enumerate(tokens[:-1]):
        next_token = tokens[index + 1]
        if isinstance(token, str):
            if not isinstance(current, dict):
                return False
            if token not in current or not isinstance(current[token], (dict, list)):
                current[token] = [] if isinstance(next_token, int) else {}
            current = current[token]
            continue

        if not isinstance(current, list) or token < 0:
            return False
        if token > len(current):
            return False
        if token == len(current):
            current.append([] if isinstance(next_token, int) else {})
        if not isinstance(current[token], (dict, list)):
            current[token] = [] if isinstance(next_token, int) else {}
        current = current[token]

    last = tokens[-1]
    if isinstance(last, str):
        if not isinstance(current, dict):
            return False
        current[last] = value
        return True

    if not isinstance(current, list) or last < 0:
        return False
    if last > len(current):
        return False
    if last == len(current):
        current.append(value)
        return True
    current[last] = value
    return True


def _delete_by_path(obj: Any, path: str) -> bool:
    """Delete a key from a dict or an element from a list at the given path."""
    tokens = _tokenize_path(path)
    if not tokens or not isinstance(obj, dict):
        return False

    current: Any = obj
    for token in tokens[:-1]:
        if isinstance(token, str):
            if not isinstance(current, dict) or token not in current:
                return False
            current = current[token]
        elif isinstance(token, int):
            if not isinstance(current, list) or token >= len(current) or token < 0:
                return False
            current = current[token]
        else:
            return False

    last = tokens[-1]
    if isinstance(last, str):
        if not isinstance(current, dict) or last not in current:
            return False
        del current[last]
        return True
    if isinstance(last, int):
        if not isinstance(current, list) or last >= len(current) or last < 0:
            return False
        del current[last]
        return True
    return False


def _make_item_key(item: Dict[str, Any]) -> str:
    path = str(item.get("path", "")).strip()
    option_id = str(item.get("option_id", "")).strip() or "default"
    return f"{path}::{option_id}" if path else ""

