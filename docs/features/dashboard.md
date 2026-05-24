# Dashboard / 仪表盘

> Central workspace — manage imports, resumes, and access all tools.  
> 工作区入口 — 管理导入、简历，访问所有功能。

---

## Layout / 布局

```
┌──────────────────────────────────────────────┐
│  Resume Studio                               │
│  Build, refine and ship structured resumes.  │
├──────────────┬──────────────┬────────────────┤
│  Imports     │  Resumes     │  Studio Flow   │
│  ─────────   │  ─────────   │  ────────────  │
│  PDF/DOC/DOCX│  Recent list │  [Build]       │
│  file list   │  click→open  │  [Import]      │
│              │              │  [Structure]   │
│              │              │  [Tailor]      │
├──────────────┴──────────────┴────────────────┤
│  Engine status · LLM · Parser · PDF          │
└──────────────────────────────────────────────┘
```

## Sections / 区块

### 1. Imports / 导入区

- Lists all uploaded files (PDF, DOC, DOCX)
- Each import shows raw text extracted by the parser
- Click to process with AI and create a resume skeleton

列出所有已上传文件。每个导入显示解析器提取的原始文本。点击用 AI 处理并生成简历框架。

### 2. Resumes / 简历区

- Recent resumes sorted by last modified
- Click to open in Resume View or AI Tailor
- Shows title, status (draft / ready), and source

最近简历按最后修改排序。点击打开简历预览或 AI 定制。显示标题、状态（草稿/就绪）和来源。

### 3. Studio Flow / 操作流程

| Action | Description | 说明 |
|--------|-------------|------|
| **Build** | Create resume from scratch via AI interview | 从零创建 — AI 对话引导 |
| **Import** | Upload PDF/DOCX for AI parsing | 上传文件让 AI 解析 |
| **Structure** | Open builder to adjust layout | 打开生成器调整布局 |
| **Tailor** | Open existing resume for AI refinement | 打开已有简历优化 |

### 4. Engine Status / 引擎状态

Shows real-time availability of core services:
- LLM connectivity (model + API key status)
- Parser readiness (document import)
- PDF readiness (export)

显示核心服务实时状态。

## Interactions / 交互

- **Click import item** → triggers AI parsing → creates resume skeleton → redirects to Tailor
- **Click resume item** → opens Resume View (builder)
- **Click Tailor button** → opens resume in AI Tailor with that resume active
- **Workflow Console** → expands to show full Studio Flow panel

---

## State / 状态管理

| State | Storage | Purpose |
|-------|---------|---------|
| Import list | Backend API | `GET /api/v1/resources/imports` |
| Resume list | Backend API | `GET /api/v1/resources/recent-resumes` |
| Last selected | URL params | `?resumeId=xxx` |
