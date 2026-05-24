<p align="center">
  <h1 align="center">Resume Studio</h1>
  <p align="center">
    Build, tailor, review, and rehearse your resume with an AI-native workspace.
  </p>
  <p align="center">
    Conversational editing | Visual resume layouts | JD-aware optimization | Mock interviews | Agent evaluation
  </p>
</p>

<p align="center">
  <a href="#quick-start"><img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white"></a>
  <a href="#tech-stack"><img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white"></a>
  <a href="#tech-stack"><img alt="React" src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=111"></a>
  <a href="#tech-stack"><img alt="Vite" src="https://img.shields.io/badge/Vite-5-646CFF?style=for-the-badge&logo=vite&logoColor=white"></a>
  <a href="#tests"><img alt="Tests" src="https://img.shields.io/badge/tests-131%20passing-2EA44F?style=for-the-badge"></a>
</p>

<p align="center">
  <a href="#why-d-resume">Why</a>
  |
  <a href="#preview">Preview</a>
  |
  <a href="#product-tour">Product Tour</a>
  |
  <a href="#quick-start">Quick Start</a>
  |
  <a href="#architecture">Architecture</a>
  |
  <a href="#agent-system">Agent System</a>
  |
  <a href="#tests">Tests</a>
  |
  <a href="./README.zh-CN.md">Chinese</a>
</p>

---

<p align="center">
  <img src="./docs/assets/d-resume-hero.svg" alt="Resume Studio product preview" width="92%">
</p>

## Why Resume Studio?

Resume Studio is a full-stack AI workspace for the messy, iterative reality of job applications. Instead of treating resume writing as a one-shot document generation task, it gives users a place to refine content, tune layout, align with a target job description, and practice the interview that follows.

Most resume tools stop at templates. Resume Studio focuses on the whole loop:

<table>
  <tr>
    <td width="25%" align="center"><b>Import</b><br>Bring in resume data and job context.</td>
    <td width="25%" align="center"><b>Improve</b><br>Use an agent to rewrite, clarify, and restructure.</td>
    <td width="25%" align="center"><b>Design</b><br>Tune the layout with visual controls and reusable templates.</td>
    <td width="25%" align="center"><b>Rehearse</b><br>Run mock interviews grounded in the resume and target JD.</td>
  </tr>
</table>

It is designed as a practical product prototype and as an agent engineering playground: the backend exposes observable tool calls, regression evaluations, self-checking, and deterministic test coverage so changes can be measured instead of guessed.

## Preview

<table>
  <tr>
    <td width="64%">
      <img src="./docs/assets/d-resume-hero.svg" alt="Resume Studio resume editing and layout preview">
    </td>
    <td width="36%">
      <h3>Built for the full application loop</h3>
      <p>Resume Studio is designed around the real path from a rough resume to a targeted application: import, refine, align with a job description, tune the document, and rehearse the interview.</p>
      <p>Drop your upcoming screenshots into <code>docs/assets/</code> and replace this preview panel with real product captures.</p>
    </td>
  </tr>
</table>

### Interviewer Presets

<p align="center">
  <img src="./frontend/src/assets/interview/interviewer-avatars.png" alt="Resume Studio interviewer avatar presets" width="48%">
  <img src="./frontend/src/assets/interview/interviewer-avatars-extra.png" alt="Additional Resume Studio interviewer avatar presets" width="48%">
</p>

## Product Tour

<table>
  <tr>
    <td width="50%">
      <h3>Chat-Driven Resume Editing</h3>
      <p>Ask for targeted edits like "make my summary more backend-focused" or "rewrite the first bullet with stronger metrics." The agent reads the current resume, chooses tools, applies field-level edits, and streams its progress to the UI.</p>
      <ul>
        <li>Function-calling agent loop</li>
        <li>Resume-aware context assembly</li>
        <li>Field-level updates with structured paths</li>
        <li>Confirmation flow for sensitive factual changes</li>
      </ul>
    </td>
    <td width="50%">
      <h3>Visual Layout Builder</h3>
      <p>Design the resume as a real document, not just a blob of text. Adjust sections, template guidance, spacing, typography, two-column layouts, tags, headers, and printable HTML output.</p>
      <ul>
        <li>Single-column and two-column resume layouts</li>
        <li>Section order and visibility controls</li>
        <li>Template-level guidance and local presets</li>
        <li>HTML export path for reliable browser printing</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>JD-Aware Resume Targeting</h3>
      <p>Attach a target job description and let the assistant reason against it. The system can inject JD context into the agent loop and use retrieval-oriented guidance to identify alignment opportunities.</p>
      <ul>
        <li>Target JD context injection</li>
        <li>RAG-ready local artifacts</li>
        <li>Role-specific rewrite guidance</li>
        <li>Clear separation between resume data and layout templates</li>
      </ul>
    </td>
    <td width="50%">
      <h3>Mock Interview Workspace</h3>
      <p>Practice with interviewers from different domains. The flow supports interviewer recommendations, resume/JD-grounded questions, interview termination detection, and a dedicated review mode after the session ends.</p>
      <ul>
        <li>Multi-industry interviewer presets</li>
        <li>Resume-aware and JD-aware prompts</li>
        <li>Custom user preference prompt</li>
        <li>Post-interview review mode</li>
      </ul>
    </td>
  </tr>
</table>

## Highlights

| Area | What makes it useful |
| --- | --- |
| Agent UX | Tool calls are streamed over SSE, so the UI can show what the assistant is doing instead of waiting on a silent black box. |
| Resume edits | Edits are applied to structured resume fields, which keeps content changes inspectable and easier to test. |
| Layout design | Template state is separated from resume content, so changing a layout does not silently mutate the resume itself. |
| Export | Printable HTML is the default export path. TeX is generated as source for users who want to compile in Overleaf or a local XeLaTeX environment. |
| Evaluation | Agent behavior has regression scenarios, fixture-based tests, and reporting scripts for iterative improvement. |
| Local-first workflow | The project is designed to run locally with explicit `.env` configuration and local runtime artifacts. |

## Quick Start

### Environment Setup

Detailed install guides for Python and Node.js on all platforms: [Development Setup → Environment Setup](./docs/development/setup.md#environment-setup--%E7%8E%AF%E5%A2%83%E5%AE%89%E8%A3%85)

**TL;DR:**

| Platform | Python | Node.js |
|----------|--------|---------|
| macOS | `brew install python@3.13` | `brew install node@22` |
| Windows | [python.org](https://www.python.org/downloads/) (check "Add to PATH") | [nodejs.org](https://nodejs.org/) (LTS) |
| Ubuntu | `sudo apt install python3 python3-pip python3-venv` | `curl -fsSL https://deb.nodesource.com/setup_22.x \| sudo -E bash - && sudo apt install -y nodejs` |

Minimal versions: **Python ≥ 3.11**, **Node.js ≥ 18**. Verify with `python --version` and `node --version`.

### Install

```bash
git clone https://github.com/MengPaul07/resume-builder
cd resume-builder

# Backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..

# Config
cp .env.example .env        # Windows: copy .env.example .env
# Edit .env and add your LLM_API_KEY
```

### Run Everything

```bash
npm run dev
```

| Service | URL |
| --- | --- |
| Frontend | `http://127.0.0.1:5173` |
| Backend API | `http://127.0.0.1:8000` |
| API Docs | `http://127.0.0.1:8000/docs` |

### Run Services Separately

```bash
npm run dev:backend
npm run dev:frontend
```

## Agent System

Resume Studio uses a function-calling agent loop rather than a single prompt that returns prose. This makes editing behavior observable and testable.

| Component | Role |
| --- | --- |
| Intent resolver | Classifies the user request into editing, analysis, fact change, or general chat categories. |
| Chain planner | Maps intent to a deterministic tool chain such as observe, suggest, refine, and compose. |
| Tool runner | Executes read, edit, confirm, and compose tools while streaming SSE events. |
| Self-checker | Reviews the output and can request a retry or fail softly when the response is not good enough. |
| Eval scripts | Run regression scenarios and produce reports for agent behavior changes. |

### Key Files

| Path | Role |
| --- | --- |
| `src/services/content_refinement_v3/agent/turn_runner.py` | Turn orchestration, tool execution, and SSE output |
| `src/services/content_refinement_v3/agent/_planner.py` | Intent classification and deterministic chain mapping |
| `src/services/content_refinement_v3/agent/_self_check.py` | Response quality checks and retry decisions |
| `src/services/content_refinement_v3/prompts/agent.py` | Agent and self-check prompts |
| `src/services/layout_design/` | Resume layout rendering, pagination, and HTML/TeX generation |
| `frontend/src/` | React app, chat UI, layout builder, and mock interview UI |

## Layout Builder

The layout system is built around reusable guidance and section configuration rather than hard-coded one-off templates.

| Capability | Description |
| --- | --- |
| Section control | Reorder and hide resume sections without changing the underlying resume content. |
| Template guidance | Store layout and style preferences as template-level state. |
| HTML rendering | Generate A4-style printable HTML for browser-native export. |
| TeX source | Generate TeX for users who prefer Overleaf or local XeLaTeX compilation. |
| Style tuning | Adjust variables such as page padding, column width, spacing, heading style, tag style, and font sizing. |

## Mock Interview

The mock interview flow is built for targeted practice rather than generic question lists.

<p align="center">
  <img src="./frontend/src/assets/interview/interviewer-avatars.png" alt="Mock interview interviewer lineup" width="82%">
</p>

| Stage | What happens |
| --- | --- |
| Setup | The user selects interview length, interviewer style, industry tags, target JD, resume, and optional custom preferences. |
| Interview | The interviewer starts with the first message, asks resume/JD-grounded questions, and adapts across rounds. |
| Termination | The system can detect when an interview has ended instead of forcing a fixed flow. |
| Review | A dedicated review prompt can analyze the session and give focused feedback. |

## Tech Stack

<table>
  <tr>
    <th align="left">Layer</th>
    <th align="left">Technologies</th>
  </tr>
  <tr>
    <td>Backend</td>
    <td>FastAPI, Pydantic, LiteLLM, SSE, SQLite-backed local stores</td>
  </tr>
  <tr>
    <td>Frontend</td>
    <td>React 18, Vite, TypeScript, Tailwind CSS, Framer Motion, i18next</td>
  </tr>
  <tr>
    <td>Retrieval</td>
    <td>FAISS, fastembed, local JD/context artifacts</td>
  </tr>
  <tr>
    <td>Documents</td>
    <td>HTML export, TeX source export, Jinja2, MarkItDown</td>
  </tr>
  <tr>
    <td>Quality</td>
    <td>pytest, frontend build checks, agent eval scripts</td>
  </tr>
</table>

## Project Structure

```text
resume-builder/
  src/                         FastAPI backend
    api/                       API routes
    services/
      content_refinement_v3/   Agent, prompts, sessions, resume editing
      layout_design/           HTML/TeX layout rendering
  frontend/                    React + Vite frontend
    src/
      components/              UI components
      pages/                   App pages and flows
      lib/                     Frontend helpers and types
  config/                      Document type and runtime configuration
  scripts/                     Eval and maintenance scripts
  tests/                       Backend tests
  docs/                        Design notes and supporting docs
```

## Tests

Run the backend test suite:

```bash
python -m pytest tests -q
```

Run the frontend build check:

```bash
npm --prefix frontend run build
```

The current local suite is expected to pass with `131` backend tests after dependencies are installed. See [tests/README.md](./tests/README.md) for a more detailed testing guide.

## Agent Evaluation

For agent behavior work, start the backend first:

```bash
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

Then run one of the evaluation commands:

```bash
python scripts/agent_eval.py --regression --base-url http://127.0.0.1:8000/api/v1 -j 4
python scripts/agent_eval.py --base-url http://127.0.0.1:8000/api/v1 -j 4
python scripts/dres_bench.py iterate diagnose
```

## Configuration Notes

- Copy `.env.example` to `.env` before running the app.
- The project is local-first by default.
- Generated runtime artifacts are kept out of the main product flow.
- TeX export is generated as source text. Users can compile it in Overleaf or their own TeX environment.
- Layout templates and resume data are intentionally separated so template tuning does not silently overwrite resume content.

## Documentation

All documentation lives in [`docs/`](./docs/). Start from the [index](./docs/index.md) or jump directly to any page:

### Features / 功能

| Document | Description |
|----------|-------------|
| [Dashboard](./docs/features/dashboard.md) | Central workspace — manage imports, resumes, and access all tools |
| [Resume Builder](./docs/features/resume-builder.md) | Visual layout editor — typography, spacing, colors, section order |
| [AI Tailor](./docs/features/ai-tailor.md) | AI-powered resume refinement — natural language editing, JD matching |
| [Mock Interview](./docs/features/mock-interview.md) | 12 interviewer presets with coding problems and review mode |
| [Settings](./docs/features/settings.md) | LLM configuration and model presets |

### Development / 开发

| Document | Description |
|----------|-------------|
| [Setup](./docs/development/setup.md) | Local development environment setup |
| [Architecture](./docs/development/architecture.md) | System design and data flow |

### Design & Notes / 设计与笔记

| Document | Description |
|----------|-------------|
| [Layout Design Flow](./docs/layout_design_main_flow.md) | Layout builder rendering pipeline |
| [UI Style Guide v2](./docs/ui-style-guide-v2.md) | macOS-minimalist design system reference |
| [Context Engineering](./docs/context-engineering-wechat.md) | Context engineering notes (WeChat article) |
| [SDGP Ideas](./docs/sdgp_idea_notes.md) | Product concept and roadmap brainstorming |
| [Plans](./docs/plans/) | Implementation plans and design RFCs |

See the [docs index](./docs/index.md) for the full navigation map.

## Roadmap Ideas

These are natural next steps for contributors, not hard requirements:

- Add polished screenshots or a short product demo GIF.
- Add more resume import fixtures and public sample projects.
- Expand mock interviewer presets across more industries.
- Improve layout template sharing and versioning.
- Add hosted deployment documentation once the deployment path is finalized.

## Credits

The frontend and resume template direction were originally inspired by [Resume-Matcher](https://github.com/srbhr/Resume-Matcher).
