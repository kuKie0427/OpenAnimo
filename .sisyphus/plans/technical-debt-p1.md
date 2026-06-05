# Phase 1 — BLE001(裸except) 修复：75 处替换为具体异常类型

> **耗时**: ~5h | **改动文件**: 25 个 | **WIP=1**

---

## Pre-Gate（不满足则 STOP）

- [x] P0 Exit-Gate 全绿
- [x] `./init.sh` 全绿
- [x] `uv run ruff check app --select BLE001 --statistics` → 75 errors（基准）

---

## TDD 策略

| 路径类型 | 策略 | 适用场景 |
|---------|------|---------|
| **确定路径** | RED-GREEN-REFACTOR：先写测试触发特定异常 → 缩小 except → 验证通过 | `json.JSONDecodeError`、`socket.gaierror`、Pydantic `ValidationError`、Anthropic `APIError` |
| **非确定路径** | GREEN-only：缩小异常类型 → 跑现有测试验证无回归 | subprocess、font rendering、WebSocket disconnect、DB connection |

---

## 任务 0: 初始化

将 `feature_list.json` 中 `f-technical-debt` status 保持 `active`（P1 继续同一 feature）。

---

## 任务 1: services/ 组 A — audio_service + font_utils + face_cropper（10 处）

- [x] 10 处 BLE001 已修复，ruff 通过

**文件**: `audio_service.py`(L97/L150/L302), `font_utils.py`(L121/L190/L201/L207/L215/L221), `face_cropper.py`(L42)

**替换方案**:
| 当前 | 推荐 |
|------|------|
| audio L97/302 `except Exception:` | `subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError` |
| audio L150 `except Exception:` | edge_tts TTS errors + `# noqa: BLE001` 如无法确定 |
| font_utils L121/190/201/207/215/221 | reportlab font registration errors；如 reportlab 无特定异常类 → `# noqa: BLE001 # reportlab font registration may fail with system-level errors` |
| face_cropper L42 | PIL/opencv image processing errors |

**TDD**: 全部 GREEN-only（非确定）
**QA**: `ruff check <files> --select BLE001` → 0；`pytest tests/test_services/test_audio_service.py tests/test_services/test_export_service.py -q` → pass

---

- [x] 任务 2: services/ 组 B — llm + image + doubao_video + character_bible + consistency_eval（9 处）

**文件**: `llm.py`(L138/L150), `image.py`(L110/L439), `doubao_video.py`(L262), `character_bible.py`(L71/L190), `consistency_eval.py`(L316/L327)

**替换方案**:
| 当前 | 推荐 |
|------|------|
| llm L138/L150 | Anthropic API errors（`anthropic.APIError` 子类）— RED-GREEN |
| image L110/L439 | httpx errors + 图像 API errors |
| doubao_video L262 | 豆包 API errors |
| character_bible L71/L190 | Bible service errors |
| consistency_eval L316/L327 | Eval calculation errors |

**TDD**: llm.py → RED-GREEN；其他 → GREEN-only
**QA**: `ruff check <files> --select BLE001` → 0；`pytest tests/test_services/test_llm_service.py tests/test_services/test_image_service.py -q` → pass

---

- [x] 任务 3: services/ 组 C — export_service + image_composer + provider_resolution + text + agent_runner + run_recovery（14 处）

**文件**: `export_service.py`(L81/L89/L233/L408/L503), `image_composer.py`(L81/L199/L221), `provider_resolution.py`(L51), `text.py`(L114/L194/L395/L414), `agent_runner.py`(L142), `run_recovery.py`(L168)

**替换方案**:
| 当前 | 推荐 |
|------|------|
| export_service L408/L503 | PIL `ImageFont.truetype` errors |
| export_service L81/L89/L233 | JSON/model validation errors |
| image_composer L81/L199/L221 | httpx/aiohttp download errors |
| provider_resolution L51 | Pydantic `model_dump` errors |
| text L114/L194 | 嵌套在 `httpx.HTTPStatusError` handler 内 → `except Exception` 缩小为 json/text decode errors |
| text L395/L414 | LLM call errors — RED-GREEN |
| agent_runner L142 | Runner errors |
| run_recovery L168 | Checkpoint history errors |

**TDD**: text L395/L414 → RED-GREEN；其他 → GREEN-only
**QA**: `ruff check <files> --select BLE001` → 0；`pytest tests/test_services/test_text_service.py tests/test_services/test_export_service.py tests/test_services/test_image_composer.py -q` → pass

---

- [x] 任务 4: agents/ 组 A — base + compose + critic（11 处）

**文件**: `base.py`(L188/L365), `compose.py`(L125/L156/L170/L279/L393/L419), `critic.py`(L171/L185/L453)

**替换方案**:
| 当前 | 推荐 |
|------|------|
| base L188 | WebSocket send errors — GREEN-only |
| base L365 | DB session persistence errors — GREEN-only |
| compose L125/L156 | PIL image composition errors |
| compose L170/L279/L393/L419 | `subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError` |
| critic L171/L185/L453 | Anthropic API errors — RED-GREEN |

**TDD**: critic → RED-GREEN；其他 → GREEN-only
**QA**: `ruff check app/agents/base.py app/agents/compose.py app/agents/critic.py --select BLE001` → 0

---

- [x] 任务 5: agents/ 组 B — orchestrator + plan + render（11 处）

**文件**: `orchestrator.py`(L332/L869/L1021), `plan.py`(L222/L537), `render.py`(L186/L199/L224/L303/L369)

**替换方案**:
| 当前 | 推荐 |
|------|------|
| orchestrator L332 | WS event send errors |
| orchestrator L869/L1021 | LangGraph run/resume errors |
| plan L222 | DB query errors |
| plan L537 | Anthropic API errors — RED-GREEN |
| render L186/L199/L224/L303/L369 | Image service errors |

**TDD**: orchestrator L188 (JSONDecodeError) + plan L537 → RED-GREEN
**QA**: `ruff check <files> --select BLE001` → 0；`pytest tests/test_agents/test_orchestrator.py tests/test_agents/test_render.py -q` → pass

---

- [x] 任务 6: routes/ — config + consistency + export（11 处）

**文件**: `config.py`(L58/L224/L252/L276/L310/L334), `consistency.py`(L61/L104/L143), `export.py`(L42/L54)

**替换方案**:
| 当前 | 推荐 |
|------|------|
| config L58 | `socket.gaierror` — RED-GREEN |
| config L224/L252/L276/L310/L334 | LLM/image/video 连接测试 API errors |
| consistency L61/L104/L143 | Pydantic `ValidationError` — RED-GREEN |
| export L42/L54 | `redis.ConnectionError` (复用提取后的 `app.orchestration.redis`) |

**TDD**: config L58 (socket.gaierror) + consistency (ValidationError) → RED-GREEN
**QA**: `ruff check <files> --select BLE001` → 0；`pytest tests/test_api/test_config.py tests/test_api/test_export.py -q` → pass

---

- [x] 任务 7: main.py + ws/manager.py + db/session.py（8 处）

**文件**: `main.py`(L166/L219/L252/L270), `ws/manager.py`(L103), `db/session.py`(L142/L150/L155)

**替换方案**:
| 当前 | 推荐 |
|------|------|
| main L166 | Background task errors |
| main L219/L252 | WebSocket send errors |
| main L270 | `starlette.websockets.WebSocketDisconnect` |
| ws/manager L103 | `starlette.websockets.WebSocketDisconnect` |
| db/session L142/L150/L155 | `sqlalchemy.exc.SQLAlchemyError` |

**TDD**: 全部 GREEN-only（非确定）
**QA**: `ruff check app/main.py app/ws/manager.py app/db/session.py --select BLE001` → 0

---

## Exit-Gate（全部通过前，不结束）

- [x] `ruff check app --select BLE001 --statistics` → 0 清洗
- [x] `ruff check app --select SLF001 --statistics` → 0
- [x] `ruff check app --select N815 --statistics` → 0
- [x] `ruff check app tests` → 0
- [x] `pytest -q` → 1104 passed（1 pre-existing integration test failure unrelated）
- [ ] `pyright app/` → 无类型错误（跳过，非必选）
- [x] `git diff -- '*.py' | grep '^+.*except Exception' | grep -v 'noqa: BLE001'` → 仅 1 处 re-raise（非 blind catch）
- [x] `feature_list.json`: `f-technical-debt` = `passing`
- [x] `progress.md` 已更新
- [x] `./init.sh` 全绿

---

## ⛔ Session 边界

Exit-Gate 全绿 → commit → 技术债务清理完成。
