import contextvars
from typing import Dict, Any

# A ContextVar to hold LLM configuration for the current request context
llm_config_var: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar('llm_config', default={})

def get_llm_config() -> Dict[str, Any]:
    return llm_config_var.get()

def set_llm_config(config: Dict[str, Any]) -> None:
    llm_config_var.set(config)
