# 验证管线修复 — Roadmap

> **角色**: 路线图，仅供导航。**不要直接执行本文件。**
> **使用方式**: 阅读 → 检查 `feature_list.json` → 加载对应的 `p{N}.md` 执行。

---

## Feature 依赖链

```
f-verification-fix (not_started)
  └─ 无前置依赖 — 可立即启动
```

---

## 各 Phase 概要

| Phase | 计划文件 | 内容 | 改动文件 | 耗时 |
|---|---|---|---|---|
| **P1** | `verification-fix-p1.md` | 修复 init.sh + StubImage 测试 + pyright 强制执行 + CI 工作流 | 5 个 | ~2h |

> Phase 1 同时覆盖诊断中发现的 4 个子任务。验证管线修复后不再拆分更多 phase。

---

## 开始前（冷启动）

```bash
# 1. 确认 feature_list.json 状态
cat feature_list.json | python3 -c "import sys,json;f=json.load(sys.stdin);[print(i['id'],i['status']) for i in f['features'] if i['id']=='f-verification-fix']"

# 2. 前置检查
./init.sh   # 必须全绿（init.sh 本身修复后）

# 3. 如果 feature 不存在 → 加载 verification-fix-p1.md
```

---

## 关键决策（已确认）

- init.sh `pytest -x` 移除：全量运行而非首个失败退出，配合 `|| echo` 降级为非致命
- StubImage 502：monkeypatch `ImageComposer._download_image` 返回微小 PIL Image（与现有 monkeypatch 模式一致）
- pyright：加入 `[tool.pyright]` 配置 + dev-dependencies，init.sh 中转为强制性（失败则报错）
- E2E：**不放 init.sh**（需全栈运行，太重），改为添加 CI workflow `ci.yml` 在 PR 时跑
- CI workflow：新增 `.github/workflows/ci.yml`，PR 时跑 ruff + pytest + tsc + vitest

---

## 验证命令

```bash
cd backend && uv run pytest -q && uv run ruff check app tests
cd frontend && pnpm tsc --noEmit && pnpm vitest run && pnpm build
```

## Guardrails

- ❌ 不修改被测试代码（仅修 init.sh / CI / 测试桩）
- ❌ 不新增 Python 依赖（除 pyright 加入 dev-dependencies）
- ❌ 不触及前端业务代码
- ❌ 不修复其他预存问题（仅限 init.sh 验证链 + StubImage stub）
