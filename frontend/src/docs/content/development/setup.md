---
title: 本地开发环境
description: 在 Windows、macOS 或 Ubuntu 上启动前端、FastAPI 后端和可选的 JD 检索。
category: start
order: 2
---

# 本地开发环境

## 前置条件

| 工具 | 版本 | 用途 |
| --- | --- | --- |
| Python | 3.11+ | FastAPI 后端与测试 |
| Node.js | 18+（推荐 LTS） | React 前端与构建 |
| Git | 最新稳定版 | 版本管理 |

## 安装

```bash
git clone <repo-url>
cd resume-studio

python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
npm --prefix frontend install
```

## 配置模型

在仓库根目录创建 `.env`。不要把它提交到 Git：

```env
API_BASE=https://api.openai.com/v1
API_KEY=your-api-key
LLM_MODEL=gpt-4o
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.7
DEBUG=true
RAG_ENABLED=false
PERSONAL_DATA_STORAGE=memory
```

项目通过 LiteLLM 支持 OpenAI-compatible endpoint。`API_BASE` 和 `API_KEY` 是后端默认配置；页面发送的 `llm_config` 可以按请求覆盖模型、地址和参数。

## 启动

终端 A 启动后端：

```bash
.venv/Scripts/python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

macOS/Linux 使用：

```bash
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

终端 B 启动前端：

```bash
npm --prefix frontend run dev
```

默认前端地址是 `http://127.0.0.1:5173`，API 代理到 `http://127.0.0.1:8000`。

## 验证

```bash
# 后端健康检查
curl http://127.0.0.1:8000/health

# 前端类型检查与生产构建
npm --prefix frontend run build
```

打开前端后，进入 Settings → Test API Connectivity 验证模型连接。JD 检索依赖 `tests/fixtures/jds/`，不需要职位匹配时可以跳过种子数据。

## 常见问题

- `8000` 被占用：把 Uvicorn 改到其他端口，并同步修改 `frontend/vite.config.ts` 的 proxy。
- `faiss` 或 embedding 依赖缺失：先执行 `pip install -r requirements.txt`，首次启动会下载本地模型缓存。
- 改完 API 后前端仍显示旧内容：确认开发服务器代理指向同一个端口，必要时重启 Vite。
