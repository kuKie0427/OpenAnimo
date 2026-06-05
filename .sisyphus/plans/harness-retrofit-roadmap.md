# openOii Harness 工程化改造 — 路线图

> **角色**: 路线图，仅供导航。**不要直接执行本文件。**
> **使用方式**: 阅读 → 检查 `feature_list.json` 判断当前需要哪个 Phase → 加载对应的 `harness-retrofit-p{0-3}.md` 执行。

---

## 当前 Harness 评分：220/500（44%）

| 子系统 | 评分 | 关键缺失 |
|---|---|---|
| Instructions | 65 | feature_list、init.sh、session handoff |
| State | 40 | feature_list.json、人类可读进度 |
| Verification | 55 | 无自动化 init.sh、无 pass-gate |
| Scope | 35 | 无 WIP=1、无依赖图 |
| Lifecycle | 25 | 无 progress.md、无 cleanup |

---

## Phase 依赖链

```
Phase 0 (P0) ── 无依赖，立即开始
    │
    │  Gate: init.sh 全绿 + f-harness-p0 = passing → 结束会话
    ▼
Phase 1 (P1) ── 新会话，依赖 P0
    │
    │  Gate: AgentTrace + Prompt VERSION → 结束会话
    ▼
Phase 2 (P2) ── 新会话，依赖 P1
    │
    │  Gate: 验证 + 降级 + WS schema → 结束会话
    ▼
Phase 3 (P3) ── 新会话，远期按需
```

---

## 各 Phase 概要

| Phase | 计划文件 | 内容 | 耗时 | 改动文件数 |
|---|---|---|---|---|
| **P0** | `harness-retrofit-p0.md` | init.sh / feature_list.json / progress.md / AGENTS.md 更新 | 2h | 4（3 新建 + 1 修改） |
| **P1** | `harness-retrofit-p1.md` | Prompt 版本管理 / AgentTrace 执行追踪 | 5h | 6（3 新建 + 3 修改） |
| **P2** | `harness-retrofit-p2.md` | 产出物自动验证 / 降级可测试化 / WS Schema 强化 | 8h | 5（3 新建 + 2 修改） |
| **P3** | `harness-retrofit-p3.md` | 指标仪表板 / 多 Agent 并行 | 8h+ | 远期 |

---

## 开始前

```bash
cat feature_list.json    # 如果不存在 → 执行 Phase 0
                          # 如果 f-harness-p0 != passing → 执行 Phase 0
                          # 如果 f-harness-p0 = passing, f-harness-p1 != passing → 执行 Phase 1
                          # ...以此类推
```

**一个会话 = 一个 Phase。Gate 通过后结束会话。新会话从此文件重新导航。**
