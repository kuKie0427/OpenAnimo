# Phase 1 — Runtime Harness 基础（P1）

> **耗时**: ~5h | **改动文件**: 6 个（3 新建 + 3 修改） | **WIP=1**

---

## 前置检查（不满足则 STOP）

- [ ] `feature_list.json` 存在，且 `f-harness-p0` = `passing`
- [ ] `feature_list.json` 中 `f-harness-p1` 不存在或状态为 `not_started` / `active`
- [ ] `./init.sh` 全绿
- [ ] 已阅读 `openOii/AGENTS.md`

> 依赖文件: `backend/app/agents/base.py`, `backend/app/agents/prompts/plan.py`, `backend/app/agents/prompts/outline.py`, `backend/app/agents/prompts/critic.py`

---

## 执行内容

### 任务 1: 初始化 feature_list 中的 Phase 1 条目

在 `feature_list.json` 中添加：
```json
{
  "id": "f-harness-p1",
  "name": "Harness Phase 1 — Prompt 版本管理 + AgentTrace",
  "dependencies": ["f-harness-p0"],
  "status": "active",
  "verification": "cd backend && uv run pytest tests/ -q && uv run ruff check app tests",
  "notes": "所有 Prompt 模块含 VERSION+CHANGELOG；AgentTrace 表可用；API 可查询 Trace"
}
```

---

### 任务 2: Prompt 版本管理

**改动文件**:
- `backend/app/agents/prompts/plan.py` — 顶部追加 `VERSION` + `CHANGELOG`
- `backend/app/agents/prompts/outline.py` — 同上
- `backend/app/agents/prompts/critic.py` — 同上
- `backend/app/agents/prompts/CHANGELOG.md` (新建) — 汇总所有 prompt 变更

**模板**（以 `plan.py` 为例）:
```python
# 文件顶部，SYSTEM_PROMPT 之前
VERSION = "3.0.0"
CHANGELOG = """
v3.0.0 (2026-06): 增加 character_hints 强制匹配逻辑；visual_bible 改为 section 注入
v2.0.0 (2026-05): 增加 incremental mode + preserve_ids
v1.0.0 (2026-04): 初始版本
"""
```

**CHANGELOG.md 格式**:
```markdown
# Prompt 变更历史

## plan.py — v3.0.0 (2026-06)
- 增加 character_hints 强制匹配逻辑
- visual_bible 从 inline 改为独立 section 注入

## plan.py — v2.0.0 (2026-05)
...
```

**必须做**:
- 每个 prompt 文件的 VERSION 和 CHANGELOG 放在文件顶部
- CHANGELOG.md 汇总所有模块的变更
- 不修改 SYSTEM_PROMPT 内容本身

**必须不做**:
- 不要改 prompt 的业务逻辑
- 不要引入新依赖
- 不要修改 config.py 的 Provider 配置

---

### 任务 3: Agent 执行追踪（AgentTrace）

**新建文件**:
- `backend/app/models/agent_trace.py`
- `backend/alembic/versions/0020_create_agent_trace.py`

**修改文件**:
- `backend/app/agents/base.py` — 添加 trace context manager

**数据模型**:
```python
# backend/app/models/agent_trace.py
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class AgentTrace(SQLModel, table=True):
    __tablename__ = "agent_trace"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="agentrun.id", index=True)
    agent_name: str
    stage: str
    method: str
    start_time: datetime
    end_time: Optional[datetime] = None
    llm_calls: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    images_generated: int = 0
    status: str = "running"
    error: Optional[str] = None
```

**BaseAgent trace context manager**（追加到 `base.py`）:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def trace_step(self, ctx: AgentContext, stage: str, method: str):
    """Trace a sub-step execution. Non-blocking on failure."""
    trace = AgentTrace(
        run_id=ctx.run.id, agent_name=self.name,
        stage=stage, method=method, start_time=utcnow(),
    )
    ctx.session.add(trace)
    await ctx.session.commit()
    try:
        yield trace
        trace.status = "completed"
    except Exception as e:
        trace.status = "failed"
        trace.error = str(e)[:500]
        raise
    finally:
        trace.end_time = utcnow()
        try:
            await ctx.session.commit()
        except Exception:
            pass  # trace persistence failure must not break agent flow
```

**Alembic migration**:
```bash
cd backend && uv run alembic revision --autogenerate -m "create agent_trace table"
# 检查生成的 migration 文件；在测试 SQLite 上需要 batch_alter_table
```

**在 Agent 中使用 trace**（示例 — OutlineAgent）:
```python
async def run_outline(self, ctx: AgentContext) -> None:
    async with self.trace_step(ctx, "plan_outline", "run_outline"):
        # ... 原有逻辑不变
```

**必须做**:
- 每个 Agent 的 production sub-step 方法用 `trace_step` 包裹
- trace 写入失败不阻塞 Agent（两处 try/except）
- migration 用 `batch_alter_table` 保证 SQLite 兼容

**必须不做**:
- 不要改 Approval / Critic / Review 节点的 trace（它们属于 Phase 2）
- 不要改 Agent 的业务逻辑

---

## Gate（全部通过前，不加载 Phase 2）

- [x] 所有 prompt 文件含 VERSION + CHANGELOG，且 `CHANGELOG.md` 汇总完整
- [ ] `AgentTrace` 表可用（`uv run alembic upgrade head` 成功）— 需要 DATABASE_URL 配置
- [ ] Agent sub-step 执行后 AgentTrace 表有对应记录 — 需要运行时验证
- [x] `feature_list.json` 中 `f-harness-p1` = `passing`
- [x] `./init.sh` 全绿（backend lint + type + test 全部通过）
- [x] `progress.md` 已记录本次 session

---

## ⛔ Session 边界

**Gate 全部通过后，执行 `/handoff` 然后等待用户开启新会话。** 禁止继续加载 `harness-retrofit-p2.md`。

1. 确认 Gate 全绿 → `git commit` → **执行 `/handoff`**
2. 告知用户："Phase 1 完成。请开启新会话，加载 handoff 文件继续 Phase 2"
3. 新会话 → 读 handoff → 读 roadmap → 读 `feature_list.json` → 确认 `f-harness-p1 = passing` → 加载 `harness-retrofit-p2.md`
