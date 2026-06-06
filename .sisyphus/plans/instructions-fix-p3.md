# Phase 3 — AGENTS.md 渐进披露重构（内联约定 → 摘要 + 链接到专题文档）

> **耗时**: ~1.5h | **改动文件**: 3 个（仅 AGENTS.md 系列） | **WIP=1**

---

## Pre-Gate（不满足则 STOP）

- [ ] `feature_list.json` 中 `f-state-scope-p2` = `passing`（前置依赖）
- [ ] `f-instructions-p3` 在 `feature_list.json` 中不存在 → 本 phase 创建
- [ ] `./init.sh` 全绿
- [ ] 确认 `.trellis/spec/` 下 19 篇专题文档存在且可读

> 如果 Pre-Gate 不满足，**停止**。

---

## 问题诊断（背景）

当前 AGENTS.md 三件套都存在"伪路由文件"问题：行数在 50-200 范围内，但所有约定/反模式全部内联展示，没有链接到 `.trellis/spec/` 下的专题文档。Harness 工程要求 **Tier 3 context loading**（按需加载专题文档），当前结构违背了这一原则。

同时 `.trellis/spec/` 下已有 **19 篇高质量专题文档**，但完全未被 AGENTS.md 引用 —— 这是"隐藏的百科全书"反模式。

---

## 任务 0: 初始化 feature_list

**位置**: `feature_list.json`

**操作**: 在 features 数组末尾追加 `f-instructions-p3` entry（在 f-ui-system 之后）:

```json
{
  "id": "f-instructions-p3",
  "name": "Instructions 子系统修复 (AGENTS.md 渐进披露: 内联约定→摘要+链接到专题文档)",
  "status": "active",
  "description": "将 backend/frontend AGENTS.md 的内联约定/反模式替换为摘要+链接到 .trellis/spec/ 下的 19 篇专题文档",
  "dependencies": ["f-state-scope-p2"],
  "domain": "fullstack",
  "verification": "grep -c '.trellis/spec/' AGENTS.md backend/AGENTS.md frontend/AGENTS.md | awk -F: '{s+=$2} END {print s}' | xargs -I{} test {} -ge 12",
  "evidence": null,
  "notes": "Harness 诊断 Phase 3 — 从伪路由文件升级到真正的渐进披露（Tier 3 context loading）"
}
```

**QA**: `python3 -c "import json; d=json.load(open('feature_list.json')); f=[i for i in d['features'] if i['id']=='f-instructions-p3'][0]; assert f['status']=='active'"` → no error

---

## 任务 1: Root AGENTS.md — 添加"详细指南"专题文档链接

**位置**: `AGENTS.md`（根目录，当前 153 行）

**原则**: 根 AGENTS.md 已经是一个合格的路由文件（153 行，有 Harness 约定 + 概览 + 目录树 + 快速查找 + 参考链接）。仅需在末尾添加跨端专题文档链接。

**操作**: 在文件末尾"## 参考"部分之后（line 153 之后），追加以下内容:

```markdown

## 详细指南

根级跨端专题文档存放在 `.trellis/spec/guides/`:

| 主题 | 文档 |
|------|------|
| 跨层开发思维 | [cross-layer-thinking-guide](.trellis/spec/guides/cross-layer-thinking-guide.md) |
| 代码复用模式 | [code-reuse-thinking-guide](.trellis/spec/guides/code-reuse-thinking-guide.md) |
| 编排架构设计 | [orchestration-architecture](.trellis/spec/guides/orchestration-architecture.md) |

后端专题文档（数据库/日志/错误处理/WS 契约等 8 篇）→ 详见 `backend/AGENTS.md`
前端专题文档（组件/状态管理/类型安全/样式规范等 7 篇）→ 详见 `frontend/AGENTS.md`
```

**预期效果**: 根 AGENTS.md 从 153 → ~170 行（仍在 200 行以内）

**必须做**:
- 链接使用相对路径（`./` not `../`）
- 保持中文描述与现有文档风格一致

**必须不做**:
- 不修改 Harness 约定（1-19 行）
- 不修改"快速查找"表（它映射源码位置，不是文档位置）

---

## 任务 2: Backend AGENTS.md — "后端约定" + "反模式" → 摘要 + 链接

**位置**: `backend/AGENTS.md`（当前 159 行）

**原则**: 将 `## 后端约定`（105-140 行，~36 行）和 `## 后端反模式（禁止）`（142-151 行，~10 行）替换为摘要 + 指向 `.trellis/spec/backend/` 的链接。"已知问题"（154-159 行）保持内联。

### 2a. 替换"后端约定"（lines 105-140）

**原内容**（105-140）:
```
## 后端约定

### 代码规范
- 文件命名: snake_case...
- 类命名: PascalCase...
- 行宽: Ruff line-length=100
- 异步: 几乎全异步...
- 包管理: uv...

### API 模式
- 路由文件在 app/api/v1/routes/...
- 请求/响应用 Pydantic schemas/ 严格校验...
- ...

### 服务层模式
- ...

### 测试模式
- ...

### 数据库
- ...
```

**替换为**（约 15 行）:

```markdown
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
```

### 2b. 替换"后端反模式"（lines 142-151）

**原内容**（~10 行）:
```
## 后端反模式（禁止）
1. 不要用裸 except Exception:...
2. 不要忽略 init_db() 的副作用...
...
7. 不要忘记更新 uv.lock...
```

**替换为**（约 6 行）:

```markdown
## 后端反模式（禁止）

详见 [quality-guidelines](.trellis/spec/backend/quality-guidelines.md) 的反模式章节。

速记：禁止裸 except · 禁止忽略副作用 · 禁止假设多实例 · 禁止 bypass 私有方法 · 禁止路由写业务逻辑
```

### 预期效果

| 指标 | 改前 | 改后 |
|------|------|------|
| backend/AGENTS.md 行数 | 159 | ~130 |
| 到 .trellis/spec/ 的链接数 | 0 | 8+ |

**必须做**:
- 所有链接路径以 `.trellis/spec/backend/` 开头
- "核心原则速记"保留 1 行涵盖关键规则（避免完全抹掉内联上下文）
- "已知问题"（154-159）完全不受影响

**必须不做**:
- 不删除或移动专题文档中的内容
- 不修改"快速查找""开发命令""概览""目录结构"部分

**QA**: `grep -c "\.trellis/spec/backend/" backend/AGENTS.md` → ≥ 8

---

## 任务 3: Frontend AGENTS.md — "前端约定" + "反模式" → 摘要 + 链接

**位置**: `frontend/AGENTS.md`（当前 176 行）

**原则**: 同任务 2，但匹配前端专题文档结构。

### 3a. 替换"前端约定"（lines 109-154，~46 行）

**原内容**:
```
## 前端约定

### 代码规范
### 组件模式
### 状态管理模式
### 样式规范
### 测试模式
### 配置/环境变量
```

**替换为**（约 18 行）:

```markdown
## 前端约定

详细开发规范见 `.trellis/spec/frontend/` 专题文档:

| 主题 | 文档 |
|------|------|
| 代码质量规范（命名/路径别名/Tailwind/类型） | [quality-guidelines](.trellis/spec/frontend/quality-guidelines.md) |
| 组件模式（页面/UI/Shape 组件、懒加载、测试同目录） | [component-guidelines](.trellis/spec/frontend/component-guidelines.md) |
| 状态管理（Zustand/React Query/Mock 策略） | [state-management](.trellis/spec/frontend/state-management.md) |
| Hook 设计模式（WebSocket/DOM/Canvas） | [hook-guidelines](.trellis/spec/frontend/hook-guidelines.md) |
| TypeScript 类型安全（严格模式/any 清理路径） | [type-safety](.trellis/spec/frontend/type-safety.md) |
| 目录结构与模块职责 | [directory-structure](.trellis/spec/frontend/directory-structure.md) |

核心原则速记：Tab 缩进 · `~/` 别名 · Tailwind only · tsc 保类型 · vitest globals:true · 无 ESLint/Prettier（有意为之）
```

> "样式规范"保留对 `DESIGN.md` 的引用行在文末（或保留在"快速查找"中已存在）

### 3b. 替换"前端反模式"（lines 156-165，~10 行）

**替换为**（约 6 行）:

```markdown
## 前端反模式（禁止）

详见 [quality-guidelines](.trellis/spec/frontend/quality-guidelines.md) 的反模式章节。

速记：禁止直接调 API（用 services/api.ts）· 禁止 any（逐步清理）· 禁止 app.config.ts · 禁止生产 console · 禁止忘 reset()
```

### 预期效果

| 指标 | 改前 | 改后 |
|------|------|------|
| frontend/AGENTS.md 行数 | 176 | ~155 |
| 到 .trellis/spec/ 的链接数 | 0 | 7+ |

**必须做**:
- "已知问题"（168-176）完全不受影响 — 它是活文档，随代码变化频繁更新
- "样式规范"中对 `DESIGN.md` 的引用保留（可在快速查找表中）

**必须不做**:
- 不修改任何 `.trellis/spec/frontend/` 下的文档

**QA**: `grep -c "\.trellis/spec/frontend/" frontend/AGENTS.md` → ≥ 7

---

## Exit-Gate（全部通过前，不结束）

- [ ] 根 AGENTS.md 含 `.trellis/spec/guides/` 链接（≥3 个）
- [ ] Backend AGENTS.md 含 `.trellis/spec/backend/` 链接（≥7 个）
- [ ] Frontend AGENTS.md 含 `.trellis/spec/frontend/` 链接（≥6 个）
- [ ] 三篇 AGENTS.md 行数均 < 200（根 ~170, backend ~130, frontend ~155）
- [ ] 每篇的"快速查找""开发命令""已知问题""Harness 约定"部分未受影响
- [ ] `./init.sh` 全绿
- [ ] `feature_list.json`: `f-instructions-p3` = `passing` 且 `evidence` 已填写
- [ ] `progress.md` 已更新

---

## ⛔ Session 边界

**Exit-Gate 全绿 → commit + 结束 Session。** 下一工作从 feature_list.json 中查找 `not_started` feature 继续。
