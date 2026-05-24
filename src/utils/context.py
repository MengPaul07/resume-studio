import contextvars
from typing import Dict, Any

# A ContextVar to hold LLM configuration for the current request context
llm_config_var: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar('llm_config', default={})
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('user_id', default='')

def get_llm_config() -> Dict[str, Any]:
    return llm_config_var.get()

def set_llm_config(config: Dict[str, Any]) -> None:
    llm_config_var.set(config)

def get_user_id() -> str:
    return user_id_var.get()

def set_user_id(uid: str) -> None:
    user_id_var.set(uid)
