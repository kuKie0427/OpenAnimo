import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TimelineView } from "./TimelineView";

const mockShapes = [
	{
		id: "shot_1",
		type: "storyboard-section" as const,
		x: 0,
		y: 0,
		content: { imageUrl: "/test.jpg" },
	},
	{
		id: "char_1",
		type: "character-section" as const,
		x: 0,
		y: 100,
		content: { name: "Alice" },
	},
];

describe("TimelineView", () => {
	const defaultProps = {
		projectId: 1,
		shapes: mockShapes,
		onShapeSelect: vi.fn(),
		onTimeChange: vi.fn(),
	};

	it("renders without crashing with empty shapes", () => {
		const { container } = render(
			<TimelineView
				projectId={1}
				shapes={[]}
				onShapeSelect={vi.fn()}
				onTimeChange={vi.fn()}
			/>,
		);
		expect(container).toBeTruthy();
	});

	it("renders track labels from shapes", () => {
		render(<TimelineView {...defaultProps} />);
		expect(screen.getByText("分镜")).toBeInTheDocument();
		expect(screen.getByText("角色")).toBeInTheDocument();
	});

	it("renders play/pause button", () => {
		render(<TimelineView {...defaultProps} />);
		expect(screen.getByLabelText("播放")).toBeInTheDocument();
	});

	it("renders time display", () => {
		render(<TimelineView {...defaultProps} />);
		expect(screen.getByText("0:00")).toBeInTheDocument();
	});

	it("calls onShapeSelect when a storyboard item is clicked", async () => {
		const user = userEvent.setup();
		const onSelect = vi.fn();
		render(
			<TimelineView
				{...defaultProps}
				onShapeSelect={onSelect}
			/>,
		);

		const item = screen.getByText("分镜 1");
		await user.click(item);
		expect(onSelect).toHaveBeenCalledWith("shot_1");
	});

	it("calls onShapeSelect when a character item is clicked", async () => {
		const user = userEvent.setup();
		const onSelect = vi.fn();
		render(
			<TimelineView
				{...defaultProps}
				onShapeSelect={onSelect}
			/>,
		);

		const item = screen.getByText("Alice");
		await user.click(item);
		expect(onSelect).toHaveBeenCalledWith("char_1");
	});
});
