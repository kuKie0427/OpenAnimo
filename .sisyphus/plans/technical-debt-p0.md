# Phase 0 — 基础设施：Ruff 规则 + Redis 提取 + SLF001 + N815

> **耗时**: ~2h | **改动文件**: 9 个 | **WIP=1**

---

## Pre-Gate（不满足则 STOP）

- [x] `feature_list.json` 中 `f-technical-debt` = `not_started` → 改为 `active`
- [x] `./init.sh` 全绿
- [x] 确认 `uv run ruff check app --select BLE001 --statistics` 显示 75 error（基准）

> 如果 Pre-Gate 不满足，**停止**。

---

## 任务 0: 初始化 feature_list + Ruff 规则

**位置**: `backend/pyproject.toml`、`feature_list.json`

**改动内容**:
1. `feature_list.json`: f-technical-debt status → `active`
2. `pyproject.toml`: 添加 `[tool.ruff.lint]` section:
```toml
[tool.ruff.lint]
extend-select = ["SLF001", "N815"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["SLF001"]
```

**必须做**:
- per-file-ignores 验证：`ruff check tests --select SLF001` → 0 errors
- SLF001 规则生效：`ruff check app --select SLF001` → 显示 7 errors（nodes.py）

**必须不做**:
- 不添加 BLE001 到 extend-select（不是 ruff 默认规则，会引入大量噪音）
- 不修改其他 ruff/tool 配置

**QA**: `ruff check tests --select SLF001 --output-format concise` → exit 0 且空输出

---

## 任务 1: 提取 Redis 助手到 app/orchestration/redis.py

**位置**: `app/orchestration/redis.py` (new), `app/agents/orchestrator.py` (mod)

**改动内容**:
从 `orchestrator.py` 移动 10 个函数到新模块：
`get_redis()`, `get_confirm_event_key()`, `get_confirm_channel()`, `get_awaiting_payload_key()`,
`store_awaiting_payload()`, `clear_awaiting_payload()`, `get_awaiting_payload()`,
`clear_confirm_event_redis()`, `trigger_confirm_redis()`, `wait_for_confirm_redis()`
+ 模块级变量 `_redis: redis.Redis | None = None` + `import json as _json`

在 `orchestrator.py` 中：删除被移动代码，添加 `from app.orchestration.redis import get_redis, ...` re-export。

新增测试：`tests/test_orchestration/test_redis.py` — 测试 `get_redis()` singleton、`wait_for_confirm_redis()` timeout。

**必须做**:
- 3 个现有 `# noqa: BLE001` 注释保留（store/clear/get_awaiting_payload 中的）
- re-export 向后兼容：`from app.agents.orchestrator import get_redis` 仍可用
- 新增测试 3+ 条

**必须不做**:
- 不移动 `GRAPH_STAGE_FOR_AGENT`、`STAGE_AGENT_MAP`、`AGENT_COMPLETION_INFO`
- 不修改任何 Redis 函数运行时行为
- 不移动 `_next_phase2_stage()` 等其他模块级函数

**QA**:
```bash
python -c "from app.orchestration.redis import get_redis, wait_for_confirm_redis; print('OK')"
python -c "from app.agents.orchestrator import get_redis; print('REEXPORT_OK')"
uv run pytest tests/test_orchestration/test_redis.py -q
```

---

## 任务 2: 添加 orchestrator 公共方法

**位置**: `app/agents/orchestrator.py`

**改动内容**: 在 `_agent_index()` 后添加两个公共方法：

```python
async def set_run_state(self, run: AgentRun, **fields) -> AgentRun:
    """Public wrapper for _set_run."""
    return await self._set_run(run, **fields)

def get_agent(self, name: str) -> BaseAgent:
    """Return agent instance by name. Raises ValueError if not found."""
    return self.agents[self._agent_index(name)]
```

**必须做**:
- `get_agent()` 返回 `BaseAgent` 对象，非 index
- `set_run_state()` 签名与 `_set_run()` 一致

**必须不做**:
- 不修改 `_set_run()` / `_agent_index()` 实现
- 不删除内部方法（其他内部调用仍依赖）

**QA**:
```bash
python -c "
import asyncio; from unittest.mock import AsyncMock
async def t():
    from app.agents.orchestrator import GenerationOrchestrator
    from app.config import Settings
    o = GenerationOrchestrator(settings=Settings(), ws=AsyncMock(), session=AsyncMock())
    a = o.get_agent('outline')
    print(f'AGENT:{type(a).__name__}')
    try: o.get_agent('nope')
    except ValueError: print('VALUE_ERROR_OK')
asyncio.run(t())"
```

---

## 任务 3: 替换 nodes.py 中 7 处 SLF001

**位置**: `app/orchestration/nodes.py`

**改动内容**: 逐行替换 7 处 `# noqa: SLF001` 调用：

| 行 | 原调用 | 新调用 |
|---|--------|--------|
| 142 | `orchestrator._set_run(...)` | `await orchestrator.set_run_state(...)` |
| 162 | `orchestrator.agents[orchestrator._agent_index(name)]` | `orchestrator.get_agent(name)` |
| 221 | `orchestrator._set_run(...)` | `await orchestrator.set_run_state(...)` |
| 493 | `orchestrator._set_run(...)` | `await orchestrator.set_run_state(...)` |
| 568 | `orchestrator._set_run(...)` | `await orchestrator.set_run_state(...)` |
| 649 | `orchestrator.agents[orchestrator._agent_index("review")]` | `orchestrator.get_agent("review")` |
| 675 | `await orchestrator._cleanup_for_rerun(...)` | 在 orchestrator 中添加 `cleanup_for_rerun()` 委托后调用 |

删除 7 个 `# noqa: SLF001` 注释。

**必须做**:
- 在 orchestrator.py 中为 Task 3 L675 添加 `async def cleanup_for_rerun(self, ...) -> await self._cleanup_for_rerun(...)`
- L675 替换为 `await orchestrator.cleanup_for_rerun(...)`

**必须不做**:
- 不重构 nodes.py 其他代码
- 不修改 graph 拓扑逻辑
- 不拆 nodes.py

**QA**:
```bash
uv run ruff check app --select SLF001 --statistics       # → 0 errors
uv run pytest tests/test_orchestration/ -q --tb=short    # → all pass
```

---

## 任务 4: Import 路径更新 + N815

**位置**: `app/main.py`, `app/api/v1/routes/export.py`, `tests/test_agents/test_orchestrator_helpers.py`, `app/schemas/ws.py`

**改动内容**:
1. **main.py**: `from app.agents.orchestrator import get_awaiting_payload, trigger_confirm_redis` → `from app.orchestration.redis import ...`；`GRAPH_STAGE_FOR_AGENT` 保持从 orchestrator import
2. **export.py**: `from app.agents.orchestrator import get_redis` → `from app.orchestration.redis import get_redis`
3. **test_orchestrator_helpers.py**: Redis 函数 import 路径更新，**零行为变更**
4. **ws.py**: `isLoading: bool | None = None` → `is_loading: bool | None = None`；如前端需要 camelCase，用 `Field(alias="isLoading")` 保持 API 兼容

**必须做**:
- `python -c "from app.main import app"` → 无 ImportError
- `ruff check app tests` → 无 F401/F821
- `ruff check app --select N815 --statistics` → 0

**必须不做**:
- 不修改 `test_orchestrator_helpers.py` 测试逻辑
- 不移动 `GRAPH_STAGE_FOR_AGENT` import

**QA**:
```bash
python -c "from app.main import app; print('OK')"
uv run ruff check app --select N815 --statistics
uv run pytest tests/test_agents/test_orchestrator_helpers.py -q
```

---

## Exit-Gate（全部通过前，不加载 P1）

- [x] `ruff check app --select SLF001 --statistics` → 0
- [x] `ruff check tests --select SLF001 --statistics` → 0（per-file-ignores）
- [x] `ruff check app --select N815 --statistics` → 0
- [x] `ruff check app tests` → 0（无 import/F401/F821）
- [x] `pytest -q` → 1106 passed
- [x] `python -c "from app.main import app"` → OK
- [ ] `feature_list.json` 中本 phase 标记 `f-technical-debt-p0=passing`（可选，如使用子 phase tracking）
- [x] `progress.md` 已更新
- [x] `./init.sh` 全绿

---

## ⛔ Session 边界

**Exit-Gate 全绿后，必须 commit + 结束 Session。** 下一 Session 加载 `technical-debt-p1.md` 执行 BLE001 修复。
