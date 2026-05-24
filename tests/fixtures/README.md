# Test Fixtures

Structured test data for unit tests, integration tests, and benchmark evaluation.

## Directory Structure

```
fixtures/
├── resumes/          # Resume JSON variants for different profiles
│   ├── minimal.json        # Minimal resume (required fields only)
│   ├── full_stack_en.json  # Full English resume (all sections)
│   ├── full_stack_zh.json  # Full Chinese resume (all sections)
│   ├── new_grad.json       # New graduate profile
│   └── executive.json      # Senior executive profile
├── jds/              # Job description samples
│   ├── backend_python.json # Backend Python JD
│   ├── pm_senior.json      # Senior PM JD (Chinese)
│   └── frontend_react.json # Frontend React JD
├── expected/         # Expected outputs for classification tests
│   ├── intent_classification.json  # Message → expected intent mapping
│   └── scope_detection.json        # Message → expected scope mapping
└── README.md
```

## Usage

### In pytest

```python
import json
from pathlib import Path

FIXTURES = Path(__file__).parent

def load_resume(name: str) -> dict:
    return json.loads((FIXTURES / "resumes" / f"{name}.json").read_text())

def test_with_minimal_resume():
    resume = load_resume("minimal")
    assert "personalInfo" in resume
```

### In agent_eval.py

The agent eval harness uses the built-in `FALLBACK_RESUME`. To use fixtures instead, import from here or load directly.

### Expected classification data

The `expected/` directory contains test case mappings used by `test_intent_resolver.py` and scope detection tests.

## Schema

All resume fixtures follow the D-Resume document schema:
- `personalInfo` — name, title, contact
- `summary` — professional summary string
- `workExperience[]` — title, company, location, years, description[]
- `education[]` — institution, degree, years, description
- `personalProjects[]` — name, role, years, description[]
- `additional` — technicalSkills, languages, certifications, awards
- `customSections` — arbitrary additional sections

All JD fixtures follow:
- `title` — job title
- `company` — company name
- `location` — job location
- `content` — full JD text
- `keywords` — extracted keywords for ATS matching tests

## Adding New Fixtures

1. Add the JSON file to the appropriate directory
2. Update the `expected/` mappings if adding new test cases
3. Tag the fixture with `"difficulty": "easy|medium|hard"` for test filtering
