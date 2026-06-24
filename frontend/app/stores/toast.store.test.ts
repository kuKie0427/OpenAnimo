import { describe, it, expect, beforeEach } from "vitest";
import { useToastStore } from "./toast.store";

describe("toast.store", () => {
  beforeEach(() => {
    useToastStore.getState().clearToasts();
  });

  it("starts with empty toasts", () => {
    expect(useToastStore.getState().toasts).toEqual([]);
  });

  it("adds a toast with generated id", () => {
    useToastStore.getState().addToast({
      type: "success",
      title: "ok",
      message: "done",
      duration: 3000,
    });
    expect(useToastStore.getState().toasts).toHaveLength(1);
    expect(useToastStore.getState().toasts[0].title).toBe("ok");
  });

  it("removes a toast by id", () => {
    useToastStore.getState().addToast({
      type: "error",
      title: "err",
      message: "fail",
      duration: 0,
    });
    const id = useToastStore.getState().toasts[0].id;
    useToastStore.getState().removeToast(id);
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("clears all toasts", () => {
    useToastStore.getState().addToast({ type: "info", title: "a", message: "b", duration: 0 });
    useToastStore.getState().addToast({ type: "info", title: "c", message: "d", duration: 0 });
    useToastStore.getState().clearToasts();
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("caps at MAX_TOASTS (5)", () => {
    for (let i = 0; i < 7; i++) {
      useToastStore.getState().addToast({
        type: "info",
        title: `t${i}`,
        message: "m",
        duration: 0,
      });
    }
    expect(useToastStore.getState().toasts).toHaveLength(5);
    expect(useToastStore.getState().toasts[0].title).toBe("t2");
  });
});
