---
title: Resume Builder 版式生成器
description: 用实时预览、分页和 CSS 变量调整简历版式，并导出 HTML 或 LaTeX。
category: features
order: 22
---

# Resume Builder 版式生成器

Builder 处理的是“如何表达”，不是“事实是什么”。左侧是模板与控制面板，中央是编辑参数，右侧按页显示 A4 预览。

## 可调参数

- 页面数量与四边页边距
- 标题/正文/等宽字体、字号、行高和段落间距
- 单栏/双栏、栏宽、分割线和强调色
- 版块顺序、可见性、列归属和日期位置
- 列表符号、技能标签和紧凑模式

所有参数先进入 `RenderGuidanceSettings`，再映射为 `--r-*` CSS 变量。这样 HTML 预览和 LaTeX 导出使用同一套语义，而不是维护两份互相漂移的模板。

## 分页规则

预览等待字体加载后计算分页，保护条目不被拆开，避免标题落在页尾，并在窗口变化时重新计算。内容过长时显示溢出提示，不会静默裁掉最后一段经历。

## 导出

| 操作 | 结果 |
| --- | --- |
| Export HTML | 下载当前渲染结果 |
| Export PDF | 打开浏览器打印对话框 |
| Copy LaTeX | 请求 TeX 源码并复制到剪贴板，可粘贴到 Overleaf |

## 相关 API

- `POST /api/v1/agent/v3/template:inspect`
- `POST /api/v1/agent/v3/template:render`
- `POST /api/v1/agent/v3/template:export-latex`
