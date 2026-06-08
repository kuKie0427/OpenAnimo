## Harness 约定

### 开始工作前
```bash
./init.sh                    # 环境检查 + 全量验证
cat feature_list.json | python -m json.tool  # 当前功能状态
cat progress.md              # 上次会话做了什么
```

### 工作中
- **WIP=1**: 同时只做一个 feature（`feature_list.json` 中 `active` 不超过 1 个）
- **pass-gate**: 只有 verification 命令全部通过，才能标记 `passing`
- **feature_list.json**: 开始做 → `active`，做完且验证通过 → `passing`

### 结束工作前
1. 更新 `progress.md`（做了什么 / 决策 / 阻断 / 下次）
2. 更新 `feature_list.json` 最终状态
3. 运行 `./init.sh` — 必须全绿
4. Git commit

# OpenAnimo — 项目知识库（根）

**生成时间:** 2026-06-05
**语言:** 中文

---

## 概览

OpenAnimo 是"故事想法 → 漫剧成片"的 **AI 多 Agent 长链路生成平台**。双包 Monorepo（后端 Python/FastAPI + 前端 React/Vite），无根级统一脚本。

- **后端**: FastAPI + LangGraph + SQLModel + Anthropic SDK — Agent 编排、LLM 调用、图像/视频/音频生成
- **前端**: React 18 + TypeScript + Vite 6 + tldraw 4 + TailwindCSS 3 + daisyUI 4 — 画布交互、实时 WebSocket、项目面板
- **基础设施**: Docker Compose（PostgreSQL 16 + Redis 7）、GitHub Container Registry

详细指南 → `backend/AGENTS.md`（后端） / `frontend/AGENTS.md`（前端）

---

## 目录结构

```
OpenAnimo/
├── backend/                    # Python FastAPI 后端（uv 管理）
│   ├── app/
│   │   ├── main.py             # ⭐ FastAPI 入口（应用工厂）
│   │   ├── config.py           # 配置加载（.env）
│   │   ├── api/v1/router.py    # API 路由聚合（/api/v1）
│   │   ├── agents/             # LangGraph Agent（编排器 + 子 Agent）
│   │   ├── orchestration/      # 编排图/节点/状态/持久化
│   │   ├── services/           # 36 个业务服务
│   │   ├── models/             # SQLModel 数据模型
│   │   ├── schemas/            # Pydantic 请求/响应
│   │   ├── db/                 # 数据库会话初始化
│   │   └── ws/                 # WebSocket 管理
│   ├── tests/                  # pytest（test_api/services/agents/orchestration）
│   ├── alembic/                # 数据库迁移版本
│   └── pyproject.toml
├── frontend/                   # React TypeScript 前端（pnpm 管理）
│   ├── app/
│   │   ├── main.tsx            # ⭐ React 入口（MSW + createRoot）
│   │   ├── App.tsx             # ⭐ 路由定义（react-router-dom 7）
│   │   ├── pages/              # 页面组件
│   │   ├── components/         # UI 组件（canvas/chat/layout/panels/settings/ui）
│   │   ├── stores/             # Zustand 状态
│   │   ├── hooks/              # 自定义 Hook
│   │   ├── services/api.ts     # API 请求封装
│   │   ├── types/              # TypeScript 类型
│   │   ├── mocks/              # MSW Mock
│   │   └── styles/             # 全局 CSS（tokens + globals + fonts）
│   ├── tests/e2e/              # Playwright E2E
│   └── package.json
├── docker-compose.yml          # 生产编排（预构建镜像）
├── docker-compose.dev.yml      # 开发编排（本地构建）
└── AGENTS.md                   # ← 本文件
```

---

## 快速查找

| 任务 | 位置 | 备注 |
|------|------|------|
| 启动全部服务 | `docker-compose up -d` | 需先 `cp backend/.env.example backend/.env` |
| 单独起后端 | `cd backend && uv run uvicorn app.main:app --reload --port 18765` | 端口 18765 |
| 单独起前端 | `cd frontend && pnpm dev` | 端口 15173 |
| 后端 API 文档 | `http://localhost:18765/docs` | Swagger UI |
| 了解生成链路 | `backend/app/orchestration/` | LangGraph 编排图 |
| 了解 API 路由 | `backend/app/api/v1/router.py` | 13 个子路由 |
| 了解前端路由 | `frontend/app/App.tsx` | 7 条 react-router 路由 |
| 了解 WebSocket | `backend/app/ws/manager.py` + `frontend/app/hooks/useWebSocket.ts` | `/ws/projects/{id}` |
| 了解配置机制 | `backend/app/config.py` + `frontend/app/utils/runtimeBase.ts` | 后端 .env，前端自动推导 |
| 了解设计规范 | `DESIGN.md` | Projection Room 放映室主题，15 条 Do/Don't |
| 查看产品定义 | `PRODUCT.md` | 产品功能与用户流程 |

---

## 代码符号速查

| 符号 | 类型 | 位置 | 职责 |
|------|------|------|------|
| `create_app()` | 函数 | `backend/app/main.py` | FastAPI 应用工厂 |
| `Orchestrator` | 类 | `backend/app/agents/orchestrator.py` | 生成链路总调度器（最大源文件，1127 行） |
| `get_settings()` | 函数 | `backend/app/config.py` | 配置单例（@lru_cache） |
| `api_router` | APIRouter | `backend/app/api/v1/router.py` | API 路由聚合 |
| `App` | 组件 | `frontend/app/App.tsx` | 前端路由根 |
| `useEditorStore` | Zustand | `frontend/app/stores/editorStore.ts` | 编辑器状态 |
| `useWebSocket` | Hook | `frontend/app/hooks/useWebSocket.ts` | WebSocket 事件路由（698 行） |
| `InfiniteCanvas` | 组件 | `frontend/app/components/canvas/InfiniteCanvas.tsx` | tldraw 画布 |

---

## 跨项目约定

### 提交格式
```
type(scope): description

类型: feat / fix / docs / refactor / test / chore
范围: 模块名（api, ui, canvas, agent, orchestrator）
```

### 验证习惯
- **前端改动**: 先跑相关 `vitest`，再跑 `pnpm build`（含 tsc 类型检查）
- **后端改动**: 先跑相关 `pytest`，再按需跑 `uv run ruff check app tests`
- **依赖变更**: 同步更新 `backend/uv.lock` 和 `frontend/pnpm-lock.yaml`
- **Docker 镜像**: CI 仅构建推送，不跑测试 — 本地自己跑

### 端口约定
| 服务 | 端口 |
|------|------|
| 前端 | 15173 |
| 后端 | 18765 |
| PostgreSQL | 5432（本地覆盖 5433） |
| Redis | 6379 |

---

## 关键易错点（跨端）

1. **无根级统一脚本** — 必须分别进入 `backend/` 和 `frontend/` 操作
2. **后端强制单 Worker** — `task_manager` 是进程内字典，`WEB_CONCURRENCY=1`
3. **前端 `frontend/.env.local` 通常不需要写** — `runtimeBase.ts` 会自动推导后端地址
4. **Docker 场景** — 图像/视频服务跑在宿主机时，`.env` 不能用 `localhost`，改 `host.docker.internal`
5. **配置路径不一致** — 后端 `get_settings()` 读 `.env`，测试 `Settings()` 不读 `.env`
6. **静态媒体输出** — `backend/app/static` 被 Compose 挂载，改导出逻辑不要忽略
7. **Alembic 默认 SQLite** — 跑迁移前先确认 `DATABASE_URL` 指向正确的数据库

---

## 详细指南

根级跨端专题文档存放在 `.trellis/spec/guides/`:

| 主题 | 文档 |
|------|------|
| 跨层开发思维 | [cross-layer-thinking-guide](.trellis/spec/guides/cross-layer-thinking-guide.md) |
| 代码复用模式 | [code-reuse-thinking-guide](.trellis/spec/guides/code-reuse-thinking-guide.md) |
| 编排架构设计 | [orchestration-architecture](.trellis/spec/guides/orchestration-architecture.md) |

后端专题文档（数据库/日志/错误处理/WS 契约等 8 篇）→ 详见 `backend/AGENTS.md`
前端专题文档（组件/状态管理/类型安全/样式规范等 7 篇）→ 详见 `frontend/AGENTS.md`



## 专题文档索引

跨端专题文档存放在 `.trellis/spec/` 目录下，按需加载（Tier 3 context）：

| 层级 | 目录 | 覆盖 |
|------|------|------|
| 跨层开发指南 | [guides/](.trellis/spec/guides/index.md) | 代码复用思维、跨层协作模式、编排架构设计 |
| 后端专题规范 | [backend/](.trellis/spec/backend/index.md) | 数据库、错误处理、日志、编排阶段、WS 事件（8 篇） |
| 前端专题规范 | [frontend/](.trellis/spec/frontend/index.md) | 组件模式、状态管理、Hook 设计、类型安全（7 篇） |

---

## 参考
- `backend/AGENTS.md` — 后端 Python/FastAPI 开发指南
- `frontend/AGENTS.md` — 前端 React/Vite 开发指南
