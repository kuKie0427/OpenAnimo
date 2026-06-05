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
│   │   └── fonts.css           # 字体加载（Fredoka/Nunito/Caveat/Bangers）
│   └── features/               # Feature-sliced 模式
├── tests/e2e/                  # Playwright E2E 测试
├── vite.config.ts              # Vite 构建 + Vitest 测试配置
├── tailwind.config.ts          # Tailwind + daisyUI（漫画双主题）
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
| 了解设计规范 | `../DESIGN.md` | CMYK 漫画风主题，15 条 Don't |
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

### 代码规范
- **组件命名**: PascalCase（`HomePage`、`ProjectPage`、`SettingsModal`）
- **文件命名**: 组件用 PascalCase 文件（`Button.tsx`），工具/hook/store 用 camelCase（`toast.ts`、`useWebSocket.ts`）
- **路径别名**: `~/` → `./app/`（非标准 `@/`）
- **类型**: TypeScript 严格模式，`app/types/index.ts` 集中定义
- **样式**: Tailwind CSS `class="..."`，无 CSS Modules / styled-components
- **无 ESLint/Prettier** — 仅靠 `tsc` 保证类型正确
- **缩进**: Tab（从 main.tsx 确认）

### 组件模式
- **页面组件**: 位于 `app/pages/`，命名 `*Page.tsx`，默认导出
- **UI 组件**: 位于 `app/components/`，按功能分子目录（canvas/chat/layout/panels/settings/ui）
- **组件测试**: 与源文件同目录，后缀 `.test.tsx`
- **懒加载**: 路由页面使用 `React.lazy()` + `Suspense`

### 状态管理模式
- **全局状态**: Zustand 5（`app/stores/`），每个 store 一个文件
- **服务器状态**: `@tanstack/react-query`（缓存/重取/乐观更新）
- **测试**: 直接调用 `useEditorStore.getState().reset()` 无需渲染组件
- **Store 命名**: camelCase 文件名（例外：`toast.store.ts` 用点分隔）

### 样式规范（来自 DESIGN.md）
- 禁止纯 `#000` / `#fff` — 所有中性色需偏暖色调
- 禁止渐变文字（`background-clip: text`）
- 禁止毛玻璃作为默认表面
- 禁止 >1px 的彩色装饰线
- 禁止在 UI 标签/按钮中使用 Bangers 显示字体
- 主题: daisyUI `doodle`（日间）/ `doodle-dark`（夜间）

### 测试模式
- **单测框架**: Vitest（globals: true，jsdom 环境）
- **Mock 策略**: `vi.fn()` / `vi.mock()` / `vi.stubGlobal()` 为主，MSW 备选
- **WebSocket 测试**: 自定义 `MockWebSocket` 类模拟连接
- **API 测试**: `vi.stubGlobal("fetch", mockFetch)` + 动态 `import()` 确保 mock 生效
- **E2E**: Playwright，Chromium 单浏览器，CI 重试 2 次
- **测试文件**: 与源文件同目录，E2E 在 `tests/e2e/`

### 配置/环境变量
- `VITE_API_URL` — 后端 HTTP 地址（默认自动推导，**通常不需要手动设置**）
- `VITE_WS_URL` — 后端 WS 地址（同上）
- `VITE_ENABLE_MSW` — 是否启用 Mock Service Worker（默认关闭）
- 自动推导逻辑在 `app/utils/runtimeBase.ts`，开发环境下自动用 hostname + `:18765`

---

## 前端反模式（禁止）

1. **不要**在组件中直接调用 API — 使用 `services/api.ts` 封装的函数
2. **不要**使用 `any` 类型 — `frontend/app/types/errors.ts` 和 tldraw shapes 中多处 `T.any` 需逐步替换为具体类型
3. **不要**在 `app.config.ts` 中修改配置 — 此文件是 TanStack Start 残留，实际构建走 `vite.config.ts`
4. **不要**在生产代码留 `console.log/debug/error` — WebSocket hook 中 5 处 console 需清理
5. **不要**忽视 Zustand store 的 `reset()` — 测试和组件卸载时确保调用
6. **不要**绕过类型检查 — 测试中的 `as any` 应在重构时消除
7. **不要**忘记 `pnpm build` 已包含 `tsc` — 无需单独运行类型检查

---

## 已知问题

- `app.config.ts` — TanStack Start 残留配置，未使用，建议删除
- `SettingsModal.tsx` 1113 行 — 全能弹窗，建议拆为 ProviderConfigPanel、ConnectionTester 等子组件
- `types/index.ts` 740 行 — 71 个导出类型，建议按领域拆分为 `project.ts`、`character.ts`、`shot.ts`、`event.ts`
- `useWebSocket.ts` 698 行 — 15+ 事件路由，可考虑策略模式
- `api.ts` 632 行 — 可按 domain 拆为 `projectsApi.ts`、`generationApi.ts` 等
- 生产代码中多处 `console.debug/error` — 应改为可配置的日志级别
- tldraw shapes 中多处 `T.any` — 类型安全待改善
