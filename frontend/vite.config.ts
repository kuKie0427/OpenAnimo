/// <reference types="vitest" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "url";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "~": fileURLToPath(new URL("./app", import.meta.url)),
    },
  },
  server: {
    port: 15173,
    strictPort: true,
  },
  preview: {
    port: 15173,
    strictPort: true,
    host: true,
  },
  build: {
    // 代码分割优化
    rollupOptions: {
      output: {
        manualChunks: {
          // 将 React 相关库打包到单独的 chunk
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          // 将状态管理库打包到单独的 chunk
          'state-vendor': ['zustand', '@tanstack/react-query'],
          // 将 tldraw 打包到单独的 chunk（较大的库）
          'tldraw-vendor': ['tldraw'],
        },
      },
    },
    // 启用 CSS 代码分割
    cssCodeSplit: true,
    // tldraw is intentionally isolated in its own vendor chunk; keep the warning
    // threshold above the current isolated payload so builds only warn on growth.
    chunkSizeWarningLimit: 1700,
    // 启用压缩
    minify: 'esbuild',
    // 启用源码映射（仅用于错误追踪）
    sourcemap: false,
  },
  // 优化依赖预构建
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'zustand',
      '@tanstack/react-query',
    ],
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./app/setupTests.ts",
    css: true,
    exclude: ["tests/e2e/**", "node_modules/**"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      reportsDirectory: "./coverage",
      include: ["app/**/*.{ts,tsx}"],
      exclude: [
        "app/main.tsx",
        "app/vite-env.d.ts",
        "app/types/index.ts",
        "app/mocks",
      ],
    },
  },
});
