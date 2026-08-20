---
title: AI Tailor 对话优化
description: 用可追踪、可撤销的对话式 Agent 优化简历并匹配目标职位。
category: features
order: 21
---

# AI Tailor 对话优化

AI Tailor 不是“生成一份新简历”的黑盒，而是一条可检查的变更流水线。用户提出目标，Agent 读取当前事实，决定工具链，输出建议并等待必要的确认。

## 一轮 turn

```text
用户请求
  → IntentResolver
  → ChainPlanner
  → read / search / edit tools
  → SelfChecker
  → SSE 增量事件 + 变更摘要
```

常见意图包括：明确字段修改、整段经历优化、敏感事实修改、只读分析和普通问答。只读分析不会偷偷改写简历。

## 三种变更状态

| 状态 | 行为 |
| --- | --- |
| Auto-apply | 高置信度、非敏感的表达优化，可直接显示在预览中 |
| Review | 低置信度建议，需要用户接受或拒绝 |
| Fact confirmation | 电话、时间、公司等事实字段，必须显式确认 |

## JD 匹配

Target JD Panel 可以从职位库加载目标职位。Agent 将职位标题、关键词、职责和要求作为上下文，但不会凭空增加用户没有提供的经历；不确定的内容会标记为建议或事实问题。

## 撤销与恢复

每个 turn 都有前后版本。用户可以拒绝建议、回滚上一轮，或在 SSE 中断后用 session ID 恢复。最终保存仍由用户触发。

## 相关 API

- `POST /api/v1/agent/v3/sessions`
- `POST /api/v1/agent/v3/sessions/{id}/turns:run`
- `POST /api/v1/agent/v3/sessions/{id}/actions:apply`
- `POST /api/v1/agent/v3/sessions/{id}/rollback`
