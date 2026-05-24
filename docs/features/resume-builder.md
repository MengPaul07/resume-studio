# Resume Builder / 简历布局生成器

> Visual layout editor — real-time preview with per-page rendering, CSS variable pipeline, and LaTeX export.  
> 可视化排版编辑器 — 实时预览、逐页渲染、CSS 变量管道、LaTeX 导出。

---

## Overview / 概述

The Resume Builder provides fine-grained control over every aspect of resume layout. Changes are reflected instantly in a live preview that renders page-by-page with PDF-quality scaling.

简历生成器提供对简历排版的精细控制。修改实时反映在逐页渲染的预览中，支持 PDF 级缩放。

## Layout / 布局

```
┌──────────┬──────┬──────────────────────────┐
│ Templates│  │   │                          │
│ ──────── │     │   Live Preview            │
│ Built-in │  │   │   ┌──────────────────┐   │
│ Custom   │     │   │  Page 1           │   │
│ ──────── │  │   │  │  ──────────────── │   │
│ Save as  │     │   │  Header           │   │
│ template │  │   │  │  Experience       │   │
├──────────┤     │   │  Education        │   │
│          │  │   │  │  ...              │   │
│ Editor   │     │   └──────────────────┘   │
│ Panel    │  │   │                          │
│ ──────── │     │   ┌──────────────────┐   │
│ Page     │  │   │  │  Page 2           │   │
│ Canvas   │     │  │  ──────────────── │   │
│ Typogr.  │  │   │  │  Projects        │   │
│ Layout   │     │  │  Skills           │   │
│ Sections │  │   │  │  ...              │   │
│ Lists    │     │  └──────────────────┘   │
└──────────┴──────┴──────────────────────────┘
```

## Editor Panel / 编辑面板

### Page / 页面

| Control | Description | 说明 |
|---------|-------------|------|
| Page Count | Single-page / Two-page mode | 单页/双页切换 |
| Margins (mm) | Top, Bottom, Left, Right (6–18mm) | 上下左右边距 |

### Canvas / 画布

| Control | Description | 说明 |
|---------|-------------|------|
| Header Font | Serif / Sans / Mono | 标题字体 |
| Body Font | Serif / Sans / Mono | 正文字体 |
| Header Align | Center / Left | 标题对齐 |
| Accent Color | Custom color picker | 强调色 |
| Divider Color | Line/separator colour | 分割线颜色 |
| Header BG / Text | Background and text colours | 头部背景与文字颜色 |
| Name Size / Weight | Font size and boldness | 姓名大小与粗细 |

### Typography / 排版

| Control | Description | 说明 |
|---------|-------------|------|
| Body Size | Base font size | 正文字号 |
| Line Height | Line spacing multiplier | 行高倍数 |
| Section Gap | Spacing between sections | 段落间距 |
| Item Gap | Spacing within sections | 项目间距 |
| Contact Layout | Inline / Stacked | 联系方式单行/堆叠 |

### Layout / 布局

| Control | Description | 说明 |
|---------|-------------|------|
| Column Mode | Single / Double column | 单栏/双栏 |
| Left Column Width | Width ratio for left column | 左栏宽度比例 |
| Column Gap | Gap between columns | 栏间距 |
| Sidebar Background | Background colour for sidebar | 侧边栏背景色 |
| Photo | Show/hide, size, shape, position | 照片显示/大小/形状/位置 |

### Sections / 版块

| Control | Description | 说明 |
|---------|-------------|------|
| Section Order | Drag/click to reorder: Summary, Experience, Education, Projects, Research, Skills, Languages, Certifications, Awards | 拖拽/点击排序 |
| Visibility | Toggle each section on/off | 显示/隐藏 |
| Column | Toggle between left/right column | 左右栏切换 |

### Structure / 结构

| Control | Description | 说明 |
|---------|-------------|------|
| Heading Style | Underline / Left Bar / Boxed | 标题样式 |
| Heading Case | Upper / Title | 大小写 |
| Heading Size | Font size for section titles | 标题字号 |
| Date Position | Below Title / Inline Right / Bottom Inline | 日期位置 |
| Header Divider | Show/hide divider line | 标题分割线 |

### Lists / 列表

| Control | Description | 说明 |
|---------|-------------|------|
| Bullet Style | Disc / Square / Dash | 项目符号样式 |
| Bullet Indent | Left offset for bullets | 符号缩进 |
| Bullet Item Gap | Spacing between items | 项目间距 |
| Skills Layout | Vertical / Horizontal | 技能布局方向 |
| Tag Font Size | Size of tag pills | 标签字号 |
| Tag Gap / Padding | Spacing and padding | 标签间距/内边距 |
| Tag Border / BG | Border width and background | 标签边框/背景 |

### Compact Mode / 紧凑度

Five density levels (0–4) that scale spacing and line-height:

| Level | Label | Spacing | Line Height |
|-------|-------|---------|-------------|
| 0 | Off / 关闭 | 100% | 100% |
| 1 | Slight / 稍紧 | 85% | 97% |
| 2 | Moderate / 适中 | 70% | 92% |
| 3 | Compact / 紧凑 | 55% | 88% |
| 4 | Ultra / 极紧 | 40% | 85% |

## Template System / 模板系统

### Built-in Templates / 内置模板

- **Swiss Single** — Clean single-column layout. Default template.

### Custom Templates / 自定义模板

- Save current guidance + section config as a named template
- Stored in localStorage under `builder_custom_templates`
- Click to load, click × to delete
- Only guidance settings saved (sections not yet included)

### Save Behaviour / 保存行为

| Action | What It Saves | Where |
|--------|--------------|-------|
| **Save** (top button) | Full resume: resume_obj + output_html + layout_preferences | Backend API |
| **Save as Template** | Current guidance settings | localStorage |
| **Export HTML** | Download rendered HTML as `.html` file | Local download |
| **Export PDF** | Open print dialog with rendered HTML | Browser print |
| **Copy LaTeX** | Generate TeX source → clip to clipboard → modal with Overleaf link | Backend + clipboard |

## Preview / 预览

### Rendering / 渲染机制

- DOM-based rendering (no iframe) with `overflow: hidden` clipping
- `transform: scale()` for PDF-quality zoom
- `document.fonts.ready` waits for font loading
- `ResizeObserver` + `MutationObserver` for pagination triggers

### Pagination / 分页

- Custom `use-pagination.ts` hook with:
  - Item protection (keep entries intact)
  - Heading orphan detection
  - 50% minimum page fill
  - 150ms debounce on resize
- Offset-based page display with `actualContentHeight`

### CSS Variables / CSS 变量管道

All layout parameters are exposed as CSS custom properties (`--r-*`) via `buildCssVariables()`:

```css
--r-body-size: 10pt;
--r-line-height: 1.5;
--r-section-gap: 12px;
--r-margin-top: 12mm;
--r-heading-style: underline;
/* ... 32+ variables total */
```

## LaTeX Export / LaTeX 导出

- One-click "Copy LaTeX" button
- Backend generates TeX from `RenderGuidanceSettings` parameters
- Document class: `article` + `fontspec` + TeX Gyre fonts
- Two-column layout via automatic left/right section assignment
- Compatible with XeLaTeX compiler (one-click Overleaf link)
- Output matches HTML rendering via shared parameter set

## Interoperability / 互操作

- **Open in Tailor**: Click "AI Tailor" button → opens the same resume in Tailor Chat
- **Resume selector**: Dropdown at top to switch between recent resumes
- **Guidance persistence**: Layout settings saved with resume in `layout_preferences.metadata`
