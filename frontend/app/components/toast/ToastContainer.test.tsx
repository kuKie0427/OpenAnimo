import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ToastContainer } from "./ToastContainer";

const mockToasts: any[] = [];

vi.mock("~/stores/toast.store", () => ({
  useToastStore: vi.fn((selector: any) => selector({ toasts: mockToasts })),
}));

describe("ToastContainer", () => {
  beforeEach(() => {
    mockToasts.length = 0;
  });

  it("returns null when no toasts", () => {
    const { container } = render(<ToastContainer />);
    expect(container.innerHTML).toBe("");
  });

  it("renders toasts", () => {
    mockToasts.push({
      id: "1",
      type: "success",
      title: "Done",
      message: "It worked",
      duration: 0,
    });
    render(<ToastContainer />);
    expect(screen.getByText("Done")).toBeInTheDocument();
  });
});
