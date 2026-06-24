# frontend — React/Vite 前端开发指南

**父级**: `../AGENTS.md`

---

## 概览

React 18 + TypeScript + Vite 6 前端 SPA，集成 tldraw 画布、WebSocket 实时推送、Zustand 状态管理。使用 `pnpm` 作为包管理器。

---

## 目录结构

```
frontend/
├── app/
│   ├── main.tsx                # React 入口（MSW 条件启用 + createRoot）
│   ├── App.tsx                 # 路由定义（react-router-dom 7，7 条懒加载路由）
│   ├── pages/                  # 页面组件（HomePage/ProjectsPage/ProjectPage/...）
│   ├── components/
│   │   ├── canvas/             # tldraw 画布（InfiniteCanvas + shapes/）
│   │   ├── chat/               # 聊天面板
│   │   ├── layout/             # 布局组件
│   │   ├── panels/             # 侧边面板
│   │   ├── settings/           # 设置弹窗（SettingsModal 1113 行，需关注）
│   │   ├── pipeline/           # 生成管道可视化
│   │   ├── project/            # 项目相关组件
│   │   └── ui/                 # 通用 UI（Button/Modal/Toast/...）
│   ├── stores/                 # Zustand 状态管理
│   │   ├── editorStore.ts     # 编辑器状态（核心）
│   │   ├── settingsStore.ts   # 配置状态
│   │   ├── themeStore.ts      # 主题状态
│   │   └── toast.store.ts     # Toast 通知
│   ├── hooks/                  # 自定义 Hook
│   │   ├── useWebSocket.ts     # WebSocket 连接 + 事件路由（698 行）
│   │   ├── useCanvasLayout.ts  # 画布布局
│   │   └── useDomSize.ts       # DOM 尺寸监听
│   ├── services/api.ts         # API 请求封装（632 行，全量 API）
│   ├── types/index.ts          # TypeScript 类型定义（740 行，71 个导出）
│   ├── utils/                  # 工具函数
│   │   └── runtimeBase.ts     # 后端地址自动推导（关键！）
│   ├── mocks/                  # MSW Mock
│   │   ├── server.ts           # Node 环境 server
│   │   ├── browser.ts          # 浏览器 worker
│   │   └── handlers.ts         # 请求处理器
│   ├── styles/                 # 全局 CSS
│   │   ├── tokens.css          # 设计令牌
│   │   ├── globals.css         # 全局样式
│   │   └── fonts.css           # 字体加载（Playfair Display/Cormorant Garamond/Source Sans 3/JetBrains Mono）
│   └── features/               # Feature-sliced 模式
├── tests/e2e/                  # Playwright E2E 测试
├── vite.config.ts              # Vite 构建 + Vitest 测试配置
├── tailwind.config.ts          # Tailwind + daisyUI（projection/rushes 双主题）
├── playwright.config.ts        # Playwright E2E 配置
├── app.config.ts               # ⚠️ TanStack Start 残留配置（未使用，可删除）
├── package.json                # 依赖 + 脚本
└── pnpm-lock.yaml              # 依赖锁定
```

---

## 快速查找

| 任务 | 位置 | 备注 |
|------|------|------|
| 了解前端路由 | `app/App.tsx` | 7 条 react-router 懒加载路由 |
| 了解画布组件 | `app/components/canvas/InfiniteCanvas.tsx` | tldraw 集成 |
| 了解 WebSocket 事件流 | `app/hooks/useWebSocket.ts` | 15+ 事件类型的路由分发 |
| 了解 API 调用 | `app/services/api.ts` | 集中式 API 封装 |
| 了解状态管理 | `app/stores/editorStore.ts` | 编辑器核心状态 |
| 了解后端地址推导 | `app/utils/runtimeBase.ts` | 开发环境自动推导 localhost:18765 |
| 了解类型定义 | `app/types/index.ts` | 71 个导出类型（project/character/shot/event） |
| 了解设计规范 | `../DESIGN.md` | Projection Room 主题，15 条 Do/Don't |
| 了解测试 | `app/` 下各 `*.test.tsx` + `tests/e2e/` | 单测同目录，E2E 独立 |

---

## 开发命令

```bash
# 安装依赖
cd frontend && pnpm install

# 启动开发服务器（端口 15173）
pnpm dev

# 构建（类型检查 + 构建）
pnpm build

# 预览生产构建
pnpm preview

# 运行单测
pnpm test                    # vitest（watch 模式）
pnpm test --run              # 单次运行
pnpm exec vitest run app/pages/ProjectPage.test.tsx  # 单文件

# 运行 E2E
pnpm e2e                     # Playwright（自动起 dev server）
pnpm e2e:install             # 安装 Playwright 浏览器

# 类型检查
pnpm exec tsc --noEmit
```

---

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

## 前端反模式（禁止）

详见 [quality-guidelines](.trellis/spec/frontend/quality-guidelines.md) 的反模式章节。

速记：禁止直接调 API（用 services/api.ts）· 禁止 any（逐步清理）· 禁止 app.config.ts · 禁止生产 console · 禁止忘 reset()

---

## 已知问题

- `app.config.ts` — TanStack Start 残留配置，未使用，建议删除
- `SettingsModal.tsx` 1113 行 — 全能弹窗，建议拆为 ProviderConfigPanel、ConnectionTester 等子组件
- `types/index.ts` 740 行 — 71 个导出类型，建议按领域拆分为 `project.ts`、`character.ts`、`shot.ts`、`event.ts`
- `useWebSocket.ts` 698 行 — 15+ 事件路由，可考虑策略模式
- `api.ts` 632 行 — 可按 domain 拆为 `projectsApi.ts`、`generationApi.ts` 等
- 生产代码中多处 `console.debug/error` — 应改为可配置的日志级别
- tldraw shapes 中多处 `T.any` — 类型安全待改善
