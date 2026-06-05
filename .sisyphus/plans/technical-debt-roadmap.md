# 技术债务清理 — Roadmap

> **角色**: 路线图，仅供导航。**不要直接执行本文件。**
> **使用方式**: 阅读 → 检查 `feature_list.json` → 加载对应的 `p{N}.md` 执行。

---

## Feature 依赖链

```
f-technical-debt (not_started)
  └─ 无前置依赖 — 可立即启动
```

---

## 各 Phase 概要

| Phase | 计划文件 | 内容 | 改动文件 | 耗时 |
|---|---|---|---|---|
| **P0** | `technical-debt-p0.md` | Ruff 规则 + Redis 提取 + SLF001 修复 + N815 | 9 个 | ~2h |
| **P1** | `technical-debt-p1.md` | 75 处 BLE001(裸except) 替换为具体异常类型 | 25 个 | ~5h |

---

## 开始前（冷启动）

```bash
# 1. 确认 feature_list.json 状态
cat feature_list.json | python3 -c "import sys,json;f=json.load(sys.stdin);[print(i['id'],i['status']) for i in f['features'] if i['id']=='f-technical-debt']"

# 2. 前置检查
./init.sh   # 必须全绿

# 3. 根据状态加载对应文件
#    not_started → 加载 technical-debt-p0.md
#    p0=passing → 加载 technical-debt-p1.md
```

---

## 关键决策（已确认）

- Bare except → 具体异常类型替换（无法确定的 `# noqa: BLE001` + 英文注释）
- SLF001 测试 316 处 → `per-file-ignores "tests/**" = ["SLF001"]` 静默
- Orchestrator → 最小拆分（仅 Redis 助手 + 2 公共方法）
- TDD tiered：确定路径 RED-GREEN，非确定 GREEN-only
- Ruff 规则：`extend-select = ["SLF001", "N815"]`

---

## 验证命令

```bash
cd backend && uv run ruff check app tests && uv run pytest -q
```

## Guardrails

- ❌ 不碰前端（除 `isLoading` 重命名可能涉及的引用搜索）
- ❌ 不完整拆分 Orchestrator
- ❌ 不修改任何 except 块运行时行为
- ❌ 不修复预存问题（Redis race condition 等，仅记录）
- ❌ 单 Phase 内不分 Session — 执行完 Gate 再停
