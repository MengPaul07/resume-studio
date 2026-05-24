# AI Tailor / AI 定制对话

> AI-powered resume refinement — natural language editing, JD matching, change tracking, and auto-apply.  
> AI 驱动的简历优化 — 自然语言编辑、JD 匹配、修改追踪、自动应用。

---

## Overview / 概述

AI Tailor is a chat-based interface where you describe what you want to change in your resume, and an AI agent executes a chain of tools to observe, suggest, refine, and compose the changes. All modifications are tracked, previewable, and reversible.

AI Tailor 是基于对话的界面。你描述想对简历做的修改，AI agent 执行工具链来观察、建议、优化并组合修改。所有修改可追踪、预览、撤销。

## Layout / 布局

```
┌──────────┬──────────────────────────┬──────────┐
│ Sessions │  Chat                    │  Preview │
│ ──────── │  ────────────────────    │  ─────── │
│ New      │  User: "优化我的summary" │  Resume  │
│ History  │  AI:  [changes applied]  │  preview │
│          │                          │  with    │
│ JD Panel │  ┌────────────────────┐  │  inline  │
│ ──────── │  │ Change Toolbar     │  │  editing │
│ Target   │  │ ├ Auto-applied     │  │          │
│ JD match │  │ ├ Low confidence   │  │          │
│          │  │ └ Fact issues      │  │          │
│ Quick    │  └────────────────────┘  │          │
│ Prompts  │                          │          │
│ ──────── │  Input: ________ [Send]  │          │
│ Templates│                          │          │
└──────────┴──────────────────────────┴──────────┘
```

## Features / 功能

### Chat Interface / 对话界面

- **Natural language input**: Type what you want to change in plain language
- **Ctrl+Enter** to send; **↑↓** for input history
- **Markdown rendering** in assistant messages (bold, lists, code blocks)
- **Loading indicators**: Thinking, planning chain, self-checking states

自然语言输入。Ctrl+Enter 发送，↑↓ 切换历史。助手消息支持 Markdown 渲染。

### AI Agent Pipeline / Agent 流水线

```
User Message → Agent Loop (LLM picks tools: read_resume, edit_field, add_entry, compose, etc.) → Response
```

| Stage | Description | 说明 |
|-------|-------------|------|
| **IntentResolver** | Classifies user intent: explicit_edit, broad_edit, fact_edit, analysis_only, general_chat | 意图分类 |
| **ChainPlanner** | Selects tool chain based on intent | 工具链选择 |
| **Tool Execution** | Runs observe → suggest → refine → compose tools sequentially | 顺序执行工具 |
| **SelfChecker** | Validates output quality: pass → deliver; fail → retry once; fail_soft → deliver with warning | 质量自检 |

### Intent → Chain Mapping / 意图→链映射

| Intent | Chain | Example |
|--------|-------|---------|
| `explicit_edit` | observe → refine → compose | "把我的title改成Senior Engineer" |
| `broad_edit` | observe → suggest → refine → compose | "优化我的项目经历，加一些量化数据" |
| `fact_edit` | observe → suggest → compose | "我的电话是 138xxxx" (sensitive data) |
| `analysis_only` | observe → analyze → compose | "分析我的简历有什么问题" |
| `general_chat` | observe → compose | "你好，介绍一下你自己" |

### Change Tracking / 修改追踪

All modifications are classified into three confidence tiers:

| Tier | Description | Behaviour |
|------|-------------|-----------|
| **Auto-apply** | High confidence changes | Applied immediately, shown in green |
| **Low confidence** | Suggested changes needing review | Shown with accept/decline buttons |
| **Fact issues** | Sensitive data changes | Requires explicit confirmation |

所有修改分三个置信度层级。高置信度自动应用，低置信度需审核，敏感数据需确认。

### Inline Editing / 行内编辑

All resume fields in the preview are double-click editable:

| Section | Editable Fields |
|---------|----------------|
| Header | Name, Title, Email, Phone, Location, Website, LinkedIn, GitHub |
| Work Experience | Title, Company, Location, Years, Description bullets |
| Projects | Name, Role, Years, Description bullets |
| Research | Name, Role, Institution, Years, Description bullets |
| Education | Institution, Degree, Years |
| Additional | Skills, Languages, Certifications, Awards |
| Summary | Full text |

Double-click any field → inline edit input → Enter to save, Esc to cancel.  
Hover shows "(double-click to edit)" hint.

双击任意字段 → 行内编辑输入框 → Enter 保存，Esc 取消。悬停显示提示。

### JD Matching / JD 匹配

- **Target JD Panel**: Load a job description from the built-in JD library
- **JD Library**: 87+ Chinese tech company JDs from Alibaba, ByteDance, Tencent, etc.
- **JD-aware tailoring**: AI considers the target JD when making suggestions
- JD fields: Title, Company, Location, Category, Keywords, Responsibilities, Requirements

从内置 JD 库加载职位描述。AI 在建议时会考虑目标 JD。

### Quick Prompts / 快捷操作

Pre-built actions for common tasks:

| Prompt | Description |
|--------|-------------|
| Analyze Resume | Full resume analysis |
| Improve Summary | Polish summary text |
| Enhance Bullets | Strengthen bullet points |
| Add Metrics | Add quantified data |
| Fix Formatting | Fix formatting issues |
| Tailor for JD | Match against target JD |
| Translate CN/EN | Chinese/English translation |
| Polish Language | Language refinement |
| Add Skills | Supplement skills |
| Check Consistency | Consistency check |

### Export / 导出

- **Save Tailor**: Persist changes to backend
- **Undo**: Rollback the last turn
- Changes persist across sessions via `session_memory`

保存修改到后端。撤销上一轮。修改跨会话持久化。

## State / 状态管理

| State | Storage | Purpose |
|-------|---------|---------|
| Resume data | Backend + React state | Current resume object |
| Session | Backend `session_memory` | Conversation history |
| JD target | localStorage `tailor_target_jd` | Active target JD |
| Pending changes | React state | Unapplied suggestions |
| Turn snapshots | React state | Pre-modification state for undo |
