# Product

## Register

product

## Users

独立漫画创作者、短剧编剧、内容创作者。他们坐在电脑前，从脑海中的一个故事画面出发，希望快速把创意变成可视化的漫剧分镜和视频。场景是专注的创作时段，不是碎片浏览。创作发生在深夜放映室里——暗色界面、琥珀暖光、胶片质感。

## Product Purpose

AI 漫剧生成平台：用户输入故事创意 → 6 个 AI Agent（Outline/Plan/Render/Critic/Compose/Review）协作生成角色、分镜、视频、配音 → 用户在无限画布上审阅、微调、导出成品。支持 17 阶段 LangGraph 编排、人机审批关卡、VLM 自动质量审查。

## Brand Personality

像深夜放映室：专业、沉浸、有仪式感。放映机投射的琥珀色光束是空间里唯一的暖光，其余一切消隐在暗影中。胶片颗粒纹理（film grain）、衬线标题字体（Playfair Display / Cormorant Garamond）、漫射辉光（glow）而非实体阴影——这是放映设备的语言，不是画材的语言。视觉服务于叙事，UI 是放映室的设备，内容才是银幕上的电影。

## Anti-references

- 企业 SaaS 灰色面板（Notion/Jira 式的冷淡无趣）
- 通用 AI 内容生成器（中间白卡片网格 + 紫色渐变）
- 儿童涂鸦风（过度圆角 + 糖果色 + 幼态排版）
- 漫画工作台风（CMYK 偏移阴影 + 粗边框 + halftone 点阵 + 手写字体 — 这是 OpenAnimo 的旧设计，已废弃）

## Design Principles

1. **Canvas-first**: 画布是工作台的核心，一切围绕视觉内容展开。面板是辅助，不占主导。
2. **Cinematic atmosphere, tool clarity**: 放映室氛围带来沉浸感，但交互逻辑必须清晰。装饰服务于识别（不同阶段用不同设备指示灯色：琥珀/红/蓝），不服务于装饰本身。
3. **Progressive disclosure**: 创作者只需看到当前步骤需要的信息。高级选项折叠，默认路径简洁。
4. **Instant feedback**: 生成进度、形状变化、状态切换必须有即时视觉反馈。放映室不该有沉默时刻。
5. **Respect the craft**: 漫剧是手艺活。工具不应降低输出的审美门槛，而应提升创作者的控制精度。

## Accessibility & Inclusion

- WCAG 2.1 AA 对比度
- 暗色模式下氛围元素可见度不低于合理阈值（胶片颗粒纹理不透明度 ≥3%，message-ai 左侧琥珀边框不透明度 ≥12%）
- 减少动效偏好尊重 `prefers-reduced-motion`
- 辉光是层次信号，不是纯装饰——移除辉光会改变元素的视觉层级
