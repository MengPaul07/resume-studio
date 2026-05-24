"""Shared helpers for real-LLM tests."""
from __future__ import annotations

import json
import os
import time

MODEL = os.getenv("TEST_MODEL", "deepseek-v4-flash")
LLM_CONFIG = {
    "model": MODEL,
    "temperature": 0.3,
}
if os.getenv("TEST_API_KEY"):
    LLM_CONFIG["api_key"] = os.getenv("TEST_API_KEY")
if os.getenv("TEST_API_BASE"):
    LLM_CONFIG["api_base"] = os.getenv("TEST_API_BASE")


DEFAULT_USER_ID = "test-user-llm-suite"

def session(resume: dict, user_id: str = DEFAULT_USER_ID) -> str:
    from fastapi.testclient import TestClient
    from src.main import app
    r = TestClient(app).post("/api/v1/agent/v3/sessions",
        json={"raw_document_obj": resume, "refined_document_obj": resume, "llm_config": LLM_CONFIG},
        headers={"X-User-Id": user_id},
    )
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def run_turn(sid: str, msg: str, timeout: int = 180, user_id: str = DEFAULT_USER_ID) -> dict:
    from fastapi.testclient import TestClient
    from src.main import app
    client = TestClient(app)
    events = []
    t0 = time.perf_counter()
    with client.stream(
        "POST", f"/api/v1/agent/v3/sessions/{sid}/turns:run",
        json={"message": msg, "allow_mutation": True, "llm_config": LLM_CONFIG},
        headers={"X-User-Id": user_id},
        timeout=timeout,
    ) as resp:
        ev = None
        for line in resp.iter_lines():
            s = line.decode("utf-8") if isinstance(line, bytes) else line
            if s.startswith("event: "): ev = s[7:].strip()
            elif s.startswith("data: ") and ev:
                events.append((ev, json.loads(s[6:])))
                ev = None
    elapsed = time.perf_counter() - t0
    r2 = client.get(f"/api/v1/agent/v3/sessions/{sid}?message_limit=10&event_limit=100")
    state = r2.json().get("state", {}) if r2.status_code == 200 else {}
    completed = [e for e in events if e[0] == "turn.completed"]
    err = completed[0][1].get("error", "") if completed else "no turn.completed"
    return {"state": state, "error": err, "elapsed": elapsed, "events": events}


def get(obj, path):
    from src.services.content_refinement_v3.session.service import _get_by_path_local
    return _get_by_path_local(obj, path)


def refined(state):
    return state.get("refined_document_obj", {}) or state.get("refined_resume_obj", {})
