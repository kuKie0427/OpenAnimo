# OpenAnimo

<p align="center">
  <strong>故事想法 → 多智能体协作 → 漫剧成片</strong>
</p>

<p align="center">
  一个以 LangGraph 为核心的 AI 漫剧生成学习项目。
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=111827" alt="React 18" />
  <img src="https://img.shields.io/badge/LangGraph-Orchestration-6D28D9?style=flat-square" alt="LangGraph" />
</p>

OpenAnimo 将故事创意串联成**规划、角色/分镜生成、视频生成与合成**的完整链路，并用无限画布展示过程与结果。

> [!WARNING]
> 这是一个 **LangGraph 学习/演示项目**，重点验证多阶段编排、恢复执行、实时进度与前后端协作。
> **不适合直接用于工业生产环境**。

## 功能特色

- 多阶段 AI 生成链路（规划 → 角色 → 分镜 → 视频）
- WebSocket 实时进度推送
- 可恢复/可取消/可反馈的 run 流程
- tldraw 无限画布审阅角色、分镜与结果
- 前端在线配置管理面板
- 多 Provider 文本/图像/视频生成支持

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18 + TypeScript + Vite 6 + tldraw 4 + TailwindCSS 3 + daisyUI 4 |
| 后端 | Python 3.10+ / FastAPI + SQLModel + LangGraph |
| 数据库 | PostgreSQL 16 + Redis 7 |
| 容器 | Docker Compose |

## 快速开始

```bash
cp backend/.env.example backend/.env
docker-compose up -d
```

- 前端: http://localhost:15173
- API 文档: http://localhost:18765/docs

### 本地开发

```bash
# 后端
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 18765

# 前端
cd frontend
pnpm install
pnpm dev
```

## 常用命令

```bash
# 后端
cd backend
uv run pytest              # 运行测试
uv run ruff check app tests # 代码检查

# 前端
cd frontend
pnpm test                  # 运行测试
pnpm build                 # 类型检查 + 构建
```

## 项目结构

```
OpenAnimo/
├── backend/                # Python FastAPI 后端
│   ├── app/
│   │   ├── agents/         # AI Agent 实现
│   │   ├── orchestration/  # LangGraph 编排图
│   │   ├── services/       # 业务服务 (36 个模块)
│   │   ├── models/         # SQLModel 数据模型
│   │   └── ws/             # WebSocket 管理
│   └── tests/              # pytest 测试
├── frontend/               # React TypeScript 前端
│   └── app/
│       ├── components/     # UI 组件
│       ├── stores/         # Zustand 状态管理
│       ├── hooks/          # 自定义 Hook
│       └── pages/          # 页面
└── docker-compose.yml      # 生产编排
```

## License

MIT
