"""Tool registry — dict-based dispatch replacing if/elif chains."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from ._types import ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Dict-based tool dispatch with uniform error handling and timing."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., ToolResult]] = {}

    def register(self, name: str, fn: Callable[..., ToolResult]) -> None:
        self._tools[name] = fn

    def get(self, name: str) -> Callable[..., ToolResult] | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def execute(self, name: str, **kwargs: Any) -> ToolResult:
        fn = self._tools.get(name)
        if fn is None:
            return ToolResult(
                success=False,
                tool_name=name,
                data={},
                error=f"unknown tool: {name}",
            )
        started = time.perf_counter()
        try:
            result = fn(**kwargs)
        except Exception as exc:
            logger.exception("[ToolRegistry] %s failed: %s", name, exc)
            return ToolResult(
                success=False,
                tool_name=name,
                data={},
                error=str(exc),
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        if result.duration_ms == 0:
            result.duration_ms = duration_ms
        return result
