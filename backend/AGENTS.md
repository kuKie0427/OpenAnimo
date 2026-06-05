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
│   │   ├── nodes.py            # 41 个节点函数（756 行，需关注）
│   │   ├── state.py            # 图状态
│   │   ├── runtime.py          # 运行时上下文
│   │   └── persistence.py      # 持久化/恢复
│   ├── agents/                 # AI Agent 实现
│   │   ├── orchestrator.py     # 总调度器（1127 行，最大文件）
│   │   ├── plan.py             # 规划 Agent（754 行）
│   │   ├── compose.py          # 合成 Agent
│   │   ├── render.py           # 渲染 Agent
│   │   ├── review.py           # 审查 Agent
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

### 代码规范
- **文件命名**: snake_case（`agent_run.py`、`style_template.py`）
- **类命名**: PascalCase（`Settings`、`AgentRun`、`AppException`）
- **变量/函数**: snake_case
- **行宽**: Ruff `line-length=100`
- **异步**: 几乎全异步（`async def`），异常处理统一用 `AppException`
- **包管理**: `uv`（非 pip/poetry），锁文件 `uv.lock`

### API 模式
- 路由文件在 `app/api/v1/routes/`，按资源命名
- 请求/响应用 Pydantic `schemas/` 严格校验
- 路由中不写业务逻辑，委托给 `services/`
- 全局异常处理器在 `app/main.py` 的 lifespan 中注册

### 服务层模式
- 业务逻辑在 `services/`，每个模块处理一类资源/能力
- 服务模块通过参数注入依赖（DB session、LLM client、Redis），避免隐式全局状态
- Provider 切换通过 `services/provider_resolution.py` 决议

### 测试模式
- **asyncio_mode = auto**，但测试仍显式标注 `@pytest.mark.asyncio`（双重保险）
- **每个 test function 独立 SQLite 文件** — 使用 `tmp_path / "test.db"` 而非 `:memory:`
- **Fake 类优先** — 不用 unittest.mock.patch，使用 `FakeSession`、`FakeRedis`、`FakeLLM` 等
- **双层验证** — API 测试既验证 HTTP 响应，又通过注入 session 查数据库
- **依赖覆盖** — FastAPI `app.dependency_overrides` 替换 DB session、配置、WS manager

### 数据库
- **ORM**: SQLModel（SQLAlchemy + Pydantic 融合）
- **生产/开发**: PostgreSQL + asyncpg
- **测试**: 内存 SQLite（aiosqlite shim，在 `backend/aiosqlite/` 目录）
- **迁移**: Alembic，手动执行（不自动在启动时运行）
- **启动初始化**: `init_db()` 会 `create_all()` + 初始化配置 + 重置遗留 run 状态

---

## 后端反模式（禁止）

1. **不要**用裸 `except Exception:` 吞异常 — 区分具体异常类型（现有 32 处需逐步修复）
2. **不要**忽略 `init_db()` 的副作用 — 启动时 `create_all()`、重置 run 状态、checkpointer setup 同步发生
3. **不要**假设多实例安全 — `task_manager` 是进程内字典，当前设计只支持单 Worker
4. **不要**直接访问私有成员 — `nodes.py` 中 7 处 `# noqa: SLF001` 绕过 `orchestrator._set_run` 等私有方法，应添加公开方法
5. **不要**在路由中写编排/持久化逻辑 — 应委托给 `orchestration/` 和 `services/`
6. **不要**在 Docker 容器内用 `localhost` 访问宿主机服务 — 改为 `host.docker.internal`
7. **不要**忘记更新 `uv.lock` — 改依赖后必须同步更新锁文件

---

## 已知问题

- `orchestration/nodes.py` 756 行，41 个函数 — 可不拆分但需留意
- `agents/orchestrator.py` 1127 行 — 职责过重，恢复/WS 推送/CC 处理可拆出
- 32 处 `except Exception:` 需逐步迁移为具体异常
- `coverage.xml` 和 `.run/backend.pid` 应加入 `.gitignore`
