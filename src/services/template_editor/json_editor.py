"""JSON field manipulation: rename, restructure, and transform fields."""

from copy import deepcopy
from typing import Any, Dict


def remap_json_field(
    resume_obj: Dict[str, Any],
    source_path: str,
    target_path: str,
    transform: str = "direct",
) -> Dict[str, Any]:
    """
    Rename or restructure a field in the resume JSON.

    transform modes:
      - "direct": move value as-is
      - "split_to_list": split comma-separated string into list
      - "wrap_in_array": wrap scalar value in a single-element array
      - "join_list": join list items into newline-separated string
    """
    patched = deepcopy(resume_obj)

    # Read source value
    src_value = _get_by_path(patched, source_path)
    if src_value is None:
        return patched

    # Apply transform
    if transform == "split_to_list" and isinstance(src_value, str):
        src_value = [item.strip() for item in src_value.replace("，", ",").split(",") if item.strip()]
    elif transform == "wrap_in_array":
        src_value = [src_value]
    elif transform == "join_list" and isinstance(src_value, list):
        src_value = "\n".join(str(v) for v in src_value)

    # Write to target
    _set_by_path(patched, target_path, src_value)

    return patched


def _get_by_path(obj: Any, path: str) -> Any:
    import re

    tokens = _tokenize_path(path)
    cur = obj
    for token in tokens:
        if isinstance(token, int):
            if not isinstance(cur, list) or token >= len(cur):
                return None
            cur = cur[token]
        elif isinstance(cur, dict):
            cur = cur.get(token)
            if cur is None:
                return None
        else:
            return None
    return cur


def _set_by_path(obj: Any, path: str, value: Any) -> bool:
    tokens = _tokenize_path(path)
    if not tokens:
        return False
    cur = obj
    for token in tokens[:-1]:
        if isinstance(token, int):
            if not isinstance(cur, list) or token >= len(cur):
                return False
            cur = cur[token]
        elif isinstance(cur, dict):
            if token not in cur:
                cur[token] = {}
            cur = cur[token]
        else:
            return False
    last = tokens[-1]
    if isinstance(last, int):
        if not isinstance(cur, list) or last >= len(cur):
            return False
        cur[last] = value
        return True
    if not isinstance(cur, dict):
        return False
    cur[last] = value
    return True


def _tokenize_path(path: str):
    import re

    tokens = []
    for part in str(path or "").split("."):
        if not part:
            continue
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)", part)
        if m:
            tokens.append(m.group(1))
        for idx in re.findall(r"\[(\d+)\]", part):
            tokens.append(int(idx))
    return tokens
