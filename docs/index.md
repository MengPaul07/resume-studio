# Resume Studio — AI Resume Builder & Mock Interview Platform

> AI-powered resume builder, optimizer, and mock interview platform.  
> AI 驱动的简历构建、优化与模拟面试平台。

---

## Overview / 概述

Resume Studio is a full-stack application that helps you create professional resumes from scratch, optimize existing ones with AI, and practice interviews — all within a single workspace.

Resume Studio 是一个全栈应用，帮助你从零构建专业简历、用 AI 优化现有简历、并练习模拟面试 — 全部在一个工作区内完成。

### Key Features / 核心功能

| Feature | Description |
|---------|-------------|
| [Dashboard](./features/dashboard.md) | Central workspace — manage imports, resumes, and access all tools |
| [Resume Builder](./features/resume-builder.md) | Visual layout editor — customise typography, spacing, colors, section order |
| [AI Tailor](./features/ai-tailor.md) | AI-powered resume refinement — natural language editing, JD matching, auto-apply |
| [Mock Interview](./features/mock-interview.md) | Realistic interview practice — 12 interviewer presets, coding problems, review mode |
| *LaTeX Export* | One-click LaTeX copy for Overleaf — XeLaTeX compatible, matches HTML output |
| *Internationalisation* | Full zh-CN / en-US support across all features |
| *JD Library* | 87+ Chinese tech company job descriptions for targeted tailoring |

### Tech Stack / 技术栈

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + TypeScript + Tailwind CSS v4 + Vite |
| Backend | Python 3.13 + FastAPI + LiteLLM |
| AI/ML | Function-calling agent loop with autonomous tool selection |
| Search | FAISS vector store + BGE-small-zh embedding for JD matching |
| Desktop | Tauri (optional) for native Windows builds |

### Quick Links / 快速链接

- [Development Setup](./development/setup.md) — Run the project locally
- [Architecture](./development/architecture.md) — System design and data flow
- [API Reference](http://localhost:8000/docs) — Auto-generated OpenAPI docs (when running)

---

## Navigation / 导航

1. **[Dashboard](./features/dashboard.md)** — 仪表盘 / 工作区入口
2. **[Resume Builder](./features/resume-builder.md)** — 简历布局生成器 / 可视化排版
3. **[AI Tailor](./features/ai-tailor.md)** — AI 定制对话 / 智能优化
4. **[Mock Interview](./features/mock-interview.md)** — 模拟面试 / 编程题 + 复盘
5. **[Settings](./features/settings.md)** — 设置 / LLM 配置
6. **[Development](./development/)** — 开发文档 / 架构与配置
