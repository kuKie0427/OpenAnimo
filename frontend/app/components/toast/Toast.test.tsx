import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Toast } from "./Toast";

vi.mock("~/stores/toast.store", () => ({
  useToastStore: Object.assign(
    vi.fn((selector: any) =>
      selector({ removeToast: mockRemoveToast })
    ),
    { getState: () => ({ removeToast: mockRemoveToast }) }
  ),
}));

let mockRemoveToast: ReturnType<typeof vi.fn>;

beforeEach(() => {
  mockRemoveToast = vi.fn();
});

const baseToast = {
  id: "t1",
  type: "success" as const,
  title: "Title",
  message: "Body text",
  duration: 0,
};

describe("Toast", () => {
  it("renders title and message", () => {
    render(<Toast toast={baseToast} />);
    expect(screen.getByText("Title")).toBeInTheDocument();
    expect(screen.getByText("Body text")).toBeInTheDocument();
  });

  it("calls removeToast on close click", () => {
    render(<Toast toast={baseToast} />);
    fireEvent.click(screen.getByLabelText("关闭"));
    expect(mockRemoveToast).toHaveBeenCalledWith("t1");
  });

  it("renders action buttons", () => {
    const onClick = vi.fn();
    const toastWithActions = {
      ...baseToast,
      actions: [{ label: "Retry", onClick, variant: "primary" as const }],
    };
    render(<Toast toast={toastWithActions} />);
    fireEvent.click(screen.getByText("Retry"));
    expect(onClick).toHaveBeenCalled();
    expect(mockRemoveToast).toHaveBeenCalledWith("t1");
  });

  it("auto-removes after duration", () => {
    vi.useFakeTimers();
    const toastWithDuration = { ...baseToast, duration: 5000 };
    render(<Toast toast={toastWithDuration} />);
    vi.advanceTimersByTime(5000);
    expect(mockRemoveToast).toHaveBeenCalledWith("t1");
    vi.useRealTimers();
  });
});
