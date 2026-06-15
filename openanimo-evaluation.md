# OpenAnimo 评估 — AI 漫剧生成师视角

**评估时间**: 2026-06-15
**评估视角**: AI 漫剧生成师（独立漫剧创作者 / 短剧编剧 / 内容创作者）
**评估对象**: `/Users/lanf/pra/die/donghua/openOii`（OpenAnimo v0.x）
**评估基线**: `feature_list.json`（45 features, 45 passing）+ `progress.md`（最近会话 2026-06-08）+ `backend/app/orchestration/` 编排源码 + `DESIGN.md` 设计规范

---

## 0. 总体判断

**会用，但分场景**。

| 用途 | 是否使用 | 信心 |
|---|---|---|
| 漫剧前期（大纲 / 角色 / 分镜） | **会用** | 高 |
| 静态/半动态漫剧（动态漫） | **会用** | 中高 |
| 商业级 1-3 分钟短视频 | **会用** | 中 |
| 长篇带配音的漫剧成片 | **不会用** | — |
| 商业播出的高完成度作品 | **不会用** | — |

OpenAnimo 是一个**认真做了"AI 漫剧生成"这件事的骨架型项目**。它的 17 阶段编排、角色圣经、Critic 回环、Per-gate 控制，都是"对的路"。但**"成片"那一步还差关键工程化能力**（字幕、竖屏导出、多轨配音、镜头语言控制），导致它目前最适合做**漫剧前 70% 的工作**（大纲→分镜→动态漫），最后 30% 的"商业成片"得切到 Premiere / 剪映 / 专业 TTS。

---

## 1. 会用的理由

### 1.1 17 阶段流水线是行业级骨架

打开 `backend/app/orchestration/graph.py` 看到的是：

```
plan_outline → outline_approval
  → plan_characters → characters_approval
  → plan_shots → shots_approval
  → render_characters → character_images_approval → critique_character_images
  → render_shots → shot_images_approval → critique_shot_images
  → compose_videos → compose_merge
  → add_audio → compose_approval
```

8 个生产节点 + 6 个人机审批关卡 + 2 个 VLM Critic 节点 + 1 个 Review 节点。这正是漫剧导演想控制的工作流：每一道闸门都可以拍板、改剧本、回炉。

特别看重的三点：

- **VLM Critic 反馈注入重生**（`f-critic-feedback-injection`）—— Critic 评完分后把评语打回 Render 的 prompt 里重生。直接解决"分镜崩坏"问题。
- **节拍分析器**（`beat_analyzer.py`）—— 把情绪曲线注入到分镜的 `duration / camera / lighting`。少数会做"节奏"的 AI 工具。
- **维度级质量阈值**（`f-critic-threshold`：consistency≥4 + quality≥4 + composition≥4 + 加权≥6.0）—— 避免单一维度崩坏被总分掩盖。

### 1.2 角色一致性是漫剧的命门，它正面回答了

- `character_bible.py`：`description + visual_notes` 自动生成 + 合并为"角色圣经"
- InsightFace 提取 512 维人脸 embedding + 余弦相似度查重
- `consistency_eval.py` 评估每张分镜与角色参考的相似度

属于**严肃对待"角色一致性"**的几个 AI 漫剧工具之一。方向是对的。

### 1.3 控制权给得恰到好处

- **Per-gate YOLO 模式**（`f-yolo-per-gate`）—— 可以选"大纲自动通过 + 分镜必须人工"，省时间但不丢关键控制点
- **实体级审批**（`f-entity-approval`）—— 20 个分镜中只重做第 7 个，不是整批推翻
- **A/B 对比内嵌**（`f-ab-compare-approval`）—— 审批时直接看新旧版本对比
- **Seed 管理**（`f-seed-management`）—— 锁定 seed 微调工作流可复现
- **版本回滚**（`f-version-compare`）—— ArtifactVersion 追溯

### 1.4 编辑器审美对路

DESIGN.md 里的"投影放映室"（Projection Room）氛围——深色底、琥珀单暖光、衬线标题、胶片颗粒——这正是"在深夜专注创作"的创作者想要的。它明确拒绝了三类反美学：

- Notion 风灰色面板
- Midjourney 紫色渐变
- 儿童涂鸦风（圆角 + 糖果色）

这种"知道不要什么"的设计判断力比"做了 200 个组件"更难得。

### 1.5 可拔插的 Provider 设计

| 能力 | Provider 选项 |
|---|---|
| LLM | openai-compatible（中转站可用）/ fake |
| 图像 | openai-compatible / fake |
| 视频 | openai-compatible / **doubao（豆包 Seedance-1-5-Pro）** / fake |
| 音频 | Edge TTS（免费） |
| 人脸 | InsightFace（本地） |

可以接自己的中转、自带 key、或本地 fake 跑测试，灵活度够用。`backend/.env.example` 注释清楚（"方式一 直连 Anthropic / 方式二 中转站"）。

### 1.6 可观测性是真的，不是装饰

- `AgentTrace` 记录每个 Agent 的输入输出（`f-harness-p1`）
- `RunMetrics` 仪表板 API（`f-harness-p3`，3 个 endpoint）
- WebSocket Schema 强约束（`f-harness-p2`）
- Prompt VERSION + CHANGELOG（解决"哪个版本效果最好"的归档噩梦）
- 阶段级完整性断言（`f-stage-completeness`）—— 防止部分产物悄悄缺失

对一个要跑几十个分镜的漫剧项目，能回溯"这一帧是哪次 Critic 评分低 + 哪个 prompt 版本生成"，省下的是无法估量的时间。

### 1.7 README 的诚实让我信任它的边界

README 明确写：

> **不适合直接用于工业生产环境**

这种"项目自认知"反而让我信任——知道它能做什么不能做什么，比"号称能搞定一切"的项目更可靠。

---

## 2. 不会用于商业级漫剧成片的原因

**核心问题：它擅长"生成分镜"，但还远没到"成片"。**

### 2.1 视频是最大短板

`compose_videos` 节点把分镜图转成视频段，然后 `video_merger` 拼接。本质是"动起来的分镜"，不是漫剧。商业漫剧需要：

- 镜头内**真实运动**（人物走动、表情变化、物体动态）—— 依赖第三方视频模型上限
- **镜头间转场**（淡入淡出、跳切、闪白、动作匹配剪辑）—— 当前没看到可配置的转场库
- **节奏可控的剪辑**—— 创作者无法在时间线上精调每个 cut 的时长

如果客户要"动态漫 / 漫剪视频"勉强可用；要"有戏剧张力的漫剧成片"得另开 Premiere / 剪映。

### 2.2 配音是 Edge TTS，能用但不够

`audio_service.py` 用 Edge TTS 免费接口，6 个 BGM 情绪分类（suspense / warm / action / sad / happy / ambient），FFmpeg 混音。问题：

- **多角色对话**的语音分配、情绪/语速/停顿精细控制？—— 没看到
- **旁白 vs 对白**的分轨混音？—— 没看到
- **真实授权 BGM 库**？—— 默认生成 15 秒静音占位 mp3（`_generate_silence_placeholder`），需要自行准备
- **音效**（脚步声、风声、门响）？—— 没有
- **TTS 情感 / 韵律**？—— Edge TTS 的弱项直接继承

作为配音导演会感觉被冷落。

### 2.3 字幕烧入 —— 漫剧分发命门 —— 缺席

对抖音 / 快手 / B站 / YouTube / TikTok 分发来说，**字幕烧入**是必选项。当前只有 PDF / Webtoon 导出（`f-export`），没有 SRT/ASS 字幕生成 + 烧入视频管线。这直接堵死短视频分发。

### 2.4 没有"时间线编辑器"

打开项目看到的是 tldraw 无限画布——很美，但它是"分镜工作台"而不是"剪辑时间线"。缺：

- 视频轨 / 音频轨 / 字幕轨的多轨编辑
- 拖拽调整镜头时长
- 关键帧级别的精修
- 速度曲线（speed ramp）

**导演要做"最后一公里的成片"，必须切到外部工具**。

### 2.5 单 Worker 限制（README 已自我承认）

`task_manager` 是进程内字典，强制 `WEB_CONCURRENCY=1`。一个 20 分镜 + 5 角色 + Critic 多轮 ≈ 30+ LLM 调用串行。session `2026-06-08` 还移除了 parallel 模式（`f-remove-parallel-mode`），因为"并行模式下分镜渲染会降级为纯文本生成，角色一致性无法保证"。但代价是速度。

### 2.6 API 成本不可见

没有任何面板显示"这个 run 花了多少钱"。商业项目负责人必须有"报价 vs 成本"依据，这是不可接受的盲区。`RunMetrics` 测的是运行时间和事件数，不是钱。

### 2.7 角色"多表情/多角度"库缺位

当前每个角色主要是一张主参考图（Character Bible）。但漫剧里同一角色需要：

- 正面 / 侧面 / 背面
- 微笑 / 愤怒 / 哭泣 / 惊讶
- 战斗服 / 日常服 / 礼服

这些系统化的"角色资产"目前缺位。靠 prompt 描述"角色 A 现在很愤怒"出不来稳定结果。

### 2.8 跨项目"IP 宇宙"刚起步

`f-universe-multi-project` 实现了"跨项目共享角色"，但深度有限：只是"导入已有角色"，没有"角色 + 场景 + 风格 + 资产"一体的 IP 资产库。出系列漫剧时复用成本高。

---

## 3. 改进建议（按优先级）

### 🔴 P0 — 决定能否从"演示"跨越到"可用"

| # | 改进 | 理由 |
|---|---|---|
| 1 | **内置字幕烧入**（中文为主，SRT/ASS → 视频硬字幕） | 没这个就上不了抖音/B站/YouTube；漫剧发行的命门 |
| 2 | **竖屏 9:16 短视频导出**（不仅是 PDF/Webtoon） | 当前所有导出偏横屏阅读，主流漫剧消费是手机竖屏 |
| 3 | **API 成本与 token 仪表板** | 商业项目必须的"报价 vs 成本"依据 |
| 4 | **多表情/多角度角色库**（每个角色 ≥ 4 视角 × 4 情绪 = 16 张） | 当前单图驱动多场景，漫剧角色崩坏的根本原因 |
| 5 | **多角色对话配音与混音**（对白轨 / 旁白轨 / 音效轨分轨） | 配音导演需要分轨精修，不能一锅烩 |

### 🟡 P1 — 决定"漫剧"专业度

| # | 改进 | 理由 |
|---|---|---|
| 6 | **剧本编辑器**（与分镜双向同步） | 当前剧本/分镜割裂；编剧要能在脚本里改一行，下游分镜自动重排 |
| 7 | **BGM 智能匹配升级**—— 接入商用 BGM 库（Epidemic Sound / Artlist / 国产商用库）或 AI 生成式 BGM（Udio/Suno API） | 当前静音占位 + 6 关键词，无法商用 |
| 8 | **专业镜头语言控制**—— 推/拉/摇/移/固定 + 特写/中景/远景 + 视角（主观/客观/过肩）术语原生支持 | 让导演用行话下指令，而不是 prompt 玄学 |
| 9 | **批量化重生成 + 区域重绘**—— 选中低分镜头，支持"只重画这一格"或"批量重渲" | 当前要么整批重做要么单点重做，效率不够 |
| 10 | **真实授权 BGM / SFX 库**或用户上传 BGM 库 | 漫剧必须解决音乐版权问题 |
| 11 | **参考图机制**—— 用户上传参考图，影响后续分镜渲染（IP 锁定） | 商业项目常需要"风格必须像这张图" |

### 🟢 P2 — 决定差异化竞争力

| # | 改进 | 理由 |
|---|---|---|
| 12 | **漫剧分镜模板**—— 日漫 / 国漫 / 韩漫 / 欧美漫画 行业模板 | 一键启用符合行业规范的分镜规范 |
| 13 | **协作模式**—— 多创作者 / 批注 / 版本合并 | 商业项目都是团队作战 |
| 14 | **长文本 → 漫剧**（小说/剧本导入，自动提取角色/情节/分镜） | 让作者从已有 IP 直接生产 |
| 15 | **资产市场**—— 共享/交易风格、角色、场景模板 | 网络效应 |
| 16 | **导演视角的"时间线审片"**—— 不只是 tldraw 画布，要有多轨时间线 | 替代部分 Premiere/剪映工作 |
| 17 | **多语言剧情支持**（不只是中英，含日韩） | 出海/多语种配音 |

### ⚪ P3 — 锦上添花

- 国际化（界面多语言）
- 离线模式（本地 LLM 替代 API）
- 工作流市场（用户自创 Pipeline）
- 角色对话历史（同一个角色前后对话的连续性）

---

## 4. 现状一图概览

```
                    ┌──────────────────────────────────┐
                    │  OpenAnimo 当前能力覆盖图        │
                    └──────────────────────────────────┘
                    
 前期 (90%)    ████████████████████░  大纲/角色/分镜规划
 角色设计 (75%) ███████████████░░░░░░  Character Bible + 渲染
 分镜图像 (70%) ██████████████░░░░░░░  Render + Critic 回环
 视频动效 (40%) ████████░░░░░░░░░░░░░  compose_videos（依赖第三方）
 配音 (35%)    ███████░░░░░░░░░░░░░░  Edge TTS + BGM 关键词
 字幕 (0%)     ░░░░░░░░░░░░░░░░░░░░░  缺失
 竖屏导出 (0%) ░░░░░░░░░░░░░░░░░░░░░  缺失（仅 PDF/Webtoon）
 时间线剪辑 (10%) ██░░░░░░░░░░░░░░░░░░  仅 tldraw 画布
 成本可见 (0%) ░░░░░░░░░░░░░░░░░░░░░  RunMetrics 不计费
                 └──────────────────────────
                 0%        50%       100%
```

---

## 5. 关键文件索引

| 关注点 | 位置 |
|---|---|
| 17 阶段流水线 | `backend/app/orchestration/graph.py` |
| 流水线状态 | `backend/app/orchestration/state.py` |
| 总调度器 | `backend/app/agents/orchestrator.py` (1035 行) |
| 角色圣经 | `backend/app/services/character_bible.py` |
| 人脸嵌入 | `backend/app/services/face_cropper.py` |
| 一致性评估 | `backend/app/services/consistency_eval.py` |
| 音频服务 | `backend/app/services/audio_service.py` |
| 节拍分析 | `backend/app/services/beat_analyzer.py` |
| Critic 阈值 | `backend/app/agents/critic.py`（`f-critic-threshold`） |
| 视频合并 | `backend/app/services/video_merger.py` |
| 导出 | `backend/app/services/export_service.py` |
| Provider 配置 | `backend/app/config.py` |
| 设计规范 | `DESIGN.md`（Projection Room） |
| 编排专题 | `.trellis/spec/guides/orchestration-architecture.md` |

---

## 6. 一句话总结

> 如果 OpenAnimo 把 P0 那 5 项做掉，**我会把它推荐给所有做动态漫的同行**。
> 如果 P0 + P1 都做了，它就有可能成为"AI 漫剧生产的中台"——这是我现在希望看到的终局。

---

**附：与 README 自认知的对照**

README 写："这是一个 LangGraph 学习/演示项目，**不适合直接用于工业生产环境**"。

我的评估与此一致：**作为"演示/学习项目"它超额完成；作为"工业生产环境"它目前差 P0 的 5 项工程化能力**。这两件事并不矛盾——它正处在从"学习项目"向"生产项目"过渡的拐点，差距清晰可量化。
