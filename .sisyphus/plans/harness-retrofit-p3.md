# Phase 3 — 观测性仪表板 + 多 Agent 并行（P3）

> **耗时**: ~8h+ | **改动文件**: 8 个（5 新建 + 3 修改） | **WIP=1** | **远期按需**

---

## 前置检查（不满足则 STOP）

- [ ] `feature_list.json` 中 `f-harness-p2` = `passing`
- [ ] `feature_list.json` 中 `f-harness-p3` 不存在或状态为 `not_started` / `active`
- [ ] `./init.sh` 全绿
- [ ] `AgentTrace` 表可用（Phase 1 产物，包含 run_id / agent_name / stage / llm_calls / tokens 等字段）

> 如果前置不满足，**停止**。P3 依赖 P2 全部完成。

---

## 执行内容

### 任务 0: 初始化 feature_list

在 `feature_list.json` 的 `features` 数组中添加：

```json
{
  "id": "f-harness-p3",
  "name": "Harness Phase 3 — 观测性仪表板 + 多 Agent 并行",
  "description": "RunMetrics API / 并行分支 / 新路由注册",
  "dependencies": ["f-harness-p2"],
  "status": "active",
  "verification": "cd backend && uv run pytest tests/ -q && uv run ruff check app tests"
}
```

---

### 任务 1: RunMetrics 仪表板 API

**位置**:
- 新建 `backend/app/services/metrics_service.py` — 聚合查询逻辑
- 新建 `backend/app/api/v1/routes/metrics.py` — HTTP 端点
- 修改 `backend/app/api/v1/router.py` — 注册新路由
- 新建 `backend/tests/test_api/test_metrics.py` — API 测试

**端点**:

1. `GET /api/v1/metrics/runs?project_id={id}&limit=20`
   — 返回最近 N 次 run 的汇总：每 run 的 agent 调用次数、LLM token 总量、生成图片数、耗时、成功率

2. `GET /api/v1/metrics/costs?project_id={id}`
   — 聚合统计：token_input/output 总和、images_generated 总数，按 agent_name 分组

3. `GET /api/v1/metrics/quality?project_id={id}`
   — 按 stage 分组，统计每个 stage 的 status 分布（success/failed/running）

**数据源**: `agent_trace` 表（Phase 1 产物），字段参考 `backend/app/models/agent_trace.py`

**必须做**:
- metrics_service 接收 SQLAlchemy session 参数，无隐式全局状态
- 路由层只做参数解析 + 调用 service + 返回，不写查询逻辑
- 在 `router.py` 中注册（include_router 模式，与现有 13 个子路由一致）
- SQL 查询使用 SQLModel/SQLAlchemy ORM，不写裸 SQL
- `project_id` 参数可选，不传则全量统计

**必须不做**:
- 不要在 metrics_service 里发 HTTP 请求或操作 WebSocket
- 不要改 `agent_trace` 表结构或迁移文件
- 不要创建新的数据库表

---

### 任务 2: 多 Agent 并行 — LangGraph 并行分支

**位置**:
- 修改 `backend/app/orchestration/graph.py` — 使用 `Send()` 添加并行分支
- 修改 `backend/app/orchestration/nodes.py` — 添加并行路由函数
- 新建 `backend/tests/test_orchestration/test_parallel.py` — 并行分支图拓扑测试

**改动内容**:

当前 `graph.py` 所有节点串行（`add_edge` / `add_conditional_edges` 的单目标）。在 `character_images_approval` 通过后，`render_shots` 和 `compose_videos` 当前是串行，但实际上如果 shots 的视觉渲染不依赖已完成 character 渲染的结果（shots 可用 character 的 description 而非渲染图），则可并行。

并行方案：

```python
# graph.py — 修改 shots_approval → 之后的路由
from langgraph.graph import Send

# 在 route_after_shots_approval 返回 list[Send] 实现扇出
graph.add_conditional_edges(
    "shots_approval",
    nodes.route_shots_approval_parallel,  # 新路由函数
    {
        "render_characters": "render_characters",
        "render_shots": "render_shots_parallel",  # 新节点
        "review": "review",
    },
)
```

`render_shots_parallel` 节点逻辑与 `render_shots` 相同，但作为独立节点以支持并行执行。完成后通过 `route_after_parallel_render` 汇聚到 `compose_videos`。

**必须做**:
- 仅用 LangGraph 原生 `Send()` / `Command` API，不引入外挂 MessageBus
- 并行节点之间无共享可变状态（每个节点独立写入 Phase2State 的不同字段）
- 并行分支的完成状态在汇聚点检查（两个都完成才继续）
- 降级开关：config.py 加 `parallel_enabled: bool = True`，关闭则回退到串行路径

**必须不做**:
- 不要改 Agent 内部的 prompt 或 LLM 调用逻辑
- 不要引入 `asyncio.gather()` / `concurrent.futures` 等 Python 原生并发
- 不要改动 Phase2State 的字段定义（并行节点写不同字段，不冲突）

---

## Gate（全部通过前，不允许结束会话）

- [x] `metrics_service.py` 存在，3 个查询方法可被 API 端点调用
- [x] `/api/v1/metrics/*` 三个端点均返回 200（`test_metrics.py` 全部通过 — 9/9）
- [x] `graph.py` 中 `shots_approval` 后的路由含并行分支
- [x] `test_parallel.py` 验证：并行两个节点都可达 + 汇聚点正确等待两者完成（27/27）
- [x] `parallel_enabled=False` 时图拓扑与当前串行版本一致（回归测试通过 — 127/127）
- [x] `feature_list.json` 中 `f-harness-p3` = `passing`
- [x] `./init.sh` 全绿（运行中验证）
- [x] `progress.md` 已记录本次 session

---

## ⛔ Session 边界 — 严禁跨 Phase

**Gate 全部通过后，执行 `/handoff` 然后等待用户开启新会话。**

原因：P3 执行期间的上下文（API 测试输出、graph 调试日志、迁移验证）会填满注意力窗口。后续加载其他 phase 文件会导致注意力稀释。

正确流程：
1. 确认 Gate 全绿 → `git commit` → **执行 `/handoff`**
2. `/handoff` 生成的摘要包含：当前进度、P3 完成确认、关键决策（并行分支选择）
3. 告知用户："Phase 3 已完成。所有 harness phase 均已交付。如有下一项工作，请开启新会话加载 handoff 文件继续。"
4. 新会话 → 读 handoff → 读 roadmap → 读 `feature_list.json` → 确认 `f-harness-p3 = passing`
