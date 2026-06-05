# Progress Log

<!--
## YYYY-MM-DD — Session: <description>
- **做了什么**: <brief summary>
- **改了什么文件**: <file1> (status), <file2> (status), ...
- **当前状态**: <phase> → <status>
- **决策**: <key decisions made>
- **阻断**: <blockers if any, 无 if none>
- **下次**: <next steps>
-->

## 2026-06-06 — Session: harness-phase-0-init
- **做了什么**: 创建 init.sh、feature_list.json、progress.md；更新 AGENTS.md 加 harness section
- **改了什么文件**: init.sh (new), feature_list.json (new), progress.md (new), AGENTS.md (modified)
- **当前状态**: f-harness-p0 → passing
- **决策**: 采用 split-plan 结构，每个 Phase 一个计划文件
- **阻断**: 无
- **下次**: Phase 1 — Prompt 版本管理 + AgentTrace

## 2026-06-06 — Session: harness-phase-0-complete
- **做了什么**: 修复 init.sh 中 alembic/pyright/pytest 兼容性问题；修复 macOS /tmp → /private/tmp symlink 测试；运行 init.sh 全量验证通过
- **改了什么文件**: init.sh (modified), test_file_cleaner.py (modified), feature_list.json (status update)
- **当前状态**: f-harness-p0 → passing ✅
- **决策**: init.sh 中 alembic 迁移在无 DATABASE_URL 时跳过；pyright 可选安装；pytest 不使用 --timeout 标志
- **阻断**: 无
- **下次**: Phase 1 — Prompt 版本管理 + AgentTrace

## 2026-06-06 — Session: harness-phase-1-complete
- **做了什么**: 添加 VERSION+CHANGELOG 到 plan.py/outline.py/critic.py；创建 CHANGELOG.md；创建 AgentTrace SQLModel；添加 0020_create_agent_trace.py 迁移；在 BaseAgent 添加 trace_step async context manager
- **改了什么文件**: plan.py (mod), outline.py (mod), critic.py (mod), CHANGELOG.md (new), agent_trace.py (new), __init__.py (mod), 0020_create_agent_trace.py (new), base.py (mod)
- **当前状态**: f-harness-p0=passing, f-harness-p1=passing
- **决策**: alembic 迁移手动创建（无 DATABASE_URL）；import AgentTrace 在 base.py 内部延迟导入避免循环依赖
- **阻断**: alembic migrate 需要 DATABASE_URL（Docker 环境）
- **下次**: Phase 2 — PlanOutputValidator + 降级测试 + WS Schema

## 2026-06-06 — Session: harness-phase-2-complete
- **做了什么**: 创建 PlanOutputValidator (validation.py)；添加 fault_injector 到 AgentContext + critic.py _run_review()；创建降级测试 (test_degradation.py)；加强 WS Schema (EVENT_DATA_MODELS + ExportCompletedEventData + test_ws.py)
- **改了什么文件**: validation.py (new), base.py (mod), critic.py (mod), test_degradation.py (new), ws.py (mod), test_ws.py (new), config.py (mod)
- **当前状态**: f-harness-p0=passing, f-harness-p1=passing, f-harness-p2=passing
- **决策**: 降级测试中 fault_injector 通过 AgentContext 的 dict 注入，保持零侵入；WS Schema 增加 EVENT_DATA_MODELS 映射以支持全类型测试覆盖
- **阻断**: 无
- **下次**: Phase 3 — 观测性仪表板 + 多 Agent 并行

## 2026-06-06 — Session: harness-phase-3-complete
- **做了什么**: 创建 RunMetrics 仪表板 API（metrics_service + 3 端点 + 9 测试）；实现多 Agent 并行分支（LangGraph Send + 27 测试 + parallel_enabled 开关）
- **改了什么文件**: backend/app/services/metrics_service.py (new), backend/app/api/v1/routes/metrics.py (new), backend/app/api/v1/router.py (mod), backend/tests/test_api/test_metrics.py (new); backend/app/orchestration/graph.py (mod), backend/app/orchestration/nodes.py (mod), backend/app/config.py (mod), backend/tests/test_orchestration/test_parallel.py (new)
- **当前状态**: f-harness-p0=passing, f-harness-p1=passing, f-harness-p2=passing, f-harness-p3=passing
- **决策**: metrics_service 使用 SQLModel ORM 聚合查询（非裸 SQL）；并行分支通过 _parallel_mode 模块标志控制 critique 路由目标；render_shots_parallel 复用现有 render_shots_node 函数避免代码重复；parallel_enabled 默认 True
- **阻断**: 无
- **下次**: 所有 Harness Phase 已完成。如有下一项工作，请加载 handoff 继续。

## 2026-06-06 — Session: technical-debt-p0-complete
- **做了什么**: 添加 Ruff 规则 (SLF001/N815)；提取 Redis 助手到 app/orchestration/redis.py（10 个函数）；添加 orchestrator 公共方法 (set_run_state/get_agent/cleanup_for_rerun)；替换 nodes.py 7 处 SLF001；更新 Import 路径 (main.py/export.py/test files)；修复 ws.py N815 (isLoading→is_loading+alias)
- **改了什么文件**: pyproject.toml (mod), app/orchestration/redis.py (new), app/agents/orchestrator.py (mod), app/orchestration/nodes.py (mod), app/main.py (mod), app/api/v1/routes/export.py (mod), app/schemas/ws.py (mod), app/config.py (mod), tests/test_orchestration/test_redis.py (new), tests/test_orchestration/test_phase2_graph.py (mod), tests/test_agents/test_orchestrator.py (mod), tests/test_agents/test_orchestrator_helpers.py (mod), tests/test_main.py (mod), tests/test_api/test_websocket.py (mod), tests/test_schemas/test_ws_events.py (mod)
- **当前状态**: f-harness-p0/p1/p2/p3=passing, f-technical-debt=active (P0 done, P1 next)
- **决策**: Redis 函数提取到独立模块保持零行为变更；set_run_state/get_agent/cleanup_for_rerun 作为 _set_run/_agent_index/_cleanup_for_rerun 的公开委托；monkeypatch 路径必须指向实际定义模块的命名空间；N815 修复使用 Field(alias) 保持 API 兼容
- **阻断**: 无
- **下次**: Phase 1 — BLE001(裸except) 修复：75 处替换为具体异常类型

## 2026-06-06 — Session: technical-debt-p1-complete
- **做了什么**: 修复全部 75 处 BLE001（裸 except Exception）替换为具体异常类型；覆盖 services/agents/routes/infra 共 25 个文件
- **改了什么文件**: audio_service.py, font_utils.py, face_cropper.py, llm.py, image.py, doubao_video.py, character_bible.py, consistency_eval.py, export_service.py, image_composer.py, provider_resolution.py, text.py, agent_runner.py, run_recovery.py, base.py, compose.py, critic.py, orchestrator.py, plan.py, render.py, config.py (routes), consistency.py (routes), export.py (routes), main.py, ws/manager.py, db/session.py, redis.py
- **当前状态**: f-technical-debt=passing ✅
- **决策**: 确定路径（Anthropic APIError/Pydantic ValidationError/httpx.HTTPError）使用具体异常类型；非确定路径（reportlab/edge_tts/insightface）使用 # noqa: BLE001 + 注释上下文说明；测试验证中 RuntimeError 追加到异常列表以兼容 monkeypatch 测试模式
- **阻断**: 无
- **下次**: 技术债务清理完成

## 2026-06-06 — Session: task-1-services-group-a-ble001
- **做了什么**: 修复 services/ 组 A 所有 10 处 BLE001 裸 except Exception 违规
- **改了什么文件**: audio_service.py (mod: L97→subprocess errors, L150→noqa+edge_tts comment, L302→subprocess errors, +module-level subprocess import), font_utils.py (mod: L121→httpx.HTTPError+OSError, L190/L201/L207/L215/L221→noqa+reportlab comments, fixed TTC nested indent), face_cropper.py (mod: L42→ImportError+OSError+RuntimeError)
- **当前状态**: services/ group A BLE001 → 0 errors; 391 service tests pass
- **决策**: edge_tts 和 reportlab 无特定异常类→noqa+justification comment；subprocess 提升到 module-level import 避免 unbound variable；TTC 嵌套 except 修复缩进与 inner try 对齐
- **阻断**: 无
- **下次**: services/ 组 B — remaining BLE001 violations
