import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { TypewriterText } from "./TypewriterText";

describe("TypewriterText", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("renders full text immediately when disabled", () => {
    render(<TypewriterText text="hello" enabled={false} />);
    expect(screen.getByText("hello")).toBeInTheDocument();
  });

  it("starts empty when enabled", () => {
    const { container } = render(<TypewriterText text="abc" enabled={true} charDelay={100} />);
    expect(container.textContent).toBe("");
  });

  it("reveals characters over time", () => {
    const { container } = render(<TypewriterText text="abc" enabled={true} charDelay={100} />);
    act(() => { vi.advanceTimersByTime(100); });
    expect(container.textContent).toBe("a");
    act(() => { vi.advanceTimersByTime(100); });
    expect(container.textContent).toBe("ab");
    act(() => { vi.advanceTimersByTime(100); });
    expect(container.textContent).toBe("abc");
  });

  it("calls onComplete when finished", () => {
    const onComplete = vi.fn();
    render(<TypewriterText text="ab" enabled={true} charDelay={50} onComplete={onComplete} />);
    act(() => { vi.advanceTimersByTime(50); });
    act(() => { vi.advanceTimersByTime(50); });
    expect(onComplete).toHaveBeenCalled();
  });

  it("shows cursor while typing", () => {
    const { container } = render(<TypewriterText text="ab" enabled={true} charDelay={100} />);
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
    act(() => { vi.advanceTimersByTime(100); });
    act(() => { vi.advanceTimersByTime(100); });
    expect(container.querySelector(".animate-pulse")).not.toBeInTheDocument();
  });
});
