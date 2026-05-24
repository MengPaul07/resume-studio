# Test Guide

The default test suite is designed to be deterministic and friendly for open
source contributors. It should not require API keys, a running server, FAISS
model downloads, a LaTeX compiler, or browser automation.

## Default Checks

From the repository root:

```bash
python -m pytest tests -q
npm --prefix frontend run build
```

The backend tests use mocks for LLM calls and isolate runtime stores in pytest
temporary directories, so they should not write session/import/recent-resume
data into the checkout.

## Test Layers

### Unit and Contract Tests

These are the default tests. They cover pure logic and mocked agent flows:

- `test_suggestion_ops.py`: suggestion normalization, diff payloads, path helpers.
- `test_turn_runner.py`: intent/scope helper functions.
- `test_agent_loop.py`: function-calling loop behavior with mocked LLM responses.
- `test_sse_scenarios.py`: in-process SSE flows with mocked LLM responses.
- `test_interview.py`: mock interview prompts and tool schema contracts.
- `test_jd_tools.py`: JD search/target tool behavior with mocked storage.
- `test_latex_render.py`: TeX source generation as text, without compiling TeX.
- `test_v3_routes.py` and `test_api.py`: route registration and basic health checks.

### API Tests

`test_resources_import_recent.py` uses FastAPI `TestClient` and monkeypatches
file parsing and storage calls. It does not require an external server.

### Optional Evaluation Scripts

Agent benchmark scripts are intentionally not part of the default test command.
They may require a running backend and, depending on configuration, an LLM API.

Typical manual commands:

```bash
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
python scripts/agent_eval.py --base-url http://127.0.0.1:8000/api/v1 -j 4
python scripts/agent_eval.py --regression --base-url http://127.0.0.1:8000/api/v1 -j 4
```

## Fixtures

Fixtures live under `tests/fixtures/`.

- `resumes/`: synthetic resume profiles used by unit and render tests.
- `jds/`: job-description fixtures for local RAG/JD experiments.
- `expected/`: expected classification/scope examples retained for regression reference.

If this repository is prepared for public release, prefer synthetic JD fixtures
over copied real job postings.

## Markers

Markers are declared in `pytest.ini` for future filtering:

- `unit`
- `integration`
- `slow`
- `llm`
- `regression`

The current default suite is intended to run without selecting markers.
