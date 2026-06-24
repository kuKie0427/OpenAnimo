import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AppShell } from "./AppShell";

vi.mock("./TopBar", () => ({
  TopBar: () => <div data-testid="topbar">TopBar</div>,
}));

vi.mock("./StagePipeline", () => ({
  StagePipeline: () => <div data-testid="stagepipeline">StagePipeline</div>,
}));

vi.mock("./DrawerPortal", () => ({
  DrawerPortal: () => <div data-testid="drawerportal">DrawerPortal</div>,
}));

describe("AppShell", () => {
  const defaultProps = {
    onToggleAssets: vi.fn(),
    onToggleHistory: vi.fn(),
    onAssetsClose: vi.fn(),
    onHistoryClose: vi.fn(),
    chatIsGenerating: false,
    onChatSendFeedback: vi.fn(),
    onChatConfirm: vi.fn(),
    onChatEntityConfirm: vi.fn(),
    onChatGenerate: vi.fn(),
    onChatCancel: vi.fn(),
    versionCompareOpen: false,
    versionCompareProjectId: 1,
    onVersionCompareClose: vi.fn(),
  };

  it("renders with default variant", () => {
    render(
      <AppShell {...defaultProps}>
        <div data-testid="content">Page Content</div>
      </AppShell>
    );

    expect(screen.getByTestId("topbar")).toBeInTheDocument();
    expect(screen.getByTestId("drawerportal")).toBeInTheDocument();
    expect(screen.getByTestId("content")).toHaveTextContent("Page Content");
  });

  it("renders children correctly", () => {
    render(
      <AppShell {...defaultProps}>
        <div data-testid="child">Child Element</div>
      </AppShell>
    );

    expect(screen.getByTestId("child")).toBeInTheDocument();
  });

  it("applies layout class h-screen flex flex-col", () => {
    const { container } = render(
      <AppShell {...defaultProps}>
        <div>Content</div>
      </AppShell>
    );

    const shell = container.firstChild as HTMLElement;
    expect(shell.classList.contains("h-screen")).toBe(true);
    expect(shell.classList.contains("flex")).toBe(true);
    expect(shell.classList.contains("flex-col")).toBe(true);
  });

  it("renders StagePipeline when showStagePipeline is true", () => {
    render(
      <AppShell {...defaultProps} showStagePipeline={true} currentStage="plan">
        <div>Content</div>
      </AppShell>
    );

    expect(screen.getByTestId("stagepipeline")).toBeInTheDocument();
  });

  it("does not render StagePipeline when showStagePipeline is false", () => {
    render(
      <AppShell {...defaultProps} showStagePipeline={false}>
        <div>Content</div>
      </AppShell>
    );

    expect(screen.queryByTestId("stagepipeline")).not.toBeInTheDocument();
  });
});
