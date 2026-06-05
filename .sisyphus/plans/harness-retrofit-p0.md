# Phase 0 — 最小可行 Harness（P0）

> **耗时**: ~2h | **改动文件**: 4 个（3 新建 + 1 修改） | **WIP=1**

---

## 前置检查（不满足则 STOP）

- [ ] `openOii/feature_list.json` **不存在**（或存在但 `f-harness-p0` 状态为 `not_started` 或 `active`）
- [ ] 已阅读 `openOii/AGENTS.md`
- [ ] `openOii/backend/` 目录存在，`uv sync` 可执行
- [ ] `openOii/frontend/` 目录存在，`pnpm install` 可执行

> 如果 `feature_list.json` 已存在且 `f-harness-p0 = passing`，**停止**。加载 `harness-retrofit-p1.md` 继续。

---

## 执行内容

### 任务 1: 创建 `init.sh`

**位置**: `openOii/init.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== openOii Harness Init ==="

# Check tools
command -v uv >/dev/null 2>&1 || { echo "❌ uv not found. Install: https://docs.astral.sh/uv/"; exit 1; }
command -v pnpm >/dev/null 2>&1 || { echo "❌ pnpm not found. Install: npm i -g pnpm"; exit 1; }

# Backend
echo "[1/6] Installing Python dependencies..."
cd backend && uv sync && cd ..

# Frontend
echo "[2/6] Installing Node dependencies..."
cd frontend && pnpm install && cd ..

# DB migration
echo "[3/6] Running database migrations..."
cd backend && uv run alembic upgrade head && cd ..

# Backend checks
echo "[4/6] Backend: lint + type + test..."
cd backend
uv run ruff check app tests || { echo "❌ ruff failed"; exit 1; }
uv run pyright app/ || { echo "❌ pyright failed"; exit 1; }
uv run pytest -x --timeout=30 -q || { echo "❌ pytest failed"; exit 1; }
cd ..

# Frontend checks
echo "[5/6] Frontend: type + unit test + build..."
cd frontend
pnpm tsc --noEmit || { echo "❌ tsc failed"; exit 1; }
pnpm vitest run || { echo "❌ vitest failed"; exit 1; }
pnpm build || { echo "❌ build failed"; exit 1; }
cd ..

echo ""
echo "✅ Harness ready. All checks passed."
```

**验证**: `chmod +x init.sh && ./init.sh` — 必须在 5 分钟内全部通过。

---

### 任务 2: 创建 `feature_list.json`

**位置**: `openOii/feature_list.json`

```json
{
  "features": [
    {
      "id": "f-harness-p0",
      "name": "Harness Phase 0 — 最小可行基础设施",
      "description": "init.sh / feature_list.json / progress.md / AGENTS.md harness section",
      "dependencies": [],
      "status": "active",
      "verification": "./init.sh && python -c \"import json; d=json.load(open('feature_list.json')); assert d['features'][0]['status']=='passing'\"",
      "notes": "这是 harness 改造的起点"
    },
    {
      "id": "f-pipeline-core",
      "name": "核心生成管线 (17-stage LangGraph)",
      "dependencies": [],
      "status": "passing",
      "verification": "cd backend && uv run pytest tests/test_orchestration/ tests/test_agents/ -q"
    },
    {
      "id": "f-character-consistency",
      "name": "角色一致性 (Bible + InsightFace + Eval)",
      "dependencies": ["f-pipeline-core"],
      "status": "passing",
      "verification": "cd backend && uv run pytest tests/ -k 'consistency or bible' -q"
    },
    {
      "id": "f-critic-loop",
      "name": "CriticAgent VLM 质量审查回环",
      "dependencies": ["f-pipeline-core"],
      "status": "passing",
      "verification": "cd backend && uv run pytest tests/ -k 'critic' -q"
    },
    {
      "id": "f-tts-audio",
      "name": "TTS 配音 + BGM 混音",
      "dependencies": ["f-pipeline-core"],
      "status": "passing",
      "verification": "cd backend && uv run pytest tests/ -k 'audio' -q"
    },
    {
      "id": "f-export",
      "name": "PDF/Webtoon 导出",
      "dependencies": ["f-pipeline-core"],
      "status": "passing",
      "verification": "cd backend && uv run pytest tests/test_api/test_export.py -q"
    },
    {
      "id": "f-style-template",
      "name": "风格模板系统 (14 内置 + 自定义)",
      "dependencies": ["f-pipeline-core"],
      "status": "passing",
      "verification": "cd backend && uv run pytest tests/test_api/test_style_templates.py -q"
    },
    {
      "id": "f-universe-multi-project",
      "name": "跨项目 IP 宇宙",
      "dependencies": ["f-character-consistency"],
      "status": "passing",
      "verification": "cd backend && uv run pytest tests/test_api/test_universes.py -q"
    },
    {
      "id": "f-version-compare",
      "name": "版本对比与回滚 (ArtifactVersion)",
      "dependencies": ["f-pipeline-core"],
      "status": "passing",
      "verification": "cd backend && uv run pytest tests/ -k 'version or snapshot' -q"
    },
    {
      "id": "f-technical-debt",
      "name": "技术债务清理 (32 裸except + 7 SLF001 + split orchestrator)",
      "dependencies": [],
      "status": "not_started",
      "verification": "cd backend && uv run ruff check app tests && uv run pytest -q"
    }
  ]
}
```

**规则**:
- `active` 同时只能 1 个
- `passing` **只能由 verification 命令执行成功后标记**（pass-gate）
- 新增 feature 时必须声明 `dependencies`

---

### 任务 3: 创建 `progress.md`

**位置**: `openOii/progress.md`

```markdown
# Progress Log

## 模板 — 每次会话结束时追加以下格式

<!--
## YYYY-MM-DD — Session: <简短描述>
- **做了什么**:
- **改了什么文件**:
- **当前状态**:
- **决策**:
- **阻断**:
- **下次**:
-->

---
## 2026-06-06 — Session: harness-phase-0-init
- **做了什么**: 创建 init.sh、feature_list.json、progress.md；更新 AGENTS.md 加 harness section
- **改了什么文件**: init.sh (new), feature_list.json (new), progress.md (new), AGENTS.md (modified)
- **当前状态**: f-harness-p0 → passing
- **决策**: 采用 split-plan 结构，每个 Phase 一个计划文件
- **阻断**: 无
- **下次**: Phase 1 — Prompt 版本管理 + AgentTrace
```

---

### 任务 4: 更新 `AGENTS.md`（追加 Harness 约定）

**位置**: `openOii/AGENTS.md`

在文件开头（`# openOii — 项目知识库（根）` 之前）插入：

```markdown
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
```

---

## Gate（全部通过前，不加载 Phase 1）

- [x] `./init.sh` 全绿（backend + frontend 全部通过）
- [x] `feature_list.json` 存在且 `f-harness-p0` = `passing`
- [x] `progress.md` 存在且有本次 session 记录
- [x] `AGENTS.md` 含 Harness 约定 section
- [x] 现有测试套件无回归

---

## ⛔ Session 边界

**Gate 全部通过后，执行 `/handoff` 然后等待用户开启新会话。** 禁止继续加载 `harness-retrofit-p1.md`。

1. 确认 Gate 全绿 → `git commit` → **执行 `/handoff`**
2. 告知用户："Phase 0 完成。请开启新会话，加载 handoff 文件继续 Phase 1"
3. 新会话 → 读 handoff → 读 roadmap → 读 `feature_list.json` → 确认 `f-harness-p0 = passing` → 加载 `harness-retrofit-p1.md`
