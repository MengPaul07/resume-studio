"""Structured error classification for Resume Studio.

4 categories × 16 error codes. Every user-facing error gets a code
so the frontend can decide what to do: retry, guide the user, or alert.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):
    LLM = "llm"
    DATA = "data"
    INPUT = "input"
    SYS = "sys"


class ErrorCode(str, Enum):
    # ── LLM failures ──────────────────────────────────────
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    LLM_EMPTY_RESPONSE = "LLM_EMPTY_RESPONSE"
    LLM_MODEL_NOT_FOUND = "LLM_MODEL_NOT_FOUND"
    LLM_API_KEY_INVALID = "LLM_API_KEY_INVALID"
    LLM_CONTEXT_OVERFLOW = "LLM_CONTEXT_OVERFLOW"
    LLM_INSUFFICIENT_BALANCE = "LLM_INSUFFICIENT_BALANCE"

    # ── Data failures ─────────────────────────────────────
    DATA_DB_LOCKED = "DATA_DB_LOCKED"
    DATA_FILE_CORRUPT = "DATA_FILE_CORRUPT"
    DATA_INDEX_MISMATCH = "DATA_INDEX_MISMATCH"

    # ── Input failures ────────────────────────────────────
    INPUT_UNSUPPORTED_FORMAT = "INPUT_UNSUPPORTED_FORMAT"
    INPUT_MISSING_FIELD = "INPUT_MISSING_FIELD"
    INPUT_INVALID_PATH = "INPUT_INVALID_PATH"

    # ── System failures ───────────────────────────────────
    SYS_DISK_FULL = "SYS_DISK_FULL"
    SYS_MEMORY_LIMIT = "SYS_MEMORY_LIMIT"
    SYS_INTERNAL = "SYS_INTERNAL"

    @property
    def category(self) -> ErrorCategory:
        prefix = self.value.split("_")[0]
        return ErrorCategory(prefix.lower())

    @property
    def retryable(self) -> bool:
        return self in _RETRYABLE

    @property
    def user_message(self) -> str:
        return _USER_MESSAGES.get(self, "An unexpected error occurred.")


_RETRYABLE: set[ErrorCode] = {
    ErrorCode.LLM_TIMEOUT,
    ErrorCode.LLM_RATE_LIMITED,
    ErrorCode.DATA_DB_LOCKED,
}

_USER_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.LLM_TIMEOUT: "AI service timed out. Please try again.",
    ErrorCode.LLM_RATE_LIMITED: "Too many requests. Please wait a moment.",
    ErrorCode.LLM_EMPTY_RESPONSE: "AI returned an empty response. Try rephrasing.",
    ErrorCode.LLM_MODEL_NOT_FOUND: "Selected model not available. Fell back to default.",
    ErrorCode.LLM_API_KEY_INVALID: "API key is invalid. Check your settings.",
    ErrorCode.LLM_CONTEXT_OVERFLOW: "Conversation too long. Older messages truncated.",
    ErrorCode.LLM_INSUFFICIENT_BALANCE: "API balance exhausted. Please top up.",
    ErrorCode.DATA_DB_LOCKED: "Database busy. Operation will retry.",
    ErrorCode.DATA_FILE_CORRUPT: "Data file corrupted. Attempting recovery.",
    ErrorCode.DATA_INDEX_MISMATCH: "Data index out of sync. Auto-repairing.",
    ErrorCode.INPUT_UNSUPPORTED_FORMAT: "File format not supported. Use PDF or DOCX.",
    ErrorCode.INPUT_MISSING_FIELD: "Required field is missing.",
    ErrorCode.INPUT_INVALID_PATH: "Target field does not exist in resume.",
    ErrorCode.SYS_DISK_FULL: "Disk space is low. Please free up space.",
    ErrorCode.SYS_MEMORY_LIMIT: "Request too large. Try simplifying.",
    ErrorCode.SYS_INTERNAL: "Something went wrong. Please try again.",
}


class AppError(Exception):
    """Application-level error with structured metadata."""

    def __init__(
        self,
        code: ErrorCode,
        detail: str = "",
        *,
        retryable: bool | None = None,
        context: dict[str, Any] | None = None,
    ):
        self.code = code
        self.detail = detail or code.user_message
        self.retryable = retryable if retryable is not None else code.retryable
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code.value,
                "category": self.code.category.value,
                "detail": self.detail,
                "retryable": self.retryable,
            }
        }


# ── Convenience constructors ──────────────────────────────


def llm_timeout(msg: str = "") -> AppError:
    return AppError(ErrorCode.LLM_TIMEOUT, msg)


def llm_rate_limited(msg: str = "") -> AppError:
    return AppError(ErrorCode.LLM_RATE_LIMITED, msg)


def llm_empty_response(msg: str = "") -> AppError:
    return AppError(ErrorCode.LLM_EMPTY_RESPONSE, msg)


def llm_model_not_found(name: str) -> AppError:
    return AppError(ErrorCode.LLM_MODEL_NOT_FOUND, f"Model '{name}' not found")


def llm_api_key_invalid() -> AppError:
    return AppError(ErrorCode.LLM_API_KEY_INVALID)


def llm_context_overflow(current_tokens: int, limit: int) -> AppError:
    return AppError(
        ErrorCode.LLM_CONTEXT_OVERFLOW,
        f"Context overflow: {current_tokens}/{limit} tokens",
        context={"current_tokens": current_tokens, "limit": limit},
    )


def llm_insufficient_balance(provider: str = "") -> AppError:
    return AppError(ErrorCode.LLM_INSUFFICIENT_BALANCE, f"Balance exhausted on {provider}" if provider else "API balance exhausted")


def data_db_locked(table: str = "") -> AppError:
    return AppError(ErrorCode.DATA_DB_LOCKED, f"Database locked on {table}" if table else "Database locked", retryable=True)


def data_file_corrupt(path: str = "") -> AppError:
    return AppError(ErrorCode.DATA_FILE_CORRUPT, f"Corrupted file: {path}" if path else "Data file corrupted")


def input_missing_field(field: str) -> AppError:
    return AppError(ErrorCode.INPUT_MISSING_FIELD, f"'{field}' is required")


def input_invalid_path(path: str) -> AppError:
    return AppError(ErrorCode.INPUT_INVALID_PATH, f"Path '{path}' not found in resume")


def sys_internal(detail: str = "") -> AppError:
    return AppError(ErrorCode.SYS_INTERNAL, detail or "Internal error")
