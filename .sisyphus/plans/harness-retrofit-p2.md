# Phase 2 — Runtime Harness 进阶（P2）

> **耗时**: ~8h | **改动文件**: 5 个（3 新建 + 2 修改） | **WIP=1**

---

## 前置检查（不满足则 STOP）

- [ ] `feature_list.json` 中 `f-harness-p1` = `passing`
- [ ] `f-harness-p2` 不存在或状态为 `not_started` / `active`
- [ ] `./init.sh` 全绿
- [ ] `AgentTrace` 表可用

---

## 执行内容

### 任务 0: 初始化 feature_list

在 `feature_list.json` 中添加：
```json
{
  "id": "f-harness-p2",
  "name": "Harness Phase 2 — 产出物验证 + 降级测试 + WS Schema",
  "dependencies": ["f-harness-p1"],
  "status": "active",
  "verification": "cd backend && uv run pytest tests/ -q && uv run ruff check app tests"
}
```

---

### 任务 1: 产出物自动验证（PlanOutputValidator）

**新建**: `backend/app/agents/validation.py`

**核心逻辑**:
```python
class PlanOutputValidator:
    """验证 Agent 产出物是否符合约束。返回问题列表，空列表 = 通过。"""

    def validate_characters(self, data: dict, hints: list[str]) -> list[str]:
        issues = []
        # 1. character_hints 全部匹配
        if hints:
            generated_names = {c.get("name", "") for c in data.get("characters", [])}
            for hint in hints:
                if not any(hint in name for name in generated_names):
                    issues.append(f"character_hint '{hint}' not matched")
        # 2. 必填字段
        for char in data.get("characters", []):
            for field in ["name", "description"]:
                if not char.get(field):
                    issues.append(f"character missing required field: {field}")
        return issues

    def validate_shots(self, data: dict, target_count: int | None) -> list[str]:
        issues = []
        if target_count is not None:
            actual = len(data.get("shots", []))
            if actual != target_count:
                issues.append(f"shot count mismatch: expected {target_count}, got {actual}")
        return issues
```

**集成点**: 在 `orchestration/nodes.py` 中对应 production node 完成后调用 validator。失败 → 重试（最多 2 次）→ 仍失败 → WS 推送 `needs_review`。

**配置**（追加到 `config.py`）:
```python
validation_enabled: bool = True
validation_max_retries: int = 2
```

**必须做**:
- PlanAgent 的 characters 和 shots 产出都校验
- 重试逻辑在 node 层，不改 Agent 本身
- `validation_enabled=False` 可完全关闭

**必须不做**:
- 不要改 PlanAgent 的 prompt 或 LLM 调用逻辑
- 不要改 graph.py 的节点拓扑

---

### 任务 2: 降级策略可测试化

**修改**: `backend/app/agents/base.py` — 在 `AgentContext` 中添加:
```python
fault_injector: dict | None = None  # 仅测试环境使用
```

**修改**: `backend/app/agents/critic.py` — 在 `_run_review()` 开头:
```python
if ctx.fault_injector and ctx.fault_injector.get("fail_vlm"):
    raise RuntimeError("Fault injected: VLM unavailable")
if ctx.fault_injector and ctx.fault_injector.get("fail_text"):
    raise RuntimeError("Fault injected: text-only fallback unavailable")
```

**新建**: `backend/tests/test_services/test_degradation.py`

测试用例:
1. `test_critic_vlm_fallback_to_text` — VLM 不可用时降级为 text-only
2. `test_critic_full_fallback_to_score_5` — VLM + text 都失败时 score=5.0
3. `test_tts_failure_non_blocking` — TTS 失败不阻塞流程
4. `test_bgm_failure_non_blocking` — BGM 失败不阻塞流程

**必须做**:
- fault_injector 仅测试环境生效，生产代码不检查
- 每个降级路径有独立测试

**必须不做**:
- 不要在生产代码中暴露 fault_injector 的任何行为
- 不要改 CriticAgent 以外的 Agent

---

### 任务 3: WS Event Schema 强化

> **现状**: 项目已有 `backend/app/schemas/ws.py`（含 `WsEvent` Union type + 事件 data model），`ws/manager.py` 已调用 `WsEvent.model_validate()`。此任务是**补齐遗漏 + 加回归测试**。

**扩展**: `backend/app/schemas/ws.py`
- 审计 `ws/manager.py` 和 `orchestrator.py` 中所有 `send_event()` 调用
- 补齐缺失的事件类型（如 `consistency_eval_completed`、`data_cleared`）

**新建**: `backend/tests/test_schemas/test_ws.py`
```python
def test_all_known_event_types_have_schema():
    """确认所有发出的事件类型在 ws.py 中有对应 Pydantic model"""
    ...

def test_event_validation_rejects_invalid_payload():
    """Schema 校验拒绝对非法 payload"""
    ...
```

**必须做**:
- 所有事件类型在 ws.py 中有对应 schema
- 测试覆盖所有已知事件类型

**必须不做**:
- 不要创建新的 schema 文件（扩展已有 ws.py）
- 不要改 `send_event()` 的行为（已有 `model_validate`）

---

## Gate（全部通过前，不加载 Phase 3）

- [x] `PlanOutputValidator` 存在，可被 node 调用
- [x] 降级路径测试全部通过（`test_degradation.py` — 4/4 passed）
- [x] WS schema 测试全部通过（`test_ws.py` — 4/4 passed）
- [x] `feature_list.json` 中 `f-harness-p2` = `passing`
- [x] `./init.sh` 全绿
- [x] `progress.md` 已更新

---

## ⛔ Session 边界

**Gate 全部通过后，执行 `/handoff` 然后等待用户开启新会话。** 禁止继续加载 `harness-retrofit-p3.md`。

1. 确认 Gate 全绿 → `git commit` → **执行 `/handoff`**
2. 告知用户："Phase 2 完成。请开启新会话，加载 handoff 文件继续 Phase 3"
3. 新会话 → 读 handoff → 读 roadmap → 读 `feature_list.json` → 确认 `f-harness-p2 = passing` → 加载 `harness-retrofit-p3.md`
