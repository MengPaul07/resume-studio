from dataclasses import dataclass
import os
from typing import Any, Dict, List, Sequence, Tuple, Union

from dotenv import load_dotenv
from src.errors import llm_api_key_invalid
from src.utils.context import get_llm_config

try:
    from litellm import completion
except Exception:
    completion = None  # type: ignore

load_dotenv()

MessageInput = Union[Tuple[str, str], Dict[str, str]]


@dataclass
class LiteLLMResponse:
    content: str
    tool_calls: list | None = None


class LiteLLMAdapter:
    def __init__(
        self,
        model: str,
        api_key: str,
        api_base: str = "",
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> None:
        self.model = self._normalize_model(model)
        self.api_key = api_key
        self.api_base = api_base
        self.temperature = temperature
        self.max_tokens = self._clamp_max_tokens(max_tokens)

    @staticmethod
    def _clamp_max_tokens(value: int) -> int:
        try:
            parsed = int(value)
        except Exception:
            parsed = 2048
        return max(1, min(parsed, 8192))

    @staticmethod
    def _normalize_role(role: str) -> str:
        role = (role or "").strip().lower()
        if role == "human":
            return "user"
        if role in {"system", "assistant", "user"}:
            return role
        return "user"

    @staticmethod
    def _normalize_model(model: str) -> str:
        m = (model or "").strip()
        if "/" in m:
            return m
        if m.startswith("ollama:"):
            return f"ollama/{m.split(':', 1)[1]}"
        if m.startswith("gpt-") or m.startswith("o1") or m.startswith("o3") or m.startswith("o4"):
            return f"openai/{m}"
        if m.startswith("claude"):
            return f"anthropic/{m}"
        if m.startswith("gemini"):
            return f"gemini/{m}"
        if m.startswith("deepseek"):
            return f"deepseek/{m}"
        if m.startswith("llama") or m.startswith("qwen") or m.startswith("mistral"):
            return f"ollama/{m}"
        return m

    def _normalize_messages(self, messages: Sequence[MessageInput]) -> List[Dict[str, str]]:
        normalized: List[Dict[str, str]] = []
        for item in messages:
            if isinstance(item, tuple) and len(item) == 2:
                role, content = item
                normalized.append({"role": self._normalize_role(role), "content": str(content)})
                continue
            if isinstance(item, dict):
                role = self._normalize_role(str(item.get("role", "user")))
                content = str(item.get("content", ""))
                normalized.append({"role": role, "content": content})
                continue
            raise ValueError("Invalid message format for LLM invoke.")
        return normalized

    def invoke(self, messages: Sequence[MessageInput],
               tools: list[dict] | None = None,
               tool_choice: str = "auto",
               response_format: dict | None = None) -> LiteLLMResponse:
        if completion is None:
            raise RuntimeError("Missing dependency: litellm")

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": self._normalize_messages(messages),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": 120,
        }
        if self.api_key:
            payload["api_key"] = self.api_key
        if self.api_base:
            payload["api_base"] = self.api_base
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        if response_format:
            payload["response_format"] = response_format

        resp = completion(**payload)
        msg = resp.choices[0].message
        content = msg.content or ""
        tool_calls = getattr(msg, "tool_calls", None) or None
        return LiteLLMResponse(content=content, tool_calls=tool_calls)


def build_llm() -> LiteLLMAdapter:
    config = get_llm_config()

    raw_model = (config.get("model") or os.getenv("LLM_MODEL") or "").strip()
    normalized_model = LiteLLMAdapter._normalize_model(raw_model or "deepseek-chat")
    is_ollama = normalized_model.startswith("ollama/")

    api_key = str(config.get("api_key") or "").strip()
    if not api_key:
        api_key = os.getenv("API_KEY", "").strip()
    if not api_key and not is_ollama:
        raise llm_api_key_invalid()

    model = raw_model or "deepseek-chat"
    base_url = str(config.get("api_base") or "").strip()
    if not base_url:
        base_url = os.getenv("API_BASE", "").strip()
    if is_ollama and not base_url:
        base_url = "http://localhost:11434"

    raw_max_tokens = config.get("max_tokens") or os.getenv("LLM_MAX_TOKENS", "2048")
    try:
        max_tokens = int(raw_max_tokens)
    except Exception:
        max_tokens = 2048
    max_tokens = max(1, min(max_tokens, 8192))
    temperature = float(config.get("temperature") or os.getenv("LLM_TEMPERATURE", "0"))

    return LiteLLMAdapter(
        model=model,
        api_key=api_key,
        api_base=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )
