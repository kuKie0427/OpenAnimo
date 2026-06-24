import { render, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CanvasMinimap } from "./CanvasMinimap";

describe("CanvasMinimap", () => {
	const defaultProps = {
		shapes: [
			{ id: "shape:1", x: 0, y: 0, width: 420, height: 260, type: "plan-section" },
			{ id: "shape:2", x: 600, y: 100, width: 420, height: 360, type: "character-section" },
			{ id: "shape:3", x: 1200, y: 200, width: 420, height: 260, type: "storyboard-section" },
		],
		viewport: { x: 0, y: 0, width: 800, height: 600 },
		canvasBounds: { width: 2000, height: 1000 },
		onNavigate: vi.fn(),
	};

	it("renders minimap container", () => {
		const { container } = render(<CanvasMinimap {...defaultProps} />);
		const minimap = container.firstChild as HTMLElement;
		expect(minimap.className).toContain("w-[150px]");
		expect(minimap.className).toContain("h-[100px]");
	});

	it("renders shape thumbnails", () => {
		const { container } = render(<CanvasMinimap {...defaultProps} />);
		const minimap = container.firstChild as HTMLElement;
		expect(minimap.children.length).toBeGreaterThanOrEqual(4);
	});

	it("color-codes shapes by type", () => {
		const { container } = render(<CanvasMinimap {...defaultProps} />);
		const minimap = container.firstChild as HTMLElement;
		const children = Array.from(minimap.children);
		const shapeDivs = children.slice(0, 3);
		expect(shapeDivs[0].className).toContain("bg-primary/30");
		expect(shapeDivs[1].className).toContain("bg-accent/30");
		expect(shapeDivs[2].className).toContain("bg-secondary/30");
	});

	it("renders viewport indicator", () => {
		const { container } = render(<CanvasMinimap {...defaultProps} />);
		const minimap = container.firstChild as HTMLElement;
		const children = Array.from(minimap.children);
		const viewportDiv = children.find((c) => c.className.includes("border-primary/50"));
		expect(viewportDiv).toBeDefined();
	});

	it("handles empty shapes array", () => {
		const { container } = render(<CanvasMinimap {...defaultProps} shapes={[]} />);
		const minimap = container.firstChild as HTMLElement;
		expect(minimap.children.length).toBeGreaterThanOrEqual(2);
	});

	it("calls onNavigate when click overlay is clicked", () => {
		const { container } = render(<CanvasMinimap {...defaultProps} />);
		const minimap = container.firstChild as HTMLElement;
		const clickOverlay = Array.from(minimap.children).find(
			(c) => c.className.includes("cursor-pointer"),
		);
		expect(clickOverlay).toBeDefined();
		fireEvent.click(clickOverlay!);
		expect(defaultProps.onNavigate).toHaveBeenCalled();
	});
});
