import { describe, it, expect, vi, beforeEach } from "vitest";

const mockAddToast = vi.fn();

vi.mock("~/stores/toast.store", () => ({
  useToastStore: { getState: () => ({ addToast: mockAddToast }) },
}));

let toast: typeof import("./toast").toast;

beforeEach(async () => {
  mockAddToast.mockClear();
  vi.resetModules();
  toast = (await import("./toast")).toast;
});

describe("toast utils", () => {
  it("success calls addToast with type=success", () => {
    toast.success({ title: "ok", message: "done" });
    expect(mockAddToast).toHaveBeenCalledWith(
      expect.objectContaining({ type: "success", duration: 3000 })
    );
  });

  it("error calls addToast with type=error", () => {
    toast.error({ title: "err", message: "fail" });
    expect(mockAddToast).toHaveBeenCalledWith(
      expect.objectContaining({ type: "error", duration: 5000 })
    );
  });

  it("warning calls addToast with type=warning", () => {
    toast.warning({ title: "w", message: "m" });
    expect(mockAddToast).toHaveBeenCalledWith(
      expect.objectContaining({ type: "warning", duration: 4000 })
    );
  });

  it("info calls addToast with type=info", () => {
    toast.info({ title: "i", message: "m" });
    expect(mockAddToast).toHaveBeenCalledWith(
      expect.objectContaining({ type: "info", duration: 3000 })
    );
  });

  it("allows custom duration", () => {
    toast.success({ title: "ok", message: "m", duration: 1000 });
    expect(mockAddToast).toHaveBeenCalledWith(
      expect.objectContaining({ duration: 1000 })
    );
  });
});
