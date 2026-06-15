import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CanvasQuickActions } from "./CanvasQuickActions";

describe("CanvasQuickActions", () => {
	const defaultProps = {
		selectedCount: 3,
		onAlignH: vi.fn(),
		onAlignV: vi.fn(),
		onDistributeH: vi.fn(),
		onDistributeV: vi.fn(),
		onGroup: vi.fn(),
		onUngroup: vi.fn(),
		onDelete: vi.fn(),
	};

	it("renders when selectedCount >= 2", () => {
		render(<CanvasQuickActions {...defaultProps} />);
		expect(screen.getByText("3 个选中")).toBeInTheDocument();
	});

	it("returns null when selectedCount < 2", () => {
		const { container } = render(<CanvasQuickActions {...defaultProps} selectedCount={1} />);
		expect(container.firstChild).toBeNull();
	});

	it("returns null when selectedCount = 0", () => {
		const { container } = render(<CanvasQuickActions {...defaultProps} selectedCount={0} />);
		expect(container.firstChild).toBeNull();
	});

	it("calls onDelete when delete button clicked", () => {
		render(<CanvasQuickActions {...defaultProps} />);
		const deleteBtn = screen.getByTitle("删除");
		fireEvent.click(deleteBtn);
		expect(defaultProps.onDelete).toHaveBeenCalled();
	});

	it("calls onGroup when group button clicked", () => {
		render(<CanvasQuickActions {...defaultProps} />);
		const groupBtn = screen.getByTitle("分组");
		fireEvent.click(groupBtn);
		expect(defaultProps.onGroup).toHaveBeenCalled();
	});

	it("calls onAlignH when horizontal align button clicked", () => {
		render(<CanvasQuickActions {...defaultProps} />);
		const alignHBtn = screen.getByTitle("水平对齐");
		fireEvent.click(alignHBtn);
		expect(defaultProps.onAlignH).toHaveBeenCalled();
	});

	it("calls onAlignV when vertical align button clicked", () => {
		render(<CanvasQuickActions {...defaultProps} />);
		const alignVBtn = screen.getByTitle("垂直对齐");
		fireEvent.click(alignVBtn);
		expect(defaultProps.onAlignV).toHaveBeenCalled();
	});

	it("has divider elements between button groups", () => {
		const { container } = render(<CanvasQuickActions {...defaultProps} />);
		const dividers = container.querySelectorAll(".divider");
		expect(dividers.length).toBe(2);
	});
});
