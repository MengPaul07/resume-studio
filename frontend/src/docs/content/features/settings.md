---
title: Settings 模型设置
description: 配置 LiteLLM 提供商、模型、API 地址和连接测试。
category: features
order: 24
---

# Settings 模型设置

Settings 管理驱动简历创建、Tailor 和模拟面试的模型连接。页面里的 Provider 预设会保存到浏览器，并在请求中以 `llm_config` 发送；服务器 `.env` 提供没有被页面覆盖时的默认值。

## 配置项

| 配置 | 说明 |
| --- | --- |
| Provider | OpenAI-compatible、Anthropic、Google、DeepSeek、GLM、MiniMax 或 Custom |
| API Base | 模型服务的 HTTP endpoint |
| Model | LiteLLM 格式的模型名 |
| API Key | 只放在浏览器本地配置或部署环境，不写入仓库 |
| Max Tokens / Temperature | 输出长度与采样策略 |

## 连接测试

Test API Connectivity 会发送最小请求，显示成功/失败和响应时间。失败时按 endpoint、模型名、Key 和额度顺序排查；解析器和浏览器打印不依赖模型，仍可单独使用。

## 安全边界

不要把 API Key 填进截图、Markdown 或提交到仓库。浏览器 localStorage 只保存当前设备的配置；生产环境应优先使用 HTTPS，并限制 CORS 来源。
