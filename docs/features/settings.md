# Settings / 设置

> LLM provider configuration, model presets, connectivity testing, and system status.  
> LLM 提供商配置、模型预设、连接测试、系统状态。

---

## Overview / 概述

The Settings page manages the backend LLM configuration that powers all AI features — resume creation, tailoring, and interviews.

设置页管理驱动所有 AI 功能的后端 LLM 配置。

## Layout / 布局

```
┌────────────────────────────────────────┐
│  Settings                               │
│  Model presets and connectivity         │
├────────────────────────────────────────┤
│  LLM Provider                           │
│  ┌──────────────────────────────────┐   │
│  │ [OpenAI] [Anthropic] [DeepSeek] │   │
│  │ [Google] [GLM] [MiniMax] ...    │   │
│  └──────────────────────────────────┘   │
│                                         │
│  API Configuration                      │
│  ┌──────────────────────────────────┐   │
│  │ API Base:  [_______________]     │   │
│  │ Model:     [_______________]     │   │
│  │ API Key:   [_______________]     │   │
│  └──────────────────────────────────┘   │
│                                         │
│  Direct Model Input                     │
│  ┌──────────────────────────────────┐   │
│  │ Or enter any LiteLLM model name  │   │
│  │ e.g. openai/gpt-4o               │   │
│  └──────────────────────────────────┘   │
│                                         │
│  Connectivity Test                      │
│  ┌──────────────────────────────────┐   │
│  │ [Test API Connectivity]         │   │
│  └──────────────────────────────────┘   │
│                                         │
│  System Status                          │
│  LLM: Connected ✓                       │
│  Parser: Ready                          │
│  PDF: Ready                             │
└────────────────────────────────────────┘
```

## Configuration / 配置项

### LLM Provider Presets / 提供商预设

Select a provider to auto-fill model and API base:

| Provider | Default Endpoint | 默认端点 |
|----------|-----------------|---------|
| OpenAI | `https://api.openai.com/v1` | OpenAI API |
| Anthropic | `https://api.anthropic.com/v1` | Anthropic API |
| Google | `https://generativelanguage.googleapis.com/v1beta` | Gemini API |
| DeepSeek | `https://api.deepseek.com/v1` | DeepSeek API |
| GLM | `https://open.bigmodel.cn/api/paas/v4` | 智谱 API |
| MiniMax | `https://api.minimaxi.com/v1` | MiniMax 中国 API |
| Kimi | `https://api.moonshot.cn/v1` | Moonshot 中国 API |
| Qwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` | DashScope 中国 API |
| Custom | Any OpenAI-compatible endpoint | 任意兼容端点 |

The curated catalog tracks current first-party text models, including GPT-5.6, Claude 5, Gemini 3.7, GLM-5.2, MiniMax M3, Kimi K3, and Qwen 3.8. Custom LiteLLM model names remain supported.

### API Configuration / API 配置

| Field | Description | 说明 |
|-------|-------------|------|
| API Base | Endpoint URL for API calls | API 基础地址 |
| Model | Model name (LiteLLM format) | 模型名称 |
| API Key | Authentication token | API 密钥 |
| Max Tokens | Response token limit | 最大输出 token |
| Temperature | Response randomness (0–2) | 采样温度 |

### Direct Model Input / 直接输入

Type any LiteLLM-compatible model name directly without selecting a preset:
```
openai/gpt-5.6-sol
anthropic/claude-sonnet-5
deepseek/deepseek-v4-flash
```

直接输入任意 LiteLLM 兼容的模型名，无需选择预设。

### Connectivity Test / 连接测试

- Sends a test request to the configured LLM
- Shows success/failure with response time
- Validates API key, endpoint, and model availability

发送测试请求到配置的 LLM。显示成功/失败和响应时间。

## System Status / 系统状态

Real-time indicators for core services:

| Service | Status | Description |
|---------|--------|-------------|
| LLM | Connected ✓ / Failed ✗ | API connectivity test result |
| Parser | Ready | Document import parser (always available) |
| PDF | Ready | PDF export via browser print |

### Reset / 重置

Click **Reset** to restore all settings to defaults.

## Persistence / 持久化

| Data | Storage |
|------|---------|
| LLM config | Browser localStorage; sent with each AI request |
| Server fallback | Backend `.env` / environment variables |

> Browser settings take precedence for AI requests. Backend environment variables are used only when a request does not include an LLM configuration.

浏览器设置会随 AI 请求发送并优先使用；请求未携带 LLM 配置时，后端才使用环境变量作为回退。
