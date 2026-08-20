---
title: Dashboard 工作台
description: 管理导入文件、最近简历和四条主要求职工作流。
category: features
order: 20
---

# Dashboard 工作台

Dashboard 是 Resume Studio 的起点：左侧看导入和最近简历，中间继续上次工作，右侧进入创建、优化、排版和面试。

## 四条工作流

| 入口 | 适合场景 | 下一步 |
| --- | --- | --- |
| Build | 从空白资料开始 | AI 对话收集经历，生成简历骨架 |
| Import | 已经有 PDF/DOCX | 解析文字，再进入 Tailor |
| Structure | 内容已稳定 | 进入 Builder 调整版式和分页 |
| Tailor | 想针对职位优化 | 绑定 JD，逐轮审核建议 |

## 导入与简历

导入文件会先提取原始文字，不会直接覆盖已有简历。确认处理后，系统生成结构化 `resume_obj`，用户可以在 Tailor 中核对事实，再保存为最近简历。

最近简历按更新时间排列。打开某条记录会进入 Builder；选择 Tailor 会保留同一份 resume ID，避免优化与预览之间产生副本分叉。

## 引擎状态

页面状态只回答三个问题：模型是否可连、解析器是否就绪、当前浏览器能否导出 PDF。状态异常时仍可打开本地内容和 Builder，不会把只读页面锁死。

## 相关 API

- `GET /api/v1/agent/imports`
- `POST /api/v1/agent/import-file`
- `GET /api/v1/agent/recent-resumes`
- `POST /api/v1/agent/recent-resumes/save`
