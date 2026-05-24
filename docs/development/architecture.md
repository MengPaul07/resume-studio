# Architecture / 架构

> System design, data flow, and key abstractions.  
> 系统设计、数据流、核心抽象。

---

## Architecture Overview / 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React SPA)                  │
│  ┌──────────┬──────────┬──────────┬──────────────────┐  │
│  │ Dashboard│ Builder  │  Tailor  │  Mock Interview  │  │
│  └────┬─────┴────┬─────┴────┬─────┴────────┬─────────┘  │
│       │          │          │              │             │
│       ▼          ▼          ▼              ▼             │
│  ┌──────────────────────────────────────────────────┐   │
│  │              API Client (fetch)                   │   │
│  └──────────────────────┬───────────────────────────┘   │
└─────────────────────────┼───────────────────────────────┘
                          │ HTTP (REST + SSE)
┌─────────────────────────┼───────────────────────────────┐
│                    Backend (FastAPI)                     │
│  ┌──────────────────────┴───────────────────────────┐   │
│  │              API Routes                           │   │
│  │  /api/v1/agent/v3/*  → Agent loop, chat, interview   │   │
│  │  /api/v1/agent/*     → CRUD for data                 │   │
│  │  /api/v1/latex/*   → LaTeX generation                │   │
│  └──────┬────────────────────────┬──────────────────┘   │
│         │                        │                       │
│         ▼                        ▼                       │
│  ┌──────────────┐    ┌──────────────────────┐           │
│  │ Agent Engine │    │   Data Services      │           │
│  │ ──────────── │    │   ─────────────────  │           │
│  │ Agent Loop   │    │   RecentResumeStore  │           │
│  │ Tool Registry│    │   SessionStore       │           │
│  │ Self-Check   │    │   JdRepository       │           │
│  │ Compose      │    │   LaTeX Generator    │           │
│  └──────┬───────┘    └──────────┬───────────┘           │
│         │                       │                        │
│         ▼                       ▼                        │
│  ┌──────────────────────────────────────────────┐       │
│  │              Storage Layer                    │       │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │       │
│  │  │ SQLite   │ │ FAISS    │ │ File System  │ │       │
│  │  │ sessions │ │ JD index │ │ JSON/MD/HTML │ │       │
│  │  └──────────┘ └──────────┘ └──────────────┘ │       │
│  └──────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

## Frontend / 前端

### Technology / 技术

| Component | Technology |
|-----------|-----------|
| Framework | React 19 |
| Language | TypeScript |
| Styling | Tailwind CSS v4 |
| Build | Vite |
| Routing | React Router v7 |
| i18n | react-i18next |
| Code editor | react-simple-code-editor + PrismJS |
| Math rendering | KaTeX |
| Icons | Lucide React |

### Page Routes / 页面路由

| Path | Page | Description |
|------|------|-------------|
| `/` | `Dashboard` | Workspace overview |
| `/create` | `CreateResumePage` | AI-guided resume creation |
| `/builder` | `ResumeViewPage` | Layout builder with preview |
| `/tailor` | `TailorChatPage` | AI refinement chat |
| `/interview` | `InterviewPage` | AI mock interview |
| `/settings` | `SettingsPage` | LLM configuration |
| `*` | `NotFoundPage` | 404 |

### Component Architecture / 组件架构

```
pages/
  dashboard.tsx         → Dashboard page
  create-resume.tsx     → Resume creation wizard
  resume-view.tsx       → Builder container (orchestrates EditorPanel + PreviewPanel)
  tailor-chat.tsx       → AI Tailor container (orchestrates chat + TemplatePreview)
  settings.tsx          → Settings page
  not-found.tsx         → 404

components/
  builder-workbench/    → Layout builder components
    BuilderLayout.tsx   → Page shell (header, columns, footer)
    EditorPanel.tsx     → All layout controls (page, canvas, typography, sections, etc.)
    PreviewPanel.tsx    → Live preview wrapper
    PaginatedPreview.tsx→ Multi-page rendering + zoom controls
    PageContainer.tsx   → Single page with transform:scale() zoom
    use-pagination.ts   → Pagination algorithm hook
    html-renderer.ts    → Resume HTML generator from guidance + data
    types.ts            → RenderGuidanceSettings, BuilderSectionDraft
    layout-plan.ts      → Layout plan calculation
    TemplateSidebar.tsx → Template save/load UI
    OverflowWarning.tsx → Content overflow alert

  tailor/              → AI Tailor components
    TemplatePreview.tsx → Resume preview with inline editing
    InterviewModal.tsx  → Full interview setup + session UI
    WritingPanel.tsx    → Code editor + writing panel
    ChatBubble.tsx      → Chat message display
    QuickPrompts.tsx    → Pre-built action buttons
    ChangeToolbar.tsx   → Change management toolbar
    AutoApplyDiff.tsx   → Auto-applied changes display
    LowConfidenceCard.tsx → Low-confidence change review
    FactIssuesCard.tsx  → Sensitive data confirmation
    TargetJDPanel.tsx   → JD selector and display
    JDCard.tsx          → Single JD card component
    SessionListPanel.tsx→ Session history sidebar
    ChangeDetailPopover.tsx → Change detail popover
    InlineFieldEdit.tsx → Generic inline field editor
    LayoutEditor.tsx    → Layout plan editor

  layout/              → Shared layouts
    app-shell.tsx       → Main app shell with navigation
    page-transition.tsx → Page transition wrapper

  ui/                  → Reusable base components
    button.tsx, textarea.tsx, card.tsx, status-badge.tsx
```

### State Management / 状态管理

| Pattern | Usage |
|---------|-------|
| React `useState` | Page-level state, form inputs, UI toggles |
| React `useEffect` | Data fetching, side effects, auto-save |
| Custom hooks | `useTailorSession`, `useTailorDag`, `usePagination`, `useInputHistory` |
| URL params | Resume ID routing (`?resumeId=xxx`) |
| localStorage | Templates, interview sessions, JD target, user preferences |
| Backend API | Source of truth for resume data, sessions |

## Backend / 后端

### Technology / 技术

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI (Python 3.13) |
| LLM Gateway | LiteLLM |
| Embeddings | fastembed (BAAI/bge-small-zh-v1.5) |
| Vector Search | FAISS |
| Database | SQLite (session_memory, faiss index) |
| Export | Printable HTML + TeX source generation |

### API Endpoints / API 端点

#### Agent Loop (v3)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/agent/v3/sessions` | Create a new agent session |
| POST | `/api/v1/agent/v3/sessions/{id}/turns:run` | Send message + run agent loop (SSE) |
| POST | `/api/v1/agent/v3/sessions/{id}/turns:resume` | Resume a paused turn |
| GET | `/api/v1/agent/v3/sessions/{id}` | Get session history |
| POST | `/api/v1/agent/v3/sessions/{id}/actions:apply` | Apply suggested changes |
| POST | `/api/v1/agent/v3/sessions/{id}/actions:reject` | Reject suggested changes |
| POST | `/api/v1/agent/v3/sessions/{id}/rollback` | Rollback to a version |
| DELETE | `/api/v1/agent/v3/sessions/by-resume/{resumeId}` | Delete all sessions for a resume |

#### Resources (CRUD)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/agent/recent-resumes` | List recent resumes |
| POST | `/api/v1/agent/recent-resumes/save` | Create/update resume |
| GET | `/api/v1/agent/recent-resumes/{id}` | Get resume by ID |
| DELETE | `/api/v1/agent/recent-resumes/{id}` | Delete resume |
| GET | `/api/v1/agent/job-descriptions` | List JDs |
| POST | `/api/v1/agent/job-descriptions/save` | Create JD |
| GET | `/api/v1/agent/job-descriptions/{id}` | Get JD by ID |
| DELETE | `/api/v1/agent/job-descriptions/{id}` | Delete JD |
| GET | `/api/v1/agent/imports` | List imported files |
| POST | `/api/v1/agent/import-file` | Upload and parse file |
| POST | `/api/v1/agent/run-import` | Build resume from imported text |
| DELETE | `/api/v1/agent/imports/{id}` | Delete import |
| POST | `/api/v1/agent/test-llm` | Test LLM connectivity |

#### Template & Render

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/agent/v3/template:inspect` | Inspect template sections |
| POST | `/api/v1/agent/v3/template:align` | Align resume to template |
| POST | `/api/v1/agent/v3/template:render` | Render resume to paginated HTML |
| POST | `/api/v1/agent/v3/template:export-latex` | Export LaTeX source |

#### LaTeX

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/latex/tex` | Generate LaTeX source |

### Agent Engine / Agent 引擎

```
User Message → Agent Loop (LLM picks tools) → Self-Check → Response
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
  read_resume      edit_field       compose
  read_history     add_entry        ask_user
  search_jd        update_field     ...
                   set_entry
                   delete_entry
```

The agent loop (`_run_agent_loop` in `_agent_loop.py`) gives the LLM a set of tools and lets it decide which to call. Each turn runs up to 6 rounds of LLM → tool execution → result → LLM. The LLM chooses tools autonomously based on user intent.

#### Core Editing Tools

| Tool | Description |
|------|-------------|
| `read_resume` | Read the current resume state |
| `add_entry` | Append to education/workExperience/personalProjects/research |
| `update_field` | Update a leaf text field (summary, skills, etc.) |
| `set_entry` | Replace an entire array entry with a new JSON object |
| `delete_entry` | Delete an entry from an array section |
| `edit_field` | Legacy multi-mode edit tool (deprecated) |
| `compose` | Finish turn, produce user-facing response |
| `ask_user` | Pause for fact-sensitive change confirmation |
| `search_jd` | Search job descriptions |
| `set_target_jd` | Set target JD for optimization |

#### Interview Tools
| `suggest` | Propose changes | 建议修改 |
#### Interview Tools

| Tool | Description |
|------|-------------|
| `start_interview` | Opening and first question |
| `ask_question` | Ask the next non-coding question |
| `ask_coding_question` | Send coding problem to editor (with starter_code) |
| `end_interview` | Final score, per-round evaluation, improvement actions |

### Data Storage / 数据存储

Runtime data is stored under `src/services/data/` (gitignored):

```
src/services/data/
├── session_memory/
│   └── session_memory.sqlite3     → Agent conversation history (SQLite)
├── recent_resumes/
│   ├── recent_resumes_index.json  → Resume index (JSON)
│   └── {id}.resume.json           → Resume data per record
├── job_descriptions/
│   ├── job_descriptions_index.json → JD index (JSON)
│   └── {id}.txt                    → JD text per record
├── imports/
│   ├── imports_index.json         → Import index (JSON)
│   └── {id}.txt                    → Raw text per record
└── user_profiles/
    └── {id}.json                  → User profile data
```

### JD Repository / JD 数据库

| Component | Technology | Description |
|-----------|-----------|-------------|
| Store | FAISS (FlatIP index) | Vector similarity search |
| Embedding | fastembed BAAI/bge-small-zh-v1.5 | 512-dim Chinese-optimised vectors |
| Metadata | SQLite (inverted_tags table) | Filter by company, type, role, keyword |
| Seed data | `tests/fixtures/jds/*.json` | 87 campus JDs from major Chinese tech companies |
| Script | `scripts/seed_jds.py` | Load/refresh JD database |

## Data Flow / 数据流

### Resume Creation / 创建简历

```
User inputs (role, skills, background)
  → POST /api/v1/agent/recent-resumes/save
  → AI generates skeleton (buildResumeSkeleton)
  → Redirect to /tailor?resumeId={id}
```

### AI Tailoring / AI 定制

```
User message
  → POST /api/v1/agent/v3/sessions/{id}/turns:run (SSE)
  → Agent loop: IntentResolver → ChainPlanner → Tools → SelfChecker
  → SSE events streamed to frontend
  → Frontend applies changes to resume state
  → TemplatePreview re-renders with highlighted changes
```

### Layout Building / 排版编辑

```
User adjusts guidance settings in EditorPanel
  → React state updates → useEffect triggers
  → renderResumeHtmlFromLayout(resumeObj, guidance, sections)
  → html-renderer generates full HTML with CSS variables
  → PaginatedPreview renders page-by-page
```

### LaTeX Export / LaTeX 导出

```
User clicks "Copy LaTeX"
  → POST /api/v1/latex/tex (guidance + sections + resume_obj)
  → latex_gen builds Jinja2 template with guidance parameters
  → Returns .tex source
  → Frontend copies to clipboard + shows Overleaf modal
```

## Configuration / 配置

### Environment Variables / 环境变量

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | Primary LLM provider |
| `LLM_MODEL` | `gpt-4o` | Model name |
| `LLM_API_KEY` | — | API key |
| `LLM_API_BASE` | — | Custom endpoint |
| `LLM_MAX_TOKENS` | `4096` | Max output tokens |
| `LLM_TEMPERATURE` | `0.7` | Sampling temperature |
| `DEBUG` | `false` | Debug mode |
| `CORS_ORIGINS` | `["*"]` | CORS allowed origins |

### File-based Config / 文件配置

```
.hermes/
├── config.yaml     → Hermes agent config (not this project)
.env                → Environment variables for backend
requirements.txt    → Python dependencies
package.json        → Node.js dependencies
```
