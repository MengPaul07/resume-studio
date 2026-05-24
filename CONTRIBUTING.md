# Contributing

## Setup

```bash
# Backend
cp .env.example .env    # fill in your API keys
pip install -r requirements.txt
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

> **Windows users**: run the backend with `start-backend.bat` and the frontend from PowerShell/CMD. WSL can read/write files but cannot execute the Windows Node/Python toolchain.

## Running Tests

```bash
pytest tests/ -q
```

133 tests should pass. No API keys needed — tests use mocked LLM responses.

## Pull Requests

1. Fork and branch from `master`
2. Make changes + add tests if applicable
3. Run `pytest tests/ -q` and `npm --prefix frontend run build`
4. Open a PR with a clear description

Keep PRs focused. One feature or fix per PR.
