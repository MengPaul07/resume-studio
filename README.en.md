# resume-builder

AI resume optimization assistant — upload, chat-to-edit, visual layout. Full-stack.

Frontend and resume template design inspired by [Resume-Matcher](https://github.com/srbhr/Resume-Matcher).

- 中文文档: [README.md](./README.md)

## Quick Start

### Prerequisites

- Python 3.11+ (`.venv` recommended)
- Node.js 18+

### Setup

```bash
pip install -r requirements.txt
npm install
npm --prefix frontend install

# Configure environment
cp .env.example .env

# Launch
npm run dev
```

| Service | URL |
|---------|-----|
| Frontend | `http://127.0.0.1:5173` |
| Backend API | `http://127.0.0.1:8000` |
| API Docs | `http://127.0.0.1:8000/docs` |

## Project Structure

```text
src/                          # FastAPI backend
  api/                        # API routes (v1/v2/tool/session)
  services/                   # Business logic + Agent pipeline
    content_refinement_v3/    #   Agent: planner / runner / self-check / prompts
bench/                        # Eval system (CLI + harness + metrics + judge)
  fixtures/resumes/           #   14 diverse resume fixtures (ZH/EN, multiple industries)
scripts/                      # Backward-compatible entry points
frontend/                     # React + Vite frontend
  src/pages/                  #   Dashboard / Tailor / Builder / Settings
tests/                        # Unit tests + fixtures
docs/                         # Design and process docs
outputs/                      # Eval run results
```

## Agent Pipeline

Each user message goes through a single-turn pipeline:

```
User Message → observe_content → rewrite_message (LLM) → IntentResolver (LLM)
→ ChainPlanner → tool execution → compose_and_check (LLM) → response
```

| Intent | Chain |
|--------|-------|
| `explicit_edit` | observe → refine → compose |
| `broad_edit` | observe → suggest → refine → compose |
| `fact_edit` | observe → suggest → compose |
| `analysis_only` | observe → analyze → compose |
| `general_chat` | observe → compose |

See [AGENTS.md](./AGENTS.md) for detailed architecture and the full mermaid flowchart.

## Eval & Bench

### Basic Usage

```bash
# Regression (19 scenarios)
bench eval --quick -j 4

# Full suite (35 scenarios)
bench eval -j 4

# Filter by intent
bench eval --intent fact_edit -j 4

# Single scenario
bench eval --scenario explicit-summary -j 1
```

### Cross-Resume Testing

14 diverse resume fixtures covering different career stages, industries, languages, and problem types:

```bash
# All fixtures × all scenarios
bench eval --resume-fixtures -j 4

# Random sample (different each run)
bench eval --resume-fixtures --sample 3 -j 4

# Single fixture
bench eval --resume messy_format -j 4
```

### Key Metrics

| Metric | Target |
|--------|--------|
| Pass rate | > 85% |
| Intent accuracy | > 90% |
| Chain validity | > 95% |
| Self-check pass rate | > 70% |
| Avg response time | < 30s |
| Quality score (LLM judge) | > 3.5/5.0 |

### Self-Iteration Loop

```bash
bench eval -j 4                              # baseline
python scripts/dres_bench.py iterate diagnose # analyze failures
# → fix code
python scripts/dres_bench.py iterate verify   # re-run + compare
```

### Other Commands

```bash
bench compare <run1> <run2>     # Compare two runs
bench explain <scenario>        # Explain a failure
bench tasks [run_dir]           # Re-generate TASKS.md
```

## More Docs

- [AGENTS.md](./AGENTS.md) — Coding agent operations manual (architecture details, common fix locations)
- [CHANGELOG.md](./CHANGELOG.md) — Iteration log
- [docs/](./docs/) — Design documents
