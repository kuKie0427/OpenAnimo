import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CanvasSearch } from "./CanvasSearch";

describe("CanvasSearch", () => {
	const defaultProps = {
		onSearch: vi.fn(),
		onFilterType: vi.fn(),
		resultCount: 0,
		onNavigateResult: vi.fn(),
		currentIndex: 0,
	};

	it("renders search input", () => {
		render(<CanvasSearch {...defaultProps} />);
		expect(screen.getByPlaceholderText("搜索...")).toBeInTheDocument();
	});

	it("renders type filter dropdown", () => {
		render(<CanvasSearch {...defaultProps} />);
		expect(screen.getByText("全部")).toBeInTheDocument();
		expect(screen.getByText("规划")).toBeInTheDocument();
		expect(screen.getByText("角色")).toBeInTheDocument();
		expect(screen.getByText("分镜")).toBeInTheDocument();
		expect(screen.getByText("合成")).toBeInTheDocument();
	});

	it("calls onSearch when input value changes", () => {
		render(<CanvasSearch {...defaultProps} />);
		const input = screen.getByPlaceholderText("搜索...");
		fireEvent.change(input, { target: { value: "test" } });
		expect(defaultProps.onSearch).toHaveBeenCalledWith("test");
	});

	it("calls onFilterType when dropdown changes", () => {
		const { container } = render(<CanvasSearch {...defaultProps} />);
		const select = container.querySelector("select") as HTMLSelectElement;
		fireEvent.change(select, { target: { value: "character-section" } });
		expect(defaultProps.onFilterType).toHaveBeenCalledWith("character-section");
	});

	it("shows result count when results > 0", () => {
		render(<CanvasSearch {...defaultProps} resultCount={5} currentIndex={2} />);
		expect(screen.getByText("3/5")).toBeInTheDocument();
	});

	it("does not show result count when results = 0", () => {
		render(<CanvasSearch {...defaultProps} />);
		expect(screen.queryByText("/")).toBeNull();
	});

	it("calls onNavigateResult with 'next' when down button clicked", () => {
		render(<CanvasSearch {...defaultProps} resultCount={3} currentIndex={0} />);
		const buttons = screen.getAllByRole("button");
		const lastButton = buttons[buttons.length - 1];
		fireEvent.click(lastButton);
		expect(defaultProps.onNavigateResult).toHaveBeenCalledWith("next");
	});

	it("calls onNavigateResult with 'prev' when up button clicked", () => {
		defaultProps.onNavigateResult.mockClear();
		render(<CanvasSearch {...defaultProps} resultCount={3} currentIndex={1} />);
		const buttons = screen.getAllByRole("button");
		fireEvent.click(buttons[0]);
		expect(defaultProps.onNavigateResult).toHaveBeenCalledWith("prev");
	});
});
