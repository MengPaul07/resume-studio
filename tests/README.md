# Test Guide

## Quick Start

```bash
# Unit + integration (no API key, ~190 tests, ~30s)
python -m pytest tests/unit tests/integration -q

# LLM scenarios (needs API key in .env, 34 tests, ~50s)
python -m pytest tests/llm -n auto -q

# Everything
python -m pytest tests -q
```

## Directory Structure

```
tests/
├── unit/              ← Pure logic, no LLM, no network
├── integration/       ← Mocked LLM + FastAPI TestClient
├── llm/               ← Real LLM API required
│   └── helpers.py     ← Shared helpers (session, run_turn, etc.)
├── fixtures/          ← Shared test data (resumes, jds, expected)
├── conftest.py        ← Shared fixtures (isolated storage)
└── README.md
```

## Unit Tests — `tests/unit/`

Run without setup. No API keys, no server, no network.

| File | What it tests |
|------|--------------|
| `test_suggestion_ops.py` | Suggestion normalization, merging, dedup, path helpers |
| `test_turn_runner.py` | Intent/scope helpers, diff payloads |
| `test_self_check.py` | Compose verdict logic, fact issue extraction |
| `test_intent_resolver.py` | Agent prompt structure |
| `test_interview.py` | Interview prompt contracts, tool schemas |
| `test_latex_render.py` | TeX source generation |
| `test_llm_settings.py` | LLM config resolution |
| `test_jd_tools.py` | JD search/target tools with mocked storage |
| `test_edit_field.py` | `_set_by_path`, `_get_by_path`, `_tokenize_path`, `build_parse_prompt`, `tool_edit_field` |

```bash
python -m pytest tests/unit -q
```

## Integration Tests — `tests/integration/`

Mock the LLM, test through FastAPI `TestClient`.

| File | What it tests |
|------|--------------|
| `test_agent_loop.py` | Agent loop with mocked LLM |
| `test_sse_scenarios.py` | SSE streaming (greeting / analysis / edit / multi-tool) |
| `test_edit_field_integration.py` | edit_field through full agent loop |
| `test_v3_routes.py` | Route registration |
| `test_api.py` | Health check + root endpoint |
| `test_resources_import_recent.py` | Import + recent-resume flows |

```bash
python -m pytest tests/integration -q
```

## LLM Tests — `tests/llm/`

Requires API key in `.env`. Uses `deepseek-v4-flash` by default.

Override via env:
```bash
TEST_MODEL=gpt-4o-mini TEST_API_KEY=sk-xxx TEST_API_BASE=https://api.openai.com/v1 \
  python -m pytest tests/llm -n auto
```

| File | Tests | Coverage |
|------|-------|----------|
| `test_edit_field_llm.py` | 10 | Multi-degree, rich work, corrupted repair, multi-section, JD tailoring, projects, delete+readd, arrays, nested, full build |
| `test_parse_llm.py` | 4 | Chinese resume, English resume, additional fields, non-resume text |
| `test_interview_llm.py` | 4 | Start interview, Q&A follow-up, end with report, coding question event |
| `test_refine_llm.py` | 6 | Summary rewrite, bullet improvement, skill add, typo fix, education add, invent prevention |
| `test_tailor_llm.py` | 9 | JD search, set target JD, greeting, analysis-only, delete, fact-sensitive, custom sections, multi-turn, JSON format |

```bash
python -m pytest tests/llm -v -s -n auto
```

## Fixtures

`tests/fixtures/resumes/` — synthetic resume profiles. Referenced via:
```python
from pathlib import Path
path = Path(__file__).parent.parent / "fixtures/resumes/full_stack_zh.json"
```

## Writing New Tests

1. **Pure logic** → `tests/unit/`
2. **Full pipeline, mocked LLM** → `tests/integration/`
3. **Real LLM call** → `tests/llm/`

Conventions:
- Lazy imports inside test functions or fixtures
- `monkeypatch` for mocking
- `conftest.py` handles storage isolation automatically
- LLM tests use `tests.llm.helpers` for shared `session()`, `run_turn()`, etc.
