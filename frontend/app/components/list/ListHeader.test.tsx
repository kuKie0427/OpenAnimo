import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ListHeader } from "./ListHeader";

describe("ListHeader", () => {
	const defaultProps = {
		searchQuery: "",
		onSearchChange: vi.fn(),
		typeFilter: "all",
		onTypeFilterChange: vi.fn(),
		sortBy: "position" as const,
		onSortChange: vi.fn(),
		selectedCount: 0,
		totalCount: 5,
		onSelectAll: vi.fn(),
		onDelete: vi.fn(),
	};

	it("renders search input and accepts text changes", async () => {
		const user = userEvent.setup();
		const onSearchChange = vi.fn();
		render(
			<ListHeader {...defaultProps} onSearchChange={onSearchChange} />,
		);

		const input = screen.getByPlaceholderText("搜索...");
		await user.type(input, "abc");
		expect(onSearchChange).toHaveBeenCalledTimes(3);
	});

	it("renders type filter dropdown with all options", () => {
		render(<ListHeader {...defaultProps} />);
		const select = screen.getByDisplayValue("全部类型");
		expect(select).toBeInTheDocument();
		expect(screen.getByText("规划")).toBeInTheDocument();
		expect(screen.getByText("角色")).toBeInTheDocument();
		expect(screen.getByText("分镜")).toBeInTheDocument();
		expect(screen.getByText("合成")).toBeInTheDocument();
	});

	it("renders sort dropdown with all options", () => {
		render(<ListHeader {...defaultProps} />);
		expect(screen.getByDisplayValue("按位置")).toBeInTheDocument();
		expect(screen.getByText("按名称")).toBeInTheDocument();
		expect(screen.getByText("按类型")).toBeInTheDocument();
	});

	it("select all button calls onSelectAll when clicked", async () => {
		const user = userEvent.setup();
		const onSelectAll = vi.fn();
		render(
			<ListHeader {...defaultProps} onSelectAll={onSelectAll} />,
		);

		await user.click(screen.getByText("全选"));
		expect(onSelectAll).toHaveBeenCalledTimes(1);
	});

	it("delete button appears when selectedCount > 0", () => {
		render(
			<ListHeader {...defaultProps} selectedCount={2} totalCount={5} />,
		);
		expect(screen.getByText("删除")).toBeInTheDocument();
	});

	it("delete button calls onDelete when clicked", async () => {
		const user = userEvent.setup();
		const onDelete = vi.fn();
		render(
			<ListHeader
				{...defaultProps}
				selectedCount={2}
				totalCount={5}
				onDelete={onDelete}
			/>,
		);

		await user.click(screen.getByText("删除"));
		expect(onDelete).toHaveBeenCalledTimes(1);
	});

	it("selection count text shows correct numbers", () => {
		render(
			<ListHeader {...defaultProps} selectedCount={3} totalCount={10} />,
		);
		expect(screen.getByText("3 / 10 选中")).toBeInTheDocument();
	});

	it("shows cancel all button text when all selected", () => {
		render(
			<ListHeader {...defaultProps} selectedCount={5} totalCount={5} />,
		);
		expect(screen.getByText("取消全选")).toBeInTheDocument();
	});
});
