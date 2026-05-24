# resume-builder

## 项目简介
这是一个用于结构化简历编辑与 AI 优化的全栈项目：
- 后端：`FastAPI` + 工具链路（解析 / refine / suggest / apply / 会话）
- 前端：`React + Vite`，包含 `Dashboard / Tailor Chat / Layout Builder / Settings`
- 支持本地确定性版式渲染（A4、单双栏、分组排版参数）

## 主要功能
- 简历导入、解析、保存与最近记录管理
- Tailor 聊天式优化（局部 refine + 可应用候选）
- Layout Builder 可视化调参与实时预览
- 模型设置页（按 Provider 分组预设）

## 快速启动
### 1) 环境准备
- Python 3.11+（建议使用仓库内 `.venv`）
- Node.js 18+

### 2) 安装依赖
```bash
# 后端依赖
pip install -r requirements.txt

# 根目录依赖（并行开发脚本）
npm install

# 前端依赖
npm --prefix frontend install
```

### 3) 配置环境变量
在根目录创建 `.env`（不要提交到 Git）：
```env
OPENAI_API_KEY=your_key
OPENAI_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-5.4
LLM_MAX_TOKENS=2048
LLM_TEMPERATURE=0
```

### 4) 启动
```bash
npm run dev
```
- 前端默认：`http://127.0.0.1:5173`
- 后端默认：`http://127.0.0.1:8000`
- 后端文档：`http://127.0.0.1:8000/docs`

## 常用命令
```bash
npm run dev:backend
npm run dev:frontend
npm run build
```

## 项目结构
```text
src/                    # FastAPI 后端
  api/                  # API 路由（v1/v2/tool/session）
  services/             # 业务与 LLM 调用逻辑
frontend/               # React 前端
  src/pages/            # 页面（dashboard/tailor/builder/settings）
  src/components/       # 组件与工作台
tests/                  # 测试
docs/                   # 设计与流程文档
```

## 安全与开源注意
- `.env`、`session sqlite`、`node_modules`、`dist` 不应提交
- 发布公开仓库前请轮换所有历史密钥

