---
title: Resume Studio 文档
description: 从本地启动到求职工作流，快速理解 Resume Studio 的产品与工程边界。
category: start
order: 1
---

# Resume Studio 文档

Resume Studio 是一个 AI 原生的求职工作台：把简历导入、结构化编辑、职位匹配、对话式优化、版式生成和模拟面试放进同一条工作流。

这份文档面向两类读者：想先把产品跑起来的人，以及希望理解 Agent、SSE、浏览器存储和渲染管道的开发者。

## 推荐阅读路径

1. [本地启动](./development/setup.md)：安装 Python/Node，配置模型并启动前后端。
2. [Dashboard](./features/dashboard.md)：理解导入、简历列表和工作流入口。
3. [AI Tailor](./features/ai-tailor.md)：理解 Agent 如何提出、追踪和应用修改。
4. [系统架构](./development/architecture.md)：把页面、API、Agent 和存储串起来。

## 产品边界

- 简历内容、导入文件和职位描述优先保存在浏览器；后端只处理当前请求需要的数据。
- 模型调用由 LiteLLM 统一，实际 API Key 由部署环境或本地配置提供。
- HTML 是默认导出路径；LaTeX 作为源代码导出，交给 Overleaf 或本地 XeLaTeX 编译。
- 这是一个可自托管的开源项目，不承诺替用户投递或替用户编造经历。

## 文档约定

代码路径以仓库根目录为基准，API 路径默认带 `/api/v1` 前缀。页面文档描述用户能看到的行为，开发文档描述当前实现边界；如果两者冲突，以源码和自动生成的 OpenAPI 为准。
