# backend — Python/FastAPI 后端开发指南

**父级**: `../AGENTS.md`

---

## 概览

Python FastAPI 后端，负责 AI Agent 编排、LLM 调用、图像/视频/音频生成、WebSocket 实时推送。使用 `uv` 作为包管理器。

---

## 目录结构

```
backend/
├── app/
│   ├── main.py                 # FastAPI 应用工厂（create_app + lifespan）
│   ├── config.py               # pydantic-settings 配置加载（.env）
│   ├── api/v1/
│   │   ├── router.py           # API 路由聚合（13 个子路由，前缀 /api/v1）
│   │   └── routes/             # 按资源分文件（generation/projects/config/...）
│   ├── orchestration/          # LangGraph 编排核心
│   │   ├── graph.py            # 状态图定义
│   │   ├── nodes.py            # 41 个节点函数（909 行，需关注）
│   │   ├── state.py            # 图状态
│   │   ├── runtime.py          # 运行时上下文
│   │   └── persistence.py      # 持久化/恢复
│   ├── agents/                 # AI Agent 实现
│   │   ├── orchestrator.py     # 总调度器（1035 行）
│   │   ├── outline.py          # 大纲 Agent
│   │   ├── plan.py             # 规划 Agent
│   │   ├── render.py           # 渲染 Agent
│   │   ├── compose.py          # 合成 Agent
│   │   ├── critic.py           # VLM 审查 Agent
│   │   ├── review_rules.py     # 反馈路由引擎
│   │   ├── base.py             # Agent 基类 + AgentContext
│   │   └── prompts/            # Prompt 模板（Python 文件）
│   ├── services/               # 36 个业务服务模块
│   │   ├── text.py             # 文本生成（多 Provider/Stream）
│   │   ├── llm.py              # LLM 调用封装
│   │   ├── image_service.py    # 图像生成
│   │   ├── video_service.py    # 视频生成
│   │   ├── audio_service.py    # 音频/TTS
│   │   ├── export_service.py   # PDF/Webtoon 导出（578 行）
│   │   ├── font_utils.py       # 字体工具
│   │   └── task_manager.py     # 进程内任务管理（单 Worker 前提）
│   ├── models/                 # SQLModel 数据模型
│   ├── schemas/                # Pydantic 请求/响应模型
│   ├── db/session.py           # 数据库会话 + init_db()
│   ├── ws/manager.py           # WebSocket 管理器
│   └── static/                 # 媒体文件输出（Compose 挂载）
├── tests/
│   ├── conftest.py             # 全局 fixtures（核心！）
│   ├── factories.py            # 测试工厂函数
│   ├── agent_fixtures.py       # Agent 专用 Fake 类
│   ├── test_api/               # API 路由测试
│   ├── test_services/          # 服务层测试
│   ├── test_agents/            # Agent 测试
│   ├── test_orchestration/     # 编排测试
│   └── integration/            # 集成测试
├── alembic/versions/           # 数据库迁移版本
├── pyproject.toml              # 项目配置（依赖/lint/测试）
└── uv.lock                     # 依赖锁定
```

---

## 快速查找

| 任务 | 位置 | 备注 |
|------|------|------|
| 了解 API 路由结构 | `app/api/v1/router.py` | 路由聚合，每个路由模块独立文件 |
| 了解生成流程 | `app/orchestration/graph.py` → `nodes.py` | LangGraph 编排图 |
| 了解 Agent 调度 | `app/agents/orchestrator.py` | 总调度器，协调 Plan/Render/Compose |
| 了解 WebSocket 事件 | `app/ws/manager.py` | 事件广播 + 连接管理 |
| 了解数据库操作 | `app/models/` + `app/services/` | SQLModel + 业务逻辑 |
| 了解配置 | `app/config.py` | `get_settings()` + `.env` |
| 了解测试 fixture | `tests/conftest.py` | 核心：test_session、app、async_client |
| 了解测试工厂 | `tests/factories.py` | `create_project()`、`create_run()` 等 |
| 了解 Fake 类 | `tests/agent_fixtures.py` | FakeLLM、FakeImageService、FakeVideoService |

---

## 开发命令

```bash
# 安装依赖
cd backend && uv sync

# 启动开发服务器
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 18765

# 运行测试
uv run pytest                              # 全量
uv run pytest tests/test_api/test_generation.py -q  # 单文件
uv run pytest -k "test_resume"             # 按名称过滤

# Lint
uv run ruff check app tests

# 数据库迁移（手动，非自动）
uv run alembic upgrade head
```

---

## 后端约定

详细开发规范见 `.trellis/spec/backend/` 专题文档:

| 主题 | 文档 |
|------|------|
| 代码质量规范（命名/行宽/异步/模块结构） | [quality-guidelines](.trellis/spec/backend/quality-guidelines.md) |
| 错误处理与异常 | [error-handling](.trellis/spec/backend/error-handling.md) |
| 日志规范 | [logging-guidelines](.trellis/spec/backend/logging-guidelines.md) |
| 数据库操作（ORM/迁移/SQLite shim） | [database-guidelines](.trellis/spec/backend/database-guidelines.md) |
| 编排阶段与状态机 | [orchestration-stages](.trellis/spec/backend/orchestration-stages.md) |
| WebSocket 事件契约 | [ws-event-contracts](.trellis/spec/backend/ws-event-contracts.md) |
| 目录结构与模块职责 | [directory-structure](.trellis/spec/backend/directory-structure.md) |

核心原则速记：snake_case 命名 · line-length=100 · 全异步 · Pydantic 校验 · SQLModel ORM · 路由委托 services/

## 后端反模式（禁止）

详见 [quality-guidelines](.trellis/spec/backend/quality-guidelines.md) 的反模式章节。

速记：禁止裸 except · 禁止忽略副作用 · 禁止假设多实例 · 禁止 bypass 私有方法 · 禁止路由写业务逻辑

---

## 已知问题

- `orchestration/nodes.py` 909 行，41 个函数 — 可不拆分但需留意
- `agents/orchestrator.py` 1035 行 — 职责偏重，恢复/WS 推送/CC 处理可进一步拆分
- `coverage.xml` 和 `.run/backend.pid` 应加入 `.gitignore`
