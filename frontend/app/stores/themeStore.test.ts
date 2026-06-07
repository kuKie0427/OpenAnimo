import { describe, it, expect, vi } from "vitest";

vi.mock("zustand/middleware", () => ({
  persist: (fn: any) => fn,
}));

// Import after mock so persist is a no-op (no localStorage needed)
const { useThemeStore } = await import("./themeStore");

describe("themeStore", () => {
  it("defaults to projection theme", () => {
    expect(useThemeStore.getState().theme).toBe("projection");
  });

  it("toggleTheme switches to rushes", () => {
    useThemeStore.getState().setTheme("projection");
    useThemeStore.getState().toggleTheme();
    expect(useThemeStore.getState().theme).toBe("rushes");
    expect(document.documentElement.getAttribute("data-theme")).toBe("rushes");
  });

  it("toggleTheme toggles back to projection", () => {
    useThemeStore.getState().setTheme("rushes");
    useThemeStore.getState().toggleTheme();
    expect(useThemeStore.getState().theme).toBe("projection");
    expect(document.documentElement.getAttribute("data-theme")).toBe("projection");
  });

  it("setTheme sets specific theme", () => {
    useThemeStore.getState().setTheme("rushes");
    expect(useThemeStore.getState().theme).toBe("rushes");
    expect(document.documentElement.getAttribute("data-theme")).toBe("rushes");
  });
});
