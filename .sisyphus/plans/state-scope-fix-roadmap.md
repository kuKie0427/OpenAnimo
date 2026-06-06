# State + Scope 子系统修复 — Roadmap

> **角色**: 路线图，仅供导航。**不要直接执行本文件。**
> **使用方式**: 阅读 → 检查 `feature_list.json` → 加载对应的 `p{N}.md` 执行。

---

## Feature 依赖链

```
f-state-scope-p2 (not_started)
  └─ f-verification-fix (passing)
```

---

## 各 Phase 概要

| Phase | 计划文件 | 内容 | 改动文件 | 耗时 |
|---|---|---|---|---|
| **P2** | `state-scope-fix-p2.md` | feature_list 重构 (domain + evidence + 前端覆盖) + blocked 状态启用 + WIP≤1 pre-commit hook | 3 个 | ~3h |

---

## 开始前（冷启动）

```bash
# 1. 确认 feature_list.json 状态
cat feature_list.json | python3 -c "import sys,json;f=json.load(sys.stdin);[print(i['id'],i['status']) for i in f['features'] if i['id']=='f-state-scope-p2']"

# 2. 确认前置依赖
cat feature_list.json | python3 -c "import sys,json;f=json.load(sys.stdin);[print(i['id'],i['status']) for i in f['features'] if i['id']=='f-verification-fix']"
# 必须 = passing

# 3. 前置检查
./init.sh   # 必须全绿

# 4. feature 不存在 → 加载 state-scope-fix-p2.md
```

---

## 关键决策（已确认）

- **domain 字段**: `"backend"` / `"frontend"` / `"fullstack"`（按改动域分类）
- **evidence 字段**: 已有证据从 progress.md + 最新 test run 推算，"?" 标记无法确认的历史 evidence
- **前端 feature**: 按页面/组件域分组，不按实现文件拆分（避免过度原子化）
- **blocked 状态**: 仅标记有硬性外部依赖的 feature（Docker/外部 API），不标记可独立验证的 feature
- **pre-commit hook**: bash 脚本，依赖 `python3` + `jq` 不可用时降级为 warning

---

## 验证命令

```bash
# feature_list.json 结构完整性
python3 -c "
import json
d = json.load(open('feature_list.json'))
for f in d['features']:
    assert 'domain' in f, f'Missing domain: {f[\"id\"]}'
    assert 'evidence' in f or f['status'] == 'active', f'Missing evidence: {f[\"id\"]}'
    assert f['domain'] in ('backend','frontend','fullstack'), f'Bad domain: {f[\"id\"]}'
print(f'{len(d[\"features\"])} features OK')
"

# pre-commit hook 生效
echo '[{"id":"x","status":"active"},{"id":"y","status":"active"}]' > /tmp/test_features.json
.git/hooks/pre-commit 2>&1 || echo "Hook blocked WIP=2 (expected)"
rm /tmp/test_features.json
```

## Guardrails

- ❌ 不修改 feature 的 `verification` 命令（仅添加元数据）
- ❌ 不新增/删除 feature 的业务逻辑
- ❌ 不修改前端/后端代码（仅 feature_list.json + pre-commit hook）
- ❌ 不将 `blocked` 用于可本地验证的 feature（即 pytest 能跑的 feature 不应标记为 blocked）
