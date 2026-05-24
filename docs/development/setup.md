# Development Setup / 开发环境搭建

> How to run the project locally for development.  
> 本地开发环境搭建指南。

---

## Prerequisites / 前置条件

### Required / 必需

| Tool | Version | Purpose |
|------|---------|---------|
| Python | ≥ 3.11 | Backend runtime |
| Node.js | ≥ 18 | Frontend build + dev server |
| npm / pnpm | — | Package management |
| Git | — | Version control |

## Environment Setup / 环境安装

### Python / Python 环境

**macOS:**

```bash
# Option 1: Official installer
# Download from https://www.python.org/downloads/ (≥ 3.11)

# Option 2: Homebrew (recommended)
brew install python@3.13

# Verify
python3 --version   # should be ≥ 3.11
```

**Windows:**

```bash
# Option 1: Official installer
# Download from https://www.python.org/downloads/ (≥ 3.11)
# IMPORTANT: check "Add Python to PATH" during installation

# Option 2: Microsoft Store
# Search "Python 3.13" in Microsoft Store

# Verify
python --version    # should be ≥ 3.11
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
python3 --version
```

### Node.js / Node.js 环境

**macOS:**

```bash
# Option 1: Official installer
# Download from https://nodejs.org/ (LTS, ≥ 18)

# Option 2: Homebrew (recommended)
brew install node@22

# Verify
node --version   # should be ≥ 18
npm --version
```

**Windows:**

```bash
# Option 1: Official installer
# Download from https://nodejs.org/ (LTS, ≥ 18)
# The installer includes npm automatically

# Option 2: nvm-windows (for switching versions)
# Download from https://github.com/coreybutler/nvm-windows

# Verify
node --version   # should be ≥ 18
npm --version
```

**Linux (Ubuntu/Debian):**

```bash
# Option 1: NodeSource (recommended)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# Option 2: nvm (for switching versions)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
nvm install 22

# Verify
node --version
npm --version
```

### Git

**macOS:** `brew install git` (or Xcode Command Line Tools)  
**Windows:** Download from https://git-scm.com/  
**Linux:** `sudo apt install git`

## Quick Start / 快速启动

### 1. Clone & install / 克隆并安装

```bash
git clone <repo-url>
cd resume-studio

# Backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### 2. Configure / 配置

Create `.env` in the project root:

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_API_KEY=your-api-key
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.7
DEBUG=true
```

### 3. Seed JD database / 导入 JD 数据

```bash
# Load JD fixtures into FAISS index
python scripts/seed_jds.py
```

This loads 87+ campus JDs from `tests/fixtures/jds/`. Skip if you don't need JD matching.

### 4. Run / 启动

**Backend** (Terminal 1):

```bash
cd resume-studio
.venv/Scripts/python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

On Linux/Mac:
```bash
cd resume-studio
source .venv/bin/activate
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend** (Terminal 2):

```bash
cd resume-studio/frontend
npm run dev
```

Frontend typically starts on `http://localhost:5173`. Backend on `http://localhost:8000`.

### 5. Verify / 验证

- Open `http://localhost:5173` in browser
- Dashboard should show with engine status
- Navigate to Settings → Test API Connectivity
- API docs: `http://localhost:8000/docs`

## Windows-Specific / Windows 特别说明

### WSL Users / WSL 用户

If using WSL for development:

```bash
# Git operations in WSL
cd ~/projects/resume-studio

# Backend runs from Windows or WSL
# Use cmd or PowerShell:
D:\Repo\resume-studio\.venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000

# Frontend dev server from Windows:
cd D:\Repo\resume-studio\frontend
npm run dev
```

**Note**: PDF export uses browser HTML printing. TeX export only generates source text for Overleaf or a user-managed TeX environment.

Project code should live in Windows filesystem (`D:\Repo\`) for full compatibility. WSL can be used for Git, searching, and editing.

### Port Conflicts / 端口冲突

If port 8000 is already in use:

```bash
# Find and kill the process
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Or use a different port
uvicorn src.main:app --port 8001
```

If using port 8001, update `frontend/vite.config.ts` proxy accordingly.

## Testing / 测试

### Backend Tests / 后端测试

```bash
# Run unit + integration tests (no API key needed)
python -m pytest tests/unit tests/integration -q

# Run LLM tests (requires API key in .env)
python -m pytest tests/llm -n auto -q

# Run everything
python -m pytest tests -q
```

### Agent Eval / Agent 评估

```bash
# Terminal 1: Start server
.venv/Scripts/python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Run eval
set PYTHONPATH=.
.venv/Scripts/python.exe scripts/agent_eval.py --base-url http://127.0.0.1:8000/api/v1 -j 4

# Fast regression (19 scenarios)
python scripts/agent_eval.py --regression --base-url http://127.0.0.1:8000/api/v1 -j 4
```

## Project Structure / 项目结构

```
resume-builder/
├── docs/                    # Documentation (← you are here)
│   ├── index.md
│   ├── features/
│   │   ├── dashboard.md
│   │   ├── resume-builder.md
│   │   ├── ai-tailor.md
│   │   ├── mock-interview.md
│   │   └── settings.md
│   └── development/
│       ├── architecture.md
│       └── setup.md
├── frontend/                # React SPA
│   ├── src/
│   │   ├── pages/           # Page components
│   │   ├── components/      # Reusable components
│   │   ├── lib/             # Utilities, hooks, types
│   │   ├── i18n/            # Translations (zh.json, en.json)
│   │   └── api/             # API client
│   ├── package.json
│   └── vite.config.ts
├── src/                     # Python backend
│   ├── main.py              # FastAPI app entry
│   ├── api/                 # Route handlers
│   ├── services/            # Business logic
│   │   ├── content_refinement_v3/  # Agent engine
│   │   ├── rag/             # JD vector search
│   │   ├── latex_gen/       # LaTeX generation
│   │   ├── layout_design/   # HTML rendering
│   │   ├── logging/         # Logging service
│   │   └── data/            # File-based storage
│   └── config.py            # Settings
├── tests/                   # Test suite
│   ├── unit/                 # Pure logic, no API needed
│   ├── integration/          # Mocked LLM + TestClient
│   ├── llm/                  # Real LLM API required
│   └── fixtures/             # Shared test data (resumes, jds, expected)
├── scripts/                 # Utility scripts
│   ├── seed_jds.py          # JD database seeding
│   ├── agent_eval.py        # Agent evaluation
│   └── dres_bench.py        # Benchmark tooling
├── templates/               # Built-in templates
│   └── swiss-single.json
├── requirements.txt         # Python dependencies
└── AGENTS.md                # Agent coding ops manual
```

## Common Issues / 常见问题

### "No module named 'faiss'"

```bash
pip install faiss-cpu
```

### "fastembed model download failed"

First run downloads the BGE-small-zh model (~120MB). Ensure network access. Model cached in `~/.cache/fastembed/`.

### Frontend build errors after package changes

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Backend import errors

```bash
# Run from project root, not from src/
cd resume-builder
python -c "from src.main import app; print('OK')"
```

### Hot reload not detecting changes (Windows)

The `--reload` flag with uvicorn may not detect file changes on some Windows configurations. Restart the server manually after changes, or use `watchfiles`:

```bash
pip install watchfiles
uvicorn src.main:app --reload
```
