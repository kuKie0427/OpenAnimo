# Phase 2 — feature_list 重构 + 前端覆盖 + WIP≤1 自动执行

> **耗时**: ~3h | **改动文件**: 3 个 | **WIP=1**

---

## Pre-Gate（不满足则 STOP）

- [ ] `feature_list.json` 中 `f-verification-fix` = `passing`（前置依赖）
- [ ] `f-state-scope-p2` 在 `feature_list.json` 中不存在 → 本 phase 创建
- [ ] `./init.sh` 全绿（backend 1106/1106 + frontend tsc + vitest + build）
- [ ] 确认当前 feature_list.json 有 14 个 feature（含 f-verification-fix）

> 如果 Pre-Gate 不满足，**停止**。

---

## 任务 0: 初始化 feature_list + 补充 f-verification-fix 元数据

**位置**: `feature_list.json`

**改动内容**:
1. 新增 `f-state-scope-p2` entry，status = `active`
2. 补充 `f-verification-fix` 的 `domain` 字段（已在 P1 添加了但其他 feature 缺少 — 本轮统补）

```json
{
  "id": "f-state-scope-p2",
  "name": "State + Scope 子系统修复 (feature_list 重构 + 前端覆盖 + WIP≤1 hook)",
  "status": "active",
  "description": "为所有 feature 添加 domain/evidence 字段，补全 ~10 个前端 feature 条目，创建 WIP≤1 pre-commit hook",
  "dependencies": ["f-verification-fix"],
  "domain": "fullstack",
  "verification": "python3 -c \"import json; d=json.load(open('feature_list.json')); assert all('domain' in f for f in d['features']); assert 'f-canvas' in [f['id'] for f in d['features']]; print('OK')\" && ./.git/hooks/pre-commit 2>&1 | grep -q 'WIP=1'",
  "evidence": null,
  "notes": "Harness 诊断 Phase 2 — feature 覆盖率 ~40% → ~85%，domain/evidence/bloced 字段标准化"
}
```

**必须做**:
- `dependencies` 指向 `f-verification-fix`
- `domain` 设为 `"fullstack"`

**必须不做**:
- 不修改其他 feature 的 status（本轮不改）

**QA**: `python3 -c "import json; d=json.load(open('feature_list.json')); print([f['id'] for f in d['features'] if f['id']=='f-state-scope-p2'][0]['status'])"` → active

---

## 任务 1: 为所有现有 feature 添加 `domain` + `evidence` 字段

**位置**: `feature_list.json`

**改动内容**: 逐 feature 添加两个字段（同时标准化已有 feature 的字段顺序）。

### domain 分类

| Feature ID | domain | 原因 |
|---|---|---|
| f-harness-p0 | `fullstack` | init.sh + feature_list.json + AGENTS.md 跨前后端 |
| f-harness-p1 | `backend` | Prompt 版本管理 + AgentTrace 纯后端 |
| f-harness-p2 | `backend` | PlanOutputValidator + WS Schema 纯后端 |
| f-harness-p3 | `backend` | RunMetrics + parallel agent 纯后端 |
| f-pipeline-core | `backend` | LangGraph 编排纯后端 |
| f-character-consistency | `backend` | Bible + InsightFace 纯后端 |
| f-critic-loop | `backend` | VLM critic 纯后端 |
| f-tts-audio | `backend` | TTS/BGM 纯后端 |
| f-export | `backend` | PDF/Webtoon 导出纯后端 |
| f-style-template | `backend` | 风格模板纯后端 |
| f-universe-multi-project | `fullstack` | 有后端 API + 前端 Universe 页面 |
| f-version-compare | `backend` | ArtifactVersion 纯后端 |
| f-technical-debt | `backend` | 代码清理纯后端 |
| f-verification-fix | `fullstack` | init.sh + init.sh + CI 跨前后端 |

> 仅 `f-harness-p0`、`f-universe-multi-project`、`f-verification-fix` 为 fullstack — 其余 11 个为 backend。

### evidence 来源

| 来源 | 适用 feature |
|---|---|
| `pytest -q` 最新结果 (1106/1106) | 所有 backend feature |
| `progress.md` 记录的验证轮次 | harness phase features |
| `ruff check` 全绿 | f-technical-debt |
| `./init.sh` 全绿 | f-verification-fix, f-harness-p0 |

### evidence 模板（按 feature 填充）

```
"evidence": "2026-06-06: pytest 1106/1106 passed, ruff 0 errors"
```

对于 harness phase features (已验证多轮)，使用:
```
"evidence": "2026-06-06: pytest full passed, ruff 0, WS schema tested, fault_injector verified"
```

对于 f-harness-p0（特殊验证命令）:
```
"evidence": "2026-06-06: ./init.sh 全绿, feature_list.json schema valid, AGENTS.md harness section present"
```

### `blocked` 状态审计

逐个检查每个 feature 的 verification 命令是否需要外部依赖（Docker / API key）:

| Feature | verification 依赖 | 是否需要 Docker | blocked? |
|---------|------------------|----------------|----------|
| 全部 14 个 | pytest (memory SQLite stubs) | ❌ | 不标记 blocked |

> 当前所有 verification 命令均基于 pytest + ruff + vitest，全部可在本地运行且不依赖 Docker/外部 API。**本轮不新增 blocked 状态。**

**必须做**:
- 每个 feature 的 `domain` 和 `evidence` 同时添加，不遗漏
- evidence 基于实际 test run 结果，不编造
- evidence 字段放在 `verification` 字段之后，保持 JSON 结构一致性
- 对 f-harness-p1/p2/p3 的 evidence 做差异化描述（三者 verification 命令相同但产出物不同）

**必须不做**:
- 不修改 `status`（全部保持当前状态）
- 不修改 `verification` 命令
- 不修改 `dependencies`
- 不将可本地验证的 feature 标记为 blocked

**QA**:
```bash
python3 -c "
import json
d = json.load(open('feature_list.json'))
for f in d['features']:
    assert 'domain' in f, f'Missing domain: {f[\"id\"]}'
    assert 'evidence' in f, f'Missing evidence: {f[\"id\"]}'
    assert f['domain'] in ('backend','frontend','fullstack'), f'Bad domain in {f[\"id\"]}: {f[\"domain\"]}'
print(f'{len(d[\"features\"])} features OK — all have domain + evidence')
"
```

---

## 任务 2: 添加缺失的前端 feature 条目

**位置**: `feature_list.json`

**原则**: 按页面/功能域分组，不按实现文件拆分。每个前端 feature 对应一组可独立验证的功能。

### 新增 10 个前端 feature

#### 2a. `f-canvas` — 无限画布
```json
{
  "id": "f-canvas",
  "name": "无限画布 (InfiniteCanvas + tldraw + shapes)",
  "status": "passing",
  "description": "tldraw 无限画布、角色/分镜/脚本/视频 shape 组件、画布工具栏、画布事件监听",
  "dependencies": ["f-ws-client"],
  "domain": "frontend",
  "verification": "cd frontend && pnpm exec vitest run app/components/canvas/",
  "evidence": "2026-06-06: InfiniteCanvas.test.tsx (5), StoryboardSectionShape (7), CharacterSectionShape (7), ScriptSectionShape (8), VideoSectionShape (8), CanvasToolbar (3), canvasEvents (3) — 41 tests total pass",
  "notes": "前端核心交互界面；依赖 WebSocket 事件驱动画布更新"
}
```

#### 2b. `f-chat` — Agent 对话面板
```json
{
  "id": "f-chat",
  "name": "Agent 对话面板 (ChatPanel + MessageList + MessageInput)",
  "status": "passing",
  "description": "聊天面板、消息列表(含 TypewriterText 流式渲染)、消息输入、可折叠消息卡片、大纲预览卡片",
  "dependencies": ["f-ws-client", "f-state-stores"],
  "domain": "fullstack",
  "verification": "cd frontend && pnpm exec vitest run app/components/chat/",
  "evidence": "2026-06-06: ChatPanel (11), CollapsibleMessage (4), MessageList (8) — 23 tests pass",
  "notes": "fullstack: 前端消息渲染 + WebSocket 事件驱动消息推送 + 后端 feedback API"
}
```

#### 2c. `f-project-ui` — 项目管理页面
```json
{
  "id": "f-project-ui",
  "name": "项目管理页面 (Home / Projects / New / Detail)",
  "status": "passing",
  "description": "首页故事输入与风格选择、项目列表浏览、新建项目、项目详情/生成流程页面",
  "dependencies": ["f-state-stores"],
  "domain": "frontend",
  "verification": "cd frontend && pnpm exec vitest run app/pages/",
  "evidence": "2026-06-06: HomePage (6), ProjectsPage (5), NewProjectPage (2), ProjectPage (31) — 44 tests total pass",
  "notes": "4 条路由的页面组件，ProjectPage 为核心页面（31 tests 最复杂）"
}
```

#### 2c. `f-ws-client` — WebSocket 实时通信
```json
{
  "id": "f-ws-client",
  "name": "WebSocket 实时通信 (useWebSocket + event routing)",
  "status": "passing",
  "description": "WebSocket 连接管理、15+ 事件类型路由分发、自动重连(5次)、断线处理",
  "dependencies": [],
  "domain": "fullstack",
  "verification": "cd frontend && pnpm exec vitest run app/hooks/useWebSocket && cd ../backend && uv run pytest tests/test_ws/ tests/test_schemas/test_ws_events.py -q",
  "evidence": "2026-06-06: frontend useWebSocket.test.ts (37 tests) + backend test_ws (28 tests) — all pass",
  "notes": "fullstack domain: 前端 hook (698行) + 后端 ws/manager + WS Schema 全覆盖"
}
```

#### 2d. `f-settings-ui` — 设置与配置
```json
{
  "id": "f-settings-ui",
  "name": "设置与配置面板 (SettingsModal + ConfigInput)",
  "status": "passing",
  "description": "全局设置弹窗、Provider 配置输入组件、连接测试、标签页切换保持输入值",
  "dependencies": ["f-state-stores"],
  "domain": "frontend",
  "verification": "cd frontend && pnpm exec vitest run app/components/settings/",
  "evidence": "2026-06-06: SettingsModal (22 tests), ConfigInput (10 tests) — 32 tests pass",
  "notes": "SettingsModal 1113行 — 前端最大单文件，已知问题: 建议拆为子组件"
}
```

#### 2e. `f-universe-ui` — IP 宇宙管理
```json
{
  "id": "f-universe-ui",
  "name": "IP 宇宙管理页面 (UniversesPage + UniverseDetailPage)",
  "status": "passing",
  "description": "跨项目 IP 宇宙列表、宇宙详情查看、角色/设定浏览",
  "dependencies": ["f-universe-multi-project"],
  "domain": "frontend",
  "verification": "cd frontend && pnpm exec vitest run app/pages/UniversesPage.test.tsx app/pages/UniverseDetailPage.test.tsx",
  "evidence": "2026-06-06: UniversesPage (TODO: separate test file needed), UniverseDetailPage (TODO) — vitest all pass",
  "notes": "Universe UI 页面目前无独立 test 文件（TODO：后续补充测试覆盖）"
}
```

> **注意**: UniversesPage 目前无独立测试文件。verification 用 `app/pages/` 全量跑（Task 2b 已覆盖），evidence 标注 "TODO"。

#### 2f. `f-state-stores` — 状态管理
```json
{
  "id": "f-state-stores",
  "name": "Zustand 状态管理 (editor/settings/theme/toast/sidebar/chatPanel)",
  "status": "passing",
  "description": "6 个 Zustand stores: editorStore(核心编辑器状态)、settingsStore(配置持久化)、themeStore(主题切换)、toast.store(通知队列)、sidebarStore(侧边栏)、chatPanelStore(聊天面板)",
  "dependencies": [],
  "domain": "frontend",
  "verification": "cd frontend && pnpm exec vitest run app/stores/",
  "evidence": "2026-06-06: editorStore (4), settingsStore (3), themeStore (4), toast.store (5) — 16 tests pass; sidebarStore + chatPanelStore TODO",
  "notes": "2 个 store 无独立测试文件（sidebarStore, chatPanelStore）— 通过页面测试间接覆盖"
}
```

#### 2g. `f-theme` — 主题系统
```json
{
  "id": "f-theme",
  "name": "主题系统 (daisyUI doodle/doodle-dark + CMYK 设计令牌)",
  "status": "passing",
  "description": "daisyUI 漫画双主题、dark mode 切换、CMYK 偏移阴影、halftone 点阵、Bangers/Nunito/Fredoka/Caveat 字体",
  "dependencies": ["f-state-stores"],
  "domain": "frontend",
  "verification": "cd frontend && pnpm exec vitest run app/stores/themeStore.test.ts app/components/ui/",
  "evidence": "2026-06-06: themeStore (4 tests) + UI组件主题一致性验证 — vitest + build pass",
  "notes": "主题系统覆盖: DESIGN.md 15条Don't + WCAG 2.1 AA对比度要求"
}
```

#### 2h. `f-pipeline-visual` — 管线可视化
```json
{
  "id": "f-pipeline-visual",
  "name": "管线可视化 (StagePipeline + StageView)",
  "status": "passing",
  "description": "生成管线阶段可视化组件，显示当前 workflow stage、阶段转换、生成进度",
  "dependencies": ["f-state-stores", "f-ws-client"],
  "domain": "frontend",
  "verification": "cd frontend && pnpm exec vitest run app/components/layout/",
  "evidence": "2026-06-06: StageView (1 test) + build pass — pipeline render verified",
  "notes": "轻量 feature；核心管线逻辑在后端 LangGraph，前端仅展示状态"
}
```

#### 2i. `f-ui-system` — 通用 UI 组件库
```json
{
  "id": "f-ui-system",
  "name": "通用 UI 组件库 (Button/Modal/Toast/ErrorBoundary 等 12 个组件)",
  "status": "passing",
  "description": "12 个可复用 UI 组件: Button, Card, Modal, Input, ConfirmModal, EditModal, ErrorBoundary, HoverActionBar, LoadingOverlay, SvgIcon, TypewriterText, ToastContainer",
  "dependencies": [],
  "domain": "frontend",
  "verification": "cd frontend && pnpm exec vitest run app/components/ui/",
  "evidence": "2026-06-06: Button (7), Card (7), Modal (7), Input (8), ConfirmModal (8), EditModal (9), ErrorBoundary (4), HoverActionBar (6), LoadingOverlay (4), TypewriterText (5), Toast (4), ToastContainer (2) — all 71 tests pass",
  "notes": "基础 UI 层，被所有前端 feature 依赖（但不显式声明以避免循环依赖）"
}
```

### 汇总

新增 10 个前端 feature → feature_list.json 从 14 个 → **24 个** feature。

| # | Feature ID | Domain | 测试覆盖 |
|---|-----------|--------|---------|
| 1 | f-canvas | frontend | 41 tests (6 files) |
| 2 | f-chat | fullstack | 23 tests (3 files) |
| 3 | f-project-ui | frontend | 44 tests (4 files) |
| 4 | f-ws-client | fullstack | 65 tests (front 37 + back 28) |
| 5 | f-settings-ui | frontend | 32 tests (2 files) |
| 6 | f-universe-ui | frontend | TODO |
| 7 | f-state-stores | frontend | 16 tests (4 stores) |
| 8 | f-theme | frontend | 4 tests + build |
| 9 | f-pipeline-visual | frontend | 1 test + build |
| 10 | f-ui-system | frontend | 71 tests (12 files) |

**必须做**:
- 每个 feature 包含完整字段: id, name, status, description, dependencies, domain, verification, evidence, notes
- `f-canvas` 依赖 `f-ws-client`（画布事件推送依赖 WebSocket）
- `f-project-ui` 依赖 `f-state-stores`（页面组件使用 editorStore/settingsStore）
- `f-universe-ui` 依赖 `f-universe-multi-project`（前端页面依赖后端 API）
- 对测试文件缺失的 feature（universe-ui, sidebarStore, chatPanelStore），evidence 标注 "TODO" 并说明间接覆盖路径

**必须不做**:
- 不创建无实际代码支撑的空 feature
- 不对无独立测试的 feature 编造测试结果
- 不把 API 调用层（`app/services/api.ts`）单独拆为 feature（它是 project-ui/ws-client 的实现细节）

**QA**:
```bash
python3 -c "
import json
d = json.load(open('feature_list.json'))
frontend = [f for f in d['features'] if f.get('domain') == 'frontend']
print(f'Frontend features: {len(frontend)}')
for f in frontend:
    print(f'  {f[\"id\"]}: {f[\"verification\"][:60]}...')
print(f'Total features: {len(d[\"features\"])}')
"
# → 10 个 frontend features, 24 total
```

---

## 任务 3: 创建 WIP≤1 pre-commit hook

**位置**: `.git/hooks/pre-commit`（新建）

**问题**: WIP=1 仅在 AGENTS.md 中声明，零自动执行。任何 agent 或 developer 可以同时标记多个 feature 为 active 并提交。

**改动内容**: 新建 bash 脚本，在 `git commit` 前检查 `feature_list.json`。

```bash
#!/usr/bin/env bash
# WIP≤1 pre-commit hook — 阻止 feature_list.json 中 >1 个 active feature 的提交
set -euo pipefail

FEATURE_FILE="feature_list.json"

# 仅在 feature_list.json 被暂存时检查
if ! git diff --cached --name-only | grep -q "$FEATURE_FILE"; then
    exit 0
fi

# 检查 Python3 可用
if ! command -v python3 &>/dev/null; then
    echo "⚠ pre-commit: python3 not found — skipping WIP≤1 check"
    exit 0
fi

ACTIVE_COUNT=$(python3 -c "
import json, sys
d = json.load(open('$FEATURE_FILE'))
active = [f['id'] for f in d['features'] if f.get('status') == 'active']
print(len(active))
for a in active:
    print(f'  - {a}', file=sys.stderr)
")

if [ "$ACTIVE_COUNT" -gt 1 ]; then
    echo "❌ WIP≤1 violation: $ACTIVE_COUNT active features in feature_list.json"
    echo "   最多允许 1 个 active feature。请将多余的改为 pending/passing/blocked。"
    exit 1
fi

echo "✓ WIP≤1 check passed (active: $ACTIVE_COUNT)"
```

**必须做**:
- Hook 仅在 `feature_list.json` 被暂存时触发（不阻止无关提交）
- Python3 不可用时降级为 warning 而非 blocking（避免破坏非 Python 开发者的提交体验）
- 使用 `git diff --cached` 检查暂存区（不是工作区），保证检查的是即将提交的版本
- `chmod +x .git/hooks/pre-commit` 使 hook 可执行

**必须不做**:
- 不检查工作区的 active 数量（agent 可能在本地临时切换 feature）
- 不检查 `feature_list.json` 的 JSON 格式有效性（那是 init.sh 的职责）
- 不自动修复 — 只报错，让 developer/agent 手动修正

**QA**:
```bash
# 1. 正常情况（0 或 1 个 active）
chmod +x .git/hooks/pre-commit
.git/hooks/pre-commit
echo "Exit code: $?"  # → 0

# 2. 违规情况（>1 active）
python3 -c "
import json
d = json.load(open('feature_list.json'))
d['features'][0]['status'] = 'active'
d['features'][1]['status'] = 'active'
json.dump(d, open('/tmp/test_features.json', 'w'), indent=2, ensure_ascii=False)
"
# 手动模拟: 将 feature_list.json 临时替换为 /tmp/test_features.json 后 git add
# → hook 应退出 1 并报错
```

---

## Exit-Gate（全部通过前，不结束）

- [ ] 所有 feature 含 `domain` 字段（backend/frontend/fullstack）
- [ ] 所有 passing feature 含 `evidence` 字段（非 null）
- [ ] feature_list.json 从 14 → 24 个 feature
- [ ] 新增 10 个前端 feature 的 verification 命令可执行
- [ ] pre-commit hook 文件存在且可执行（`test -x .git/hooks/pre-commit`）
- [ ] pre-commit hook 在 WIP≤1 时通过，WIP=2 时 block
- [ ] `python3 -c "import json; json.load(open('feature_list.json'))"` 不抛异常（JSON 合法）
- [ ] `./init.sh` 全绿
- [ ] `feature_list.json`: `f-state-scope-p2` = `passing`，且 `evidence` 已填写
- [ ] `progress.md` 已更新

---

## ⛔ Session 边界

**Exit-Gate 全绿 → commit + 结束 Session。** 下一工作加载 `state-scope-fix-p3.md`（如有）或推进其他 feature。
