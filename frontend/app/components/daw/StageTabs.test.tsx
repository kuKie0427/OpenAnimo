import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { StageTabs } from "./StageTabs";
import type { WorkflowStage } from "~/types";

const MockIcon = ({ className }: { className?: string }) => (
	<span className={className}>Icon</span>
);

const stages = [
	{ key: "plan" as WorkflowStage, label: "Plan", icon: MockIcon, status: "completed" as const },
	{ key: "render" as WorkflowStage, label: "Render", icon: MockIcon, status: "active" as const },
	{ key: "compose" as WorkflowStage, label: "Compose", icon: MockIcon, status: "pending" as const },
	{ key: "review" as WorkflowStage, label: "Review", icon: MockIcon, status: "error" as const },
];

describe("StageTabs", () => {
	it("renders all stage tabs", () => {
		render(
			<StageTabs currentStage="render" stages={stages} onStageChange={vi.fn()} />,
		);

		expect(screen.getByRole("tab", { name: /plan/i })).toBeInTheDocument();
		expect(screen.getByRole("tab", { name: /render/i })).toBeInTheDocument();
		expect(screen.getByRole("tab", { name: /compose/i })).toBeInTheDocument();
		expect(screen.getByRole("tab", { name: /review/i })).toBeInTheDocument();
	});

	it("marks the active tab with aria-selected", () => {
		render(
			<StageTabs currentStage="render" stages={stages} onStageChange={vi.fn()} />,
		);

		expect(screen.getByRole("tab", { name: /render/i })).toHaveAttribute("aria-selected", "true");
		expect(screen.getByRole("tab", { name: /plan/i })).toHaveAttribute("aria-selected", "false");
	});

	it("disables pending tabs", () => {
		render(
			<StageTabs currentStage="render" stages={stages} onStageChange={vi.fn()} />,
		);

		expect(screen.getByRole("tab", { name: /compose/i })).toBeDisabled();
	});

	it("calls onStageChange when a clickable tab is clicked", async () => {
		const user = userEvent.setup();
		const handleStageChange = vi.fn();
		render(
			<StageTabs currentStage="render" stages={stages} onStageChange={handleStageChange} />,
		);

		await user.click(screen.getByRole("tab", { name: /plan/i }));
		expect(handleStageChange).toHaveBeenCalledWith("plan");
	});

	it("does not call onStageChange when a pending tab is clicked", async () => {
		const user = userEvent.setup();
		const handleStageChange = vi.fn();
		render(
			<StageTabs currentStage="render" stages={stages} onStageChange={handleStageChange} />,
		);

		await user.click(screen.getByRole("tab", { name: /compose/i }));
		expect(handleStageChange).not.toHaveBeenCalled();
	});

	it("navigates with ArrowRight and wraps to first", async () => {
		const user = userEvent.setup();
		const handleStageChange = vi.fn();
		render(
			<StageTabs currentStage="render" stages={stages} onStageChange={handleStageChange} />,
		);

		const activeTab = screen.getByRole("tab", { name: /render/i });
		await user.click(activeTab);
		await user.keyboard("{ArrowRight}");

		expect(handleStageChange).toHaveBeenCalledWith("compose");
	});

	it("navigates with ArrowLeft and wraps to last", async () => {
		const user = userEvent.setup();
		const handleStageChange = vi.fn();
		render(
			<StageTabs currentStage="plan" stages={stages} onStageChange={handleStageChange} />,
		);

		const activeTab = screen.getByRole("tab", { name: /plan/i });
		await user.click(activeTab);
		await user.keyboard("{ArrowLeft}");

		expect(handleStageChange).toHaveBeenCalledWith("review");
	});

	it("shows check icon for completed status", () => {
		render(
			<StageTabs currentStage="render" stages={stages} onStageChange={vi.fn()} />,
		);

		const planTab = screen.getByRole("tab", { name: /plan/i });
		expect(planTab.querySelector(".text-success")).toBeInTheDocument();
	});

	it("shows exclamation icon for error status", () => {
		render(
			<StageTabs currentStage="render" stages={stages} onStageChange={vi.fn()} />,
		);

		const reviewTab = screen.getByRole("tab", { name: /review/i });
		expect(reviewTab.querySelector(".text-error")).toBeInTheDocument();
	});

	it("applies active styles to the current tab", () => {
		render(
			<StageTabs currentStage="render" stages={stages} onStageChange={vi.fn()} />,
		);

		const activeTab = screen.getByRole("tab", { name: /render/i });
		expect(activeTab).toHaveClass("text-primary");
	});
});
