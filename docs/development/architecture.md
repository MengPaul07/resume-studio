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
│  │  /api/v1/v3/*     → Agent loop, chat, interview   │   │
│  │  /api/v1/resources/* → CRUD for data              │   │
│  │  /api/v1/latex/*   → LaTeX generation             │   │
│  └──────┬────────────────────────┬──────────────────┘   │
│         │                        │                       │
│         ▼                        ▼                       │
│  ┌──────────────┐    ┌──────────────────────┐           │
│  │ Agent Engine │    │   Data Services      │           │
│  │ ──────────── │    │   ─────────────────  │           │
│  │ IntentResolv │    │   RecentResumeStore  │           │
│  │ ChainPlanner │    │   SessionStore       │           │
│  │ ToolRunner   │    │   JdRepository       │           │
│  │ SelfChecker  │    │   LaTeX Generator    │           │
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
| `/resumes/:id` | `ResumeViewPage` | Layout builder with preview |
| `/tailor` | `TailorChatPage` | AI refinement chat |
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
| POST | `/api/v1/v3/session/start` | Start a new agent session |
| POST | `/api/v1/v3/turn/chat` | Send message + run agent loop (SSE) |
| GET | `/api/v1/v3/session/{id}/content` | Get session history |
| POST | `/api/v1/v3/turn/rollback` | Rollback last turn |

#### Resources (CRUD)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/resources/recent-resumes` | List recent resumes |
| POST | `/api/v1/resources/recent-resumes` | Create/update resume |
| GET | `/api/v1/resources/recent-resumes/{id}` | Get resume by ID |
| DELETE | `/api/v1/resources/recent-resumes/{id}` | Delete resume |
| GET | `/api/v1/resources/job-descriptions` | List JDs |
| POST | `/api/v1/resources/job-descriptions` | Create JD |
| GET | `/api/v1/resources/job-descriptions/{id}` | Get JD by ID |
| DELETE | `/api/v1/resources/job-descriptions/{id}` | Delete JD |
| GET | `/api/v1/resources/imports` | List imported files |
| POST | `/api/v1/resources/imports` | Upload file |
| DELETE | `/api/v1/resources/imports/{id}` | Delete import |

#### LaTeX

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/latex/tex` | Generate LaTeX source |

### Agent Engine / Agent 引擎

```
                     ┌─────────────┐
User Message ──────→│IntentResolver│
                     │  (LLM call)  │
                     └──────┬──────┘
                            │ intent
                     ┌──────▼──────┐
                     │ChainPlanner │
                     │ (deterministic)│
                     └──────┬──────┘
                            │ tool_chain
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌─────────┐  ┌─────────┐  ┌─────────┐
        │ observe │→ │ suggest │→ │ compose │
        └─────────┘  └─────────┘  └─────────┘
              │             │             │
              └─────────────┼─────────────┘
                            │ output
                     ┌──────▼──────┐
                     │SelfChecker  │
                     │  (LLM call)  │
                     └──────┬──────┘
                            │ pass / retry / fail_soft
                     ┌──────▼──────┐
                     │  Response   │
                     └─────────────┘
```

#### Tools / 工具函数

Core tools executed by `TurnRunner`:

| Tool | Function | Description |
|------|----------|-------------|
| `observe` | Read current resume state | 读取当前简历 |
| `suggest` | Propose changes | 建议修改 |
| `refine` | Apply and polish suggestions | 应用并润色 |
| `analyze` | Generate analysis report | 生成分析报告 |
| `compose` | Assemble final response | 组装最终回复 |

Interview-specific tools:

| Tool | Function | Description |
|------|----------|-------------|
| `interview_question` | Generate next question | 生成下一个问题 |
| `coding_question` | Generate coding problem (SSE) | 生成编程题 |
| `interview_review` | Analyse performance | 复盘分析 |

### Data Storage / 数据存储

```
src/services/data/
├── session_memory/
│   └── session_memory.sqlite3     → Agent conversation history (SQLite)
├── recent_resumes/
│   ├── recent_resumes_index.json  → Resume index (JSON)
│   └── {id}.resume.json           → Resume data per record
│   └── {id}.html                  → Rendered HTML per record
│   └── {id}.md                     → Markdown per record
├── user_profiles/
│   └── {id}.json                  → User profile data
└── imports/
    └── {id}.json                  → Imported file metadata
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
  → POST /api/v1/resources/recent-resumes
  → AI generates skeleton (buildResumeSkeleton)
  → Redirect to /tailor?resumeId={id}
```

### AI Tailoring / AI 定制

```
User message
  → POST /api/v1/v3/turn/chat (SSE)
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
