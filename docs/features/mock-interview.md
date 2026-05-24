# Mock Interview / 模拟面试

> Realistic interview practice — 12 interviewer presets, coding problems, code editor, and AI coach review.  
> 真实模拟面试练习 — 12 位面试官预设、编程题、代码编辑器、AI 教练复盘。

---

## Overview / 概述

The Mock Interview feature simulates real technical interviews. An AI interviewer asks questions based on your resume and target position. You answer in natural language or write code in a built-in editor. After the interview, an AI coach reviews your performance.

模拟面试功能模拟真实技术面试。AI 面试官根据你的简历和目标职位提问。你用自然语言回答或在内置编辑器中写代码。面试结束后，AI 教练复盘你的表现。

## Interview Setup / 面试设置

### Step 1: Choose Interviewer / 选择面试官

12 preset interviewers with distinct styles, languages, and specialities:

| # | Name | Speciality | Language | Rounds |
|---|------|-----------|----------|--------|
| 1 | **Li Yan** | ByteDance Backend Bar Raiser | 中文 | 7 |
| 2 | **Maya Chen** | FAANG System Design Coach | English | 6 |
| 3 | **Helena Brooks** | Investment Bank Risk Panelist | English | 6 |
| 4 | **Qiao Lin** | Campus Interview Mentor | 中文 | 5 |
| 5 | **Sofia Rivera** | ML Engineering Panelist | English | 6 |
| 6 | **Dr. Aisha Patel** | Healthcare AI Safety Reviewer | English | 6 |
| 7 | **Prof. Eleanor Park** | Research Faculty Interviewer | English | 7 |
| 8 | **Marcus Reed** | Management Consulting Case Lead | English | 5 |
| 9 | **Priya Nair** | Product Growth Panelist | English | 6 |
| 10 | **Carlos Mendes** | Game Engine Technical Director | English | 6 |
| 11 | **Kenji Sato** | Robotics Systems Reviewer | English | 6 |
| 12 | **Grace Okafor** | Public Sector Digital Services Lead | English | 5 |

### Step 2: Configure / 配置参数

| Setting | Options | 选项 |
|---------|---------|------|
| Company | FAANG / Startup / Enterprise / Consulting | FAANG / 创业公司 / 国内大厂 / 咨询公司 |
| Level | Junior / Mid / Senior / Staff | 初级 / 中级 / 高级 / 专家 |
| Role | Backend / Frontend / Fullstack / ML / Infra / General | 后端 / 前端 / 全栈 / 机器学习 / 基础架构 / 通用 |
| Style | Balanced / High Pressure / Collaborative | 均衡 / 高压 / 协作 |
| Depth | Shallow / Moderate / Deep | 浅层 / 中等 / 深度 |
| Length | Micro (3r) / Short (5r) / Standard (7r) / Deep (10r) / Marathon (14r) | 极简/简短/标准/深度/马拉松 |
| Language | 中文 / English | 中文/English |
| Focus | Weight distribution: Algo & DS, OS/Network/DB, System Design, Projects, Behavioral, Language-specific | 权重分配 |

### Step 3: Custom Preferences / 自定义偏好

Free-text field (max 600 chars) sent to the interviewer. Examples:
- "Focus on distributed systems. Be strict about metrics."
- "Ask in Chinese but keep technical terms in English."

自由文本（最多 600 字），发送给面试官。

## Interview Flow / 面试流程

### In-Session / 面试中

```
┌──────────────────────────────────────────┐
│  Mock Interview                  [Notes] │
│  Session #1 · Running…                   │
├──────────────────────────────────────────┤
│                                          │
│  ┌─────────────────────────────────┐     │
│  │ Interviewer: Tell me about your │     │
│  │ most challenging project...     │     │
│  └─────────────────────────────────┘     │
│                                          │
│              ┌──────────────────┐        │
│              │ User: In my      │        │
│              │ previous role... │        │
│              └──────────────────┘        │
│                                          │
│  ┌─────────────────────────────────┐     │
│  │ Interviewer: How did you       │     │
│  │ handle the scaling issue?      │     │
│  │ [Coding Problem →]             │     │
│  └─────────────────────────────────┘     │
│                                          │
├──────────────────────────────────────────┤
│  [Your answer…                    ] [→]  │
└──────────────────────────────────────────┘
```

### Key Interactions / 关键交互

| Action | Shortcut | Description |
|--------|----------|-------------|
| Send answer | Enter | Submit your response |
| New line | Shift+Enter | Line break in input |
| Start interview | Say "开始" / "Start" | Kickoff message |
| End interview | Say "结束" / "end" | Trigger report generation |
| Open coding | Button click | Toggle code/problem panel |

### Coding Problems / 编程题

When the interviewer sends a coding question:

- **Problem display**: Title, difficulty, description with markdown + LaTeX rendering
- **Code Editor**: Syntax-aware code editor with language detection
- **Submit**: Code is sent back to the interviewer as a formatted code block
- **Pending indicator**: Amber dot when a problem is waiting for your solution

面试官发来时显示题目（支持 markdown + KaTeX 数学公式）。代码编辑器支持语法高亮。提交后代码以格式化块发回。

### Code Editor / 代码编辑器

Two editor modes accessible during the interview:

| Mode | Description | 说明 |
|------|-------------|------|
| **Code** | Full code editor with language detection, submit solution | 代码编辑，提交解答 |
| **Writing** | Plain text / markdown for general note-taking | 纯文本/笔记 |

### Notes Panel / 笔记面板

A separate writing panel for jotting down thoughts, notes, or draft responses during the interview.

独立写作面板，面试中记录想法或草稿。

## Review Mode / 复盘模式

After the interview ends (report generated):

### Report / 面试报告

- AI-generated score and breakdown
- Strengths and weaknesses identified
- Specific question-by-question analysis
- Rendered in formatted markdown

AI 生成的评分和详细分析。按题目逐一分析优缺点。

### AI Coach / AI 教练

- **Enter Review Mode**: Switch from interviewer to coach persona
- Ask the coach specific questions about your performance
- Get targeted advice: "How should I improve my system design answers?"
- Role-play specific questions again

进入复盘模式后，切换到教练角色。可询问具体问题的表现和改进建议。

### Interview History / 面试记录

- All past sessions saved with date, score, and summary
- Click any session to replay the transcript
- Session numbering (Session #1, #2, ...)

所有历史面试保存，含日期、评分、摘要。点击可重温对话记录。

## Persistence / 持久化

| Data | Storage | Notes |
|------|---------|-------|
| In-progress session | localStorage `interview_in_progress` | Auto-saved on each state change |
| Completed sessions | localStorage `interview_history` | Saved on interview end |
| Last setup config | localStorage `interview_setup_last` | Pre-fills next setup |
| Server session | Backend API | Actual conversation stored server-side |

If you close the interview modal mid-session, a banner on the setup screen offers to continue or discard.

如果面试中途关闭，重新打开时会在设置页显示"继续"横幅。

## Keyboard Shortcuts / 快捷键

| Shortcut | Action | 操作 |
|----------|--------|------|
| Enter | Send message | 发送消息 |
| Shift+Enter | New line | 换行 |
| Esc | Cancel edit | 取消编辑 |
| Ctrl+Enter (code editor) | Submit solution | 提交解答 |
