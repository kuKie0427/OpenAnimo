# Phase 3 — E2E 测试：前后端真实集成

> **耗时**: ~1 day | **改动文件**: 6 个（3 新建 + 3 修改） | **WIP=1**

---

## Pre-Gate（不满足则 STOP）

- [x] `grep -q 'stub_services' backend/app/config.py && echo "OK" || echo "MISSING"` — Settings 类需包含 `stub_services: bool` 字段（后端 stub 服务切换开关）
- [x] `feature_list.json` 中 `f-e2e-real-integration` = `not_started` → 改为 `active`
- [x] `./init.sh` 全绿（ruff ✓, pytest 1177✓(1 flaky skip unrelated), tsc ✓, vitest 368✓, build ✓）
- [x] `cd frontend && pnpm e2e:install` — Playwright 浏览器已安装
- [x] `cd frontend && pnpm e2e` — 现有 mock-based E2E 全部通过
- [x] 确认 `frontend/playwright.config.ts` 可读，`frontend/tests/e2e/` 目录存在

> 如果 Pre-Gate 不满足，**停止**。

---

## 背景

**现状**: 所有 Playwright E2E 测试通过 `installMockWebSocket(page)` 和 `page.route("**/api/v1/**", ...)` 完全模拟后端行为。前端代码从未在测试中连接过真实的后端进程。风险：

1. API 路径/方法拼写错误无法被 E2E 捕获（mock 路由可能与真实后端路由不同步）
2. WebSocket 事件格式/字段变化无法检测（MockWebSocket 手动 dispatch 的 payload 可能过期）
3. 前后端序列化契约不一致（后端返回的字段名/类型变化，mock 看不出来）
4. 恢复流程（409 → resume）只在 mock 层测试，真实后端 LangGraph checkpoint 恢复未验证

**目标**: 在保留现有 mock-based E2E 测试（快速 CI 路径）的同时，新增一组**真实集成 E2E 测试**，前端连接真实后端进程（FastAPI + SQLite + stub 服务），覆盖核心业务链路。

**架构变更**:

```
Before:  [Playwright] → [Vite Dev Server] → MockWebSocket + page.route() mocks
After:   [Playwright] → [Vite Dev Server] → [Real Backend (uvicorn, random port)]
                                              ├── SQLite (temp file)
                                              ├── StubLLM / StubImage / StubVideo
                                              └── Real WebSocket (/ws/projects/{id})
```

**双重测试策略**:
- 保留 `workflow-stage-sync.spec.ts` 的 4 个 mock 测试（最快，CI 上用）
- 新建 `workflow-real-api.spec.ts` 的 4 个集成测试（慢但真实，开发机上用）
- 新建 `workflow-real-ws.spec.ts` — WebSocket 行为验证
- 新建 `workflow-real-recovery.spec.ts` — 恢复链路验证
- 通过 Playwright `test.describe.configure({ mode: 'serial' })` 隔离集成测试

**后端 stub 策略**（不使用真实 API Key）:
- LLM: stub 返回固定 JSON（plan 输出含 characters/shots 结构）
- Image: stub 返回 `http://image.test/{n}` URL
- Video: stub 返回 `http://video.test/{n}` URL
- 使用 `monkeypatch` 或环境变量切换 stub 实现（复用 `backend/tests/agent_fixtures.py` 模式）

---

## 任务 0: 初始化 feature_list + 创建后端服务器生命周期 Fixture

**位置**: `feature_list.json` (mod), `frontend/tests/e2e/conftest.ts` (new), `frontend/tests/e2e/global-setup.ts` (new), `frontend/tests/e2e/global-teardown.ts` (new), `frontend/playwright.config.ts` (mod)

**改动内容**:

1. `feature_list.json`: 添加新条目
2. 创建 `frontend/tests/e2e/conftest.ts` — Playwright 测试上下文 fixture 文件：
   - 导出 `BACKEND_PORT` 作为模块变量（globalSetup 写入，fixture/测试读取）
       - 可选：提供 `seedProject(page)` helper，通过真实 API 创建项目并返回 projectId

> **注意**: Playwright 不会 auto-discover `conftest.ts`（这是 pytest 约定）。spec 文件中需通过 `import { BACKEND_PORT, seedProject } from './conftest'` 显式导入。

3. 创建 `frontend/tests/e2e/global-setup.ts` — Playwright globalSetup：
   - 获取随机空闲端口（使用 `net.createServer` → listen → close 获取）
   - 通过 `child_process.spawn` 启动 `uv run uvicorn app.main:app`：
     - `--port {random_port}`
     - 传 `DATABASE_URL=sqlite+aiosqlite:///{tmpdir}/test.db`
     - 传 `OPENOII_STUB_SERVICES=true`（后端通过此环境变量切换到 stub 实现）
   - 等待 `http://localhost:{port}/health` 返回 200（最多 30s）
   - 运行 `alembic upgrade head` 创建表
   - 通过 API 创建种子项目（POST /api/v1/projects）用于测试
   - 将 `backendPort` 和 `seedProjectId` 写入共享状态文件（如 `.e2e-state.json` 或通过 `process.env`）
4. 创建 `frontend/tests/e2e/global-teardown.ts` — Playwright globalTeardown：
   - 向 uvicorn 进程发送 SIGTERM
   - 等待进程退出（最多 10s，超时则 SIGKILL）
   - 清理临时 SQLite 文件
5. 修改 `frontend/playwright.config.ts`：
   - 添加 `globalSetup: './tests/e2e/global-setup.ts'`
   - 添加 `globalTeardown: './tests/e2e/global-teardown.ts'`
    - 在 `webServer` 的 `env` 中注入 `VITE_API_URL` 和 `VITE_WS_URL`（指向 globalSetup 启动的后端端口）

> **实现细节**: `webServer.env` 是静态配置，无法引用 globalSetup 动态发现的端口。解决方案：不在 `webServer.env` 中配置端口，而是在 `globalSetup` 中直接设置 `process.env.VITE_API_URL` 和 `process.env.VITE_WS_URL`。Playwright 的 webServer 作为 globalSetup 所在的 Node 进程的子进程启动，会自动继承父进程的环境变量。

**必须做**:
- 不修改 `workflow-stage-sync.spec.ts`（现有 mock 测试保持不变）
- 后端端口必须随机分配（避免端口冲突，支持并行运行）
- globalSetup 超时设为 60s
- 种子项目数据（story、style、target_shot_count）需与前端页面预期匹配
- 使用 `cross-env` 或 Playwright 的 `webServer.env` 传递环境变量给 Vite

**必须不做**:
- 不创建新的 playwright.config 文件（在现有 config 上增量修改）
- 不假设端口 18765 可用（必须随机分配）
- 不修改 `frontend/app/utils/runtimeBase.ts`（前端地址推导逻辑不变，靠 `VITE_API_URL` 环境变量覆盖）
- 不在 globalSetup 中硬编码 API Key

**QA**:
```bash
cd frontend && npx playwright test --project=chromium --grep "real" --reporter=list
# 预期: globalSetup 启动后端成功，测试连接成功
```

---

## 任务 1: 真实 API 集成测试 — 页面加载真实后端数据

**位置**: `frontend/tests/e2e/workflow-real-api.spec.ts` (new)

**改动内容**:

创建新的 spec 文件，替换 `page.route()` mock 为真实后端 API 调用。测试结构：

```
test.describe("Real API Integration", () => {
  test.describe.configure({ mode: 'serial' });

  test("homepage loads project list from real backend")
  test("project page loads project detail from real backend")
  test("project page loads characters from real backend")
  test("project page loads shots from real backend")
});
```

每个测试：
1. 使用 `page.goto("/")` 或 `page.goto("/project/{seedProjectId}")`
2. 不调用 `mockProjectPageApis()`（移除 mock）
3. 验证页面渲染了真实后端返回的数据

**简化替代方案**: 如果后端 stub 服务实现复杂度过高（影响 Pre-Gate），可以先不做 Task 1 的全量测试，而是：
1. 在 `workflow-real-api.spec.ts` 中添加一个 smoke test（仅验证 fetch 不 404）
2. 或者复用 `page.route()` 但改为"**穿透**"模式（未 mock 的请求透传给真实后端）

**与 Task 0 的依赖**: 需要 globalSetup 已启动后端 + 种子项目已创建

**必须做**:
- 使用 `test.describe.configure({ mode: 'serial' })`（避免并行时数据竞争）
- 所有 API 调用走真实后端（不安装 `mockProjectPageApis`）
- 验证关键 UI 元素存在（项目标题、角色列表、分镜列表等）

**必须不做**:
- 不修改 `workflow-stage-sync.spec.ts`
- 不测试生成流程（生成走 Task 3）
- 不安装 MockWebSocket（Task 2 处理 WebSocket）

**QA**:
```bash
cd frontend && npx playwright test tests/e2e/workflow-real-api.spec.ts --reporter=list
```

---

## 任务 2: 真实 WebSocket 集成测试 — WS 事件从后端广播

**位置**: `frontend/tests/e2e/workflow-real-ws.spec.ts` (new), `frontend/tests/e2e/conftest.ts` (mod)

**改动内容**:

1. 在 `conftest.ts` 中添加 WS helper（可选）：
   ```typescript
   // 辅助函数：通过 HTTP 触发后端 WS 事件广播
   async function triggerWsEvent(page: Page, eventType: string, payload: object) {
     // 调用后端内部 API 触发事件（或直接调用 ws manager）
   }
   ```

2. 创建 `workflow-real-ws.spec.ts`：
   - 测试前端 `useWebSocket` hook 连接真实 WS 端点 `/ws/projects/{projectId}`
   - 验证 WS 连接建立（检查页面是否发起 WS 连接）
   - 验证 WS 事件到达前端后，UI 正确更新（ChatPanel 显示消息、阶段指示器更新）
   - 通过后端 API 触发生成（POST `/api/v1/projects/{id}/generate`），然后监听前端 WS 事件处理

**注意**: 真实后端在 stub 模式下，生成流程会立即完成（stub LLM 返回固定数据）。这意味着：
- 前端的 WS 事件监听器会收到完整的 `run_progress` / `run_awaiting_confirm` 序列
- 可以在合理时间内验证 UI 状态转换

**与 Task 1 的依赖**: 需要真实 API 可用（创建项目、获取数据）

**必须做**:
- 不安装 `installMockWebSocket(page)` — 使用浏览器原生 WebSocket
- 验证至少 3 种 WS 事件类型到达前端（run_progress, run_awaiting_confirm, run_completed）
- 使用 `page.waitForResponse()` 或 `page.waitForSelector()` 等待 UI 更新

**必须不做**:
- 不手动 `page.evaluate(() => window.__mockWs.dispatch(...))`（无 mock）
- 不拦截 WebSocket 构造函数
- 不修改 `frontend/app/hooks/useWebSocket.ts`

**QA**:
```bash
cd frontend && npx playwright test tests/e2e/workflow-real-ws.spec.ts --reporter=list --timeout=60000
```

---

## 任务 3: 完整用户流程 — 生成 + 确认 + 完成

**位置**: `frontend/tests/e2e/workflow-real-api.spec.ts` (mod, 追加测试)

**改动内容**:

在 `workflow-real-api.spec.ts` 中追加测试：

```
test("full generation flow: start → plan → confirm → render → confirm → compose → complete")
```

测试步骤：
1. 导航到项目页面（使用种子项目 ID）
2. 打开 ChatPanel
3. 点击"开始生成漫剧"按钮 → 触发 POST `/api/v1/projects/{id}/generate`
4. 等待 `run_progress` WS 事件 → 验证 UI 显示"规划阶段"
5. 等待 `run_awaiting_confirm` WS 事件 → 验证"通过"按钮可见
6. 点击"通过"按钮 → 触发确认 API
7. 等待 `run_confirmed` + 下一阶段 `run_progress` → 验证"渲染阶段"
8. 重复确认流程直到 `run_completed`
9. 验证前端最终状态与后端状态一致（通过 GET API 交叉验证）

**关键差异 vs mock 测试**: 
- Mock 测试手动 dispatch WS 事件（可控制时序）
- 集成测试等待真实 WS 事件到达（需合理 timeout，建议 30s/stage）
- 后端 stub 服务在 1-3s 内完成每阶段

**与 Task 2 的依赖**: 需要 Task 2 的模式（真实 WS）

**必须做**:
- 使用 `page.waitForSelector()` 等待 UI 元素，不使用 `page.evaluate()` dispatch mock 事件
- 每阶段添加合理的 timeout（stub 后端很快，但留 buffer）
- 验证最终状态：通过 GET `/api/v1/projects/{id}` 确认 status/characters/shots/video_url 与前端一致

**必须不做**:
- 不手动 dispatch mock WS 事件
- 不 mock 任何 API 路由
- 不修改前端生成流程代码

**QA**:
```bash
cd frontend && npx playwright test tests/e2e/workflow-real-api.spec.ts -g "full generation" --reporter=list --timeout=120000
```

---

## 任务 4: 恢复流程 — 409 recoverable → resume

**位置**: `frontend/tests/e2e/workflow-real-recovery.spec.ts` (new)

**改动内容**:

创建新 spec 文件，测试真实后端 LangGraph checkpoint 恢复：

```
test.describe("Recovery Flow", () => {
  test.describe.configure({ mode: 'serial' });

  test("409 recoverable triggers resume UI")
  test("resume continues from checkpoint")
});
```

测试步骤：
1. 创建新项目（通过 API）并触发第一次生成
2. 在 `plan_approval` 阶段中断后端（不确认就第二次调用 generate → 返回 409 recoverable）
3. 验证前端显示"恢复"按钮和恢复卡片
4. 点击"恢复" → 验证 resume 请求发出且流程继续
5. 确认流程最终完成

**关键**: 这是 mock-based 测试无法覆盖的场景（mock 不会维护 LangGraph checkpoint state）

**与 Task 3 的依赖**: 需要 Task 3 的生成流程模式

**必须做**:
- 使用 serial mode（恢复状态依赖前序操作）
- 验证 409 响应 body 包含 `state: "recoverable"`, `recovery_summary` 等字段
- 验证 resume 后 WS 事件从正确的 stage 开始（不是从头）
- timeout 设置为 90s（恢复流程可能更慢）

**必须不做**:
- 不手动触发 409（mock 模式的做法）— 让后端自然返回 409
- 不修改 `useWebSocket.ts` 的恢复逻辑

**QA**:
```bash
cd frontend && npx playwright test tests/e2e/workflow-real-recovery.spec.ts --reporter=list --timeout=90000
```

---

## 任务 5: 反馈流程 — 发送反馈 → 后端处理

**位置**: `frontend/tests/e2e/workflow-real-api.spec.ts` (mod, 追加测试)

**改动内容**:

在现有 spec 中追加测试：

```
test("feedback sends to backend and is processed")
```

测试步骤：
1. 确保项目已完成一次生成（run_completed）
2. 在 ChatPanel 输入框中输入反馈文本："请修改剧本，增加更多悬念"
3. 点击发送
4. 验证前端请求正确到达后端：
   - POST `/api/v1/projects/{id}/feedback` 请求包含正确的 `feedback_type` 和 `message`
   - 后端返回 `{ ok: true }`
5. 验证前端 UI 更新（反馈消息出现在聊天记录中）

**与 Task 3 的依赖**: 需要完整生成流程完成

**必须做**:
- 不 mock `page.route("**/api/v1/projects/*/feedback")` 
- 验证 HTTP 请求成功发送（使用 `page.waitForResponse()` 或检查网络请求）
- 验证反馈文本在 ChatPanel 中可见

**必须不做**:
- 不测试反馈后的重新生成流程（那是另一轮 generate，已有 Task 3 覆盖）

**QA**:
```bash
cd frontend && npx playwright test tests/e2e/workflow-real-api.spec.ts -g "feedback" --reporter=list --timeout=60000
```

---

## Exit-Gate（全部通过前，不结束）

- [x] `cd frontend && pnpm e2e` — 现有 mock-based E2E 全绿（无回归）
- [x] `cd frontend && npx playwright test tests/e2e/workflow-real-*.spec.ts --reporter=list` — 所有新集成测试通过
- [x] `cd frontend && npx playwright test --reporter=list` — 全部 E2E（mock + 集成）通过
- [x] `cd backend && uv run ruff check app tests` → 0
- [x] `cd backend && uv run pytest -q` — 后端测试全绿（1177✓, 1 flaky skip unrelated）
- [x] `feature_list.json` 中 `f-e2e-real-integration` status = `passing`，evidence 更新
- [x] `progress.md` 已更新
- [x] `./init.sh` 全绿（ruff ✓, pytest ✓, tsc ✓, vitest 368✓, build ✓）

---

## Guardrails（检查清单）

**向后兼容**:
- [x] `workflow-stage-sync.spec.ts` 的 4 个 mock 测试不变、不过、不被 skip
- [x] `pnpm e2e`（默认命令）仍然只跑 mock 测试 — 所有集成测试通过 `test.describe("Real...")` 名称区分

**后端 stub 隔离**:
- [x] 后端 stub 服务不向外部发送任何 HTTP 请求（LLM/Image/Video API key 不参与 — 所有 provider 设为 fake）
- [x] 后端 stub 使用独立 SQLite 文件（global-setup 创建临时目录，不影响开发/生产数据库）
- [x] 后端 stub 进程在测试完成后一定被杀死（globalTeardown SIGTERM→10s→SIGKILL）

**端口管理**:
- [x] 后端使用随机端口（`net.createServer` + listen + close 获取）
- [x] 前端 Vite 使用固定端口 15173（未修改）
- [x] globalSetup 写入的端口号在 globalTeardown 前被清理（`.e2e-state.json` deleted）

**代码质量**:
- [x] 新增文件全部 TypeScript（`conftest.ts`, `global-setup.ts`, `global-teardown.ts`, 3 个 spec 文件）
- [x] 不引入新 npm 依赖（仅使用 Node.js 内置 `child_process`, `net`, `fs`, `path`, `os`）
- [x] 不修改前端源代码（`app/` 目录零改动 — 已验证 editorStore.ts 回滚）

---

## 注意事项

> ⚠️ **前置依赖（本 Phase 执行前必须完成）**: 后端需先支持 `OPENOII_STUB_SERVICES=true` 环境变量切换 stub 服务。所需改动：`backend/app/config.py` 添加 `stub_services: bool = False` 字段，`backend/app/main.py` lifespan 中根据该字段注入 FakeLLM/FakeImageService/FakeVideoService。此项为独立 Phase，本 plan 不包含。

2. **stub 实现位置**: 建议新增 `backend/app/services/stubs.py`，包含 `StubLLM`、`StubImage`、`StubVideo` 三个类，复用 `backend/tests/agent_fixtures.py` 中的已有 Stub 类模式（`StubLLM`、`StubImage`、`StubVideo`）。

3. **CI 策略**: 集成测试较慢（stub 后端每次启动 + 种子数据），不建议纳入 CI 必须通过项。建议：
   - CI 只跑 `pnpm e2e`（mock tests）
   - 集成测试通过 `pnpm e2e:integration` 脚本按需运行
   - 在 `package.json` 添加 `"e2e:integration": "playwright test tests/e2e/workflow-real-*.spec.ts"`

4. **并行执行**: `test.describe.configure({ mode: 'serial' })` 确保每个 spec 内测试串行，不同 spec 文件之间可以并行（Playwright worker 分配）。

---

## ⛔ Session 边界

**Exit-Gate 全绿后，必须 commit + 更新 progress.md + 更新 feature_list.json。** 然后停止。
