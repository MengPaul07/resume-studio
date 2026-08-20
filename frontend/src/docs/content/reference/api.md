---
title: API 参考
description: Resume Studio 当前稳定的健康检查、资源、Agent、模板和导出接口。
category: reference
order: 30
---

# API 参考

后端默认监听 `127.0.0.1:8000`，公开 API 前缀是 `/api/v1`。每个浏览器用户请求会带 `X-User-Id` 与 `X-User-Lang`，服务端据此隔离个人工作流上下文。

## 健康检查

```http
GET /health
```

返回 `status`、版本和应用名，用于反向代理或进程监控。

## Agent 会话

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/api/v1/agent/v3/sessions` | 创建会话 |
| GET | `/api/v1/agent/v3/sessions/{id}` | 读取会话 |
| POST | `/api/v1/agent/v3/sessions/{id}/turns:run` | 运行一轮并以 SSE 返回 |
| POST | `/api/v1/agent/v3/sessions/{id}/turns:resume` | 恢复暂停 turn |
| POST | `/api/v1/agent/v3/sessions/{id}/actions:apply` | 应用建议 |
| POST | `/api/v1/agent/v3/sessions/{id}/actions:reject` | 拒绝建议 |
| POST | `/api/v1/agent/v3/sessions/{id}/rollback` | 回滚版本 |

## 资源

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/api/v1/agent/import-file` | 上传并解析文件 |
| POST | `/api/v1/agent/run-import` | 从导入文字生成简历 |
| GET/DELETE | `/api/v1/agent/imports/{id}` | 读取/删除导入记录 |
| GET/POST/DELETE | `/api/v1/agent/recent-resumes` | 简历列表、保存、删除 |
| GET/POST/DELETE | `/api/v1/agent/job-descriptions` | JD 列表、保存、删除 |
| POST | `/api/v1/agent/test-llm` | 测试模型连接 |

## 模板与导出

```text
POST /api/v1/agent/v3/template:inspect
POST /api/v1/agent/v3/template:render
POST /api/v1/agent/v3/template:export-latex
POST /api/v1/latex/tex
```

开发时可打开 `http://127.0.0.1:8000/api-docs` 查看 FastAPI 自动生成的请求 schema。公开产品文档使用 `/docs`，两者互不冲突。SSE 客户端必须持续读取流，并在断线时用 session 查询，而不是重复提交同一个 turn。
