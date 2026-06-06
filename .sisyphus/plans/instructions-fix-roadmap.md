# Instructions 子系统修复 — Roadmap

> **角色**: 路线图，仅供导航。**不要直接执行本文件。**
> **使用方式**: 阅读 → 检查 `feature_list.json` → 加载 `instructions-fix-p3.md` 执行。

---

## Feature 依赖链

```
f-instructions-p3 (not_started)
  └─ f-state-scope-p2 (passing)
```

---

## 各 Phase 概要

| Phase | 计划文件 | 内容 | 改动文件 | 耗时 |
|---|---|---|---|---|
| **P3** | `instructions-fix-p3.md` | AGENTS.md 渐进披露重构：内联约定 → 摘要+链接到 `.trellis/spec/` 19 篇专题文档 | 3 个 | ~1.5h |

---

## 开始前（冷启动）

```bash
# 1. 确认前置依赖
cat feature_list.json | python3 -c "import sys,json;f=json.load(sys.stdin);[print(i['id'],i['status']) for i in f['features'] if i['id'] in ('f-state-scope-p2','f-instructions-p3')]"

# 2. 前置检查
./init.sh

# 3. feature 不存在 → 加载 instructions-fix-p3.md
```

---

## 关键决策（已确认）

- **不移动内容**：`.trellis/spec/` 专题文档保持原位，仅在 AGENTS.md 中添加链接
- **替换策略**：大段内联约定 → 2-3 行摘要 + `→ 详见 [专题文档]` 链接；快速查找表 → 添 topic doc 列
- **保留部分**：已知问题、目录结构、快速查找源码映射保持内联（它们随代码频繁变更）
- **行宽上限**：每篇 AGENTS.md 保持在 200 行以内
- **链接格式**：相对路径 `.trellis/spec/backend/quality-guidelines.md`（GitHub 可点击）

---

## 验证命令

```bash
# 行数检查
wc -l AGENTS.md backend/AGENTS.md frontend/AGENTS.md
# → 预期根 <170, backend <150, frontend <160（均从当前值减少）

# 链接有效性
grep -c "\.trellis/spec/" AGENTS.md backend/AGENTS.md frontend/AGENTS.md
# → 预期 ≥15 个链接（根 3-5 + backend 5-8 + frontend 5-8）
```

## Guardrails

- ❌ 不移动/重命名 `.trellis/spec/` 下的任何文件
- ❌ 不修改专题文档内容
- ❌ 不新增专题文档
- ❌ 不修改 AGENTS.md 的 "Harness 约定" "目录结构" "快速查找" "开发命令" "已知问题" 部分
