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
| Anthropic | `https://api.anthropic.com` | Anthropic API |
| Google | `https://generativelanguage.googleapis.com/v1beta` | Gemini API |
| DeepSeek | `https://api.deepseek.com/v1` | DeepSeek API |
| GLM | `https://open.bigmodel.cn/api/paas/v4` | 智谱 API |
| MiniMax | `https://api.minimax.chat/v1` | MiniMax API |
| Custom | Any OpenAI-compatible endpoint | 任意兼容端点 |

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
openai/gpt-4o
anthropic/claude-sonnet-4
deepseek/deepseek-chat
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
| LLM config | Backend `.env` / environment variables |
| Provider selection | localStorage (frontend-only) |

> Backend settings (API key, model, base URL) are read from environment variables on startup. The frontend settings page writes to localStorage for display convenience — actual API calls use backend config.

后端设置从环境变量读取。前端设置页写入 localStorage 仅用于展示便利 — 实际 API 调用使用后端配置。
