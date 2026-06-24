import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CanvasBreadcrumb } from "./CanvasBreadcrumb";

describe("CanvasBreadcrumb", () => {
	const defaultProps = {
		projectId: 1,
		currentStage: "plan" as const,
		selectedShapeId: undefined,
		onStageClick: vi.fn(),
		onShapeClick: vi.fn(),
		onFitToContent: vi.fn(),
	};

	it("renders current stage name", () => {
		render(<CanvasBreadcrumb {...defaultProps} />);
		expect(screen.getByText("plan")).toBeInTheDocument();
	});

	it("renders fit to content button", () => {
		render(<CanvasBreadcrumb {...defaultProps} />);
		const button = screen.getByTitle("适应内容");
		expect(button).toBeInTheDocument();
		fireEvent.click(button);
		expect(defaultProps.onFitToContent).toHaveBeenCalled();
	});

	it("renders selected shape ID when provided", () => {
		render(<CanvasBreadcrumb {...defaultProps} selectedShapeId="shape:123" />);
		expect(screen.getByText("shape:123")).toBeInTheDocument();
	});

	it("does not render separator when no shape selected", () => {
		const { container } = render(<CanvasBreadcrumb {...defaultProps} />);
		const separators = container.querySelectorAll("span");
		expect(separators.length).toBe(1);
	});

	it("calls onStageClick when stage is clicked", () => {
		render(<CanvasBreadcrumb {...defaultProps} />);
		fireEvent.click(screen.getByText("plan"));
		expect(defaultProps.onStageClick).toHaveBeenCalledWith("plan");
	});

	it("calls onShapeClick when shape ID is clicked", () => {
		render(<CanvasBreadcrumb {...defaultProps} selectedShapeId="shape:456" />);
		fireEvent.click(screen.getByText("shape:456"));
		expect(defaultProps.onShapeClick).toHaveBeenCalledWith("shape:456");
	});

	it("truncates long shape IDs", () => {
		const longId = "shape:" + "a".repeat(200);
		render(<CanvasBreadcrumb {...defaultProps} selectedShapeId={longId} />);
		const button = screen.getByText(longId);
		expect(button.className).toContain("truncate");
		expect(button.className).toContain("max-w-[120px]");
	});
});
