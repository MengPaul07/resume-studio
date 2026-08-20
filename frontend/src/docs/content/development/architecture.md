---
title: 系统架构
description: 从浏览器状态到 Agent Loop、SSE 和存储边界，建立 Resume Studio 的系统心智模型。
category: development
order: 10
---

# 系统架构

Resume Studio 把“内容事实”和“表达形式”分开：简历 JSON 是事实，Tailor 产生的是可审核变更，Builder 负责把同一份事实排成可导出的页面。

## 一次请求的路径

```text
浏览器页面
  → API client（X-User-Id / X-User-Lang）
  → FastAPI route
  → Agent / resource service
  → LiteLLM 或本地存储
  → JSON / SSE 回到页面
```

## 四个边界

### 1. 页面与状态

React 页面负责交互状态、乐观预览和本地偏好。最近简历、导入记录、职位目标和面试历史优先使用 localStorage；路由参数只保存当前工作区需要的 ID。

### 2. API 与 Agent

FastAPI 以 `/api/v1` 为统一前缀。资源路由负责导入、保存和读取；v3 路由负责会话、turn、建议应用和模板渲染。一个 Tailor turn 由 IntentResolver、ChainPlanner、工具执行和 SelfChecker 组成。

### 3. 实时输出

Agent turn 使用 Server-Sent Events（SSE）把规划、工具调用、建议和最终回答按顺序推送给前端。SSE 适合单向增量输出，断线后可用 session ID 查询状态或恢复暂停的 turn。

### 4. 渲染与导出

Builder 通过 `RenderGuidanceSettings` 生成 CSS 变量，再由前端分页渲染 A4 预览。HTML 可直接打印为 PDF；LaTeX API 复用同一组 guidance 参数生成 TeX 源码。

## 主要存储

| 数据 | 当前实现 | 边界 |
| --- | --- | --- |
| 简历与导入 | 浏览器 localStorage + 后端资源 API | 浏览器是个人工作流的首选来源 |
| Agent session | SQLite / session service | 只保存服务端会话所需内容 |
| JD 检索 | FAISS + embedding + SQLite 元数据 | 可选能力，索引为空时不阻塞主流程 |
| 导出结果 | 浏览器下载或 API 返回源代码 | 不默认代替用户发布 |

## 设计原则

1. 事实修改必须可见、可撤销，敏感字段需要用户确认。
2. 事件流与最终状态分离，前端可以渐进展示而不牺牲一致性。
3. 供应商通过 LiteLLM 适配，业务代码不绑定单一模型厂商。
4. 不把个人简历或 API Key 写入前端构建产物和公开文档。
