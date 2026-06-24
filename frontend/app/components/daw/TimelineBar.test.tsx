import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { TimelineBar } from "./TimelineBar";
import type { WorkflowStage } from "~/types";

const stages = [
	{ key: "plan" as WorkflowStage, label: "Plan", progress: 100 },
	{ key: "render" as WorkflowStage, label: "Render", progress: 50 },
	{ key: "compose" as WorkflowStage, label: "Compose", progress: 0 },
	{ key: "review" as WorkflowStage, label: "Review", progress: 0 },
];

describe("TimelineBar", () => {
	it("renders all stages as buttons", () => {
		render(
			<TimelineBar currentStage="render" stages={stages} />,
		);

		expect(screen.getByTitle("Plan: 100%")).toBeInTheDocument();
		expect(screen.getByTitle("Render: 50%")).toBeInTheDocument();
		expect(screen.getByTitle("Compose: 0%")).toBeInTheDocument();
		expect(screen.getByTitle("Review: 0%")).toBeInTheDocument();
	});

	it("highlights current stage with bg-primary", () => {
		const { container } = render(
			<TimelineBar currentStage="render" stages={stages} />,
		);

		const buttons = container.querySelectorAll("button");
		expect(buttons[1]).toHaveClass("bg-primary");
	});

	it("shows bg-success for completed stages", () => {
		const { container } = render(
			<TimelineBar currentStage="render" stages={stages} />,
		);

		const buttons = container.querySelectorAll("button");
		expect(buttons[0]).toHaveClass("bg-success");
	});

	it("shows bg-base-content/10 for pending stages", () => {
		const { container } = render(
			<TimelineBar currentStage="render" stages={stages} />,
		);

		const buttons = container.querySelectorAll("button");
		expect(buttons[2]).toHaveClass("bg-base-content/10");
		expect(buttons[3]).toHaveClass("bg-base-content/10");
	});

	it("calls onStageClick when a stage is clicked", async () => {
		const user = userEvent.setup();
		const onStageClick = vi.fn();
		render(
			<TimelineBar
				currentStage="render"
				stages={stages}
				onStageClick={onStageClick}
			/>,
		);

		await user.click(screen.getByTitle("Plan: 100%"));
		expect(onStageClick).toHaveBeenCalledWith("plan");
	});

	it("does not throw when onStageClick is not provided", async () => {
		const user = userEvent.setup();
		render(
			<TimelineBar currentStage="render" stages={stages} />,
		);

		await user.click(screen.getByTitle("Render: 50%"));
	});

	it("shows current item info when provided", () => {
		const currentItem = { id: 1, title: "My Scene" };
		render(
			<TimelineBar
				currentStage="render"
				stages={stages}
				currentItem={currentItem}
			/>,
		);

		expect(screen.getByText("render")).toBeInTheDocument();
		expect(screen.getByText("My Scene")).toBeInTheDocument();
	});

	it("does not show current item info when not provided", () => {
		render(
			<TimelineBar currentStage="render" stages={stages} />,
		);

		expect(screen.queryByText("render")).not.toBeInTheDocument();
	});

	it("renders progress percentage in title attribute", () => {
		render(
			<TimelineBar currentStage="plan" stages={stages} />,
		);

		expect(screen.getByTitle("Plan: 100%")).toBeInTheDocument();
		expect(screen.getByTitle("Render: 50%")).toBeInTheDocument();
	});

	it("handles first stage as current", () => {
		const { container } = render(
			<TimelineBar currentStage="plan" stages={stages} />,
		);

		const buttons = container.querySelectorAll("button");
		expect(buttons[0]).toHaveClass("bg-primary");
		expect(buttons[1]).toHaveClass("bg-base-content/10");
		expect(buttons[2]).toHaveClass("bg-base-content/10");
		expect(buttons[3]).toHaveClass("bg-base-content/10");
	});

	it("handles last stage as current", () => {
		const { container } = render(
			<TimelineBar currentStage="review" stages={stages} />,
		);

		const buttons = container.querySelectorAll("button");
		expect(buttons[0]).toHaveClass("bg-success");
		expect(buttons[1]).toHaveClass("bg-success");
		expect(buttons[2]).toHaveClass("bg-success");
		expect(buttons[3]).toHaveClass("bg-primary");
	});
});
