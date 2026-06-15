import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ListItem } from "./ListItem";

const makeShape = (overrides: Record<string, unknown> = {}) => ({
	id: "shape_1",
	type: "plan-section",
	content: { title: "测试标题", description: "测试描述" },
	x: 0,
	y: 0,
	...overrides,
});

describe("ListItem", () => {
	const defaultProps = {
		isSelected: false,
		onSelect: vi.fn(),
		onClick: vi.fn(),
		onEdit: vi.fn(),
	};

	it("renders title from shape content", () => {
		render(
			<ListItem shape={makeShape()} {...defaultProps} />,
		);
		expect(screen.getByText("测试标题")).toBeInTheDocument();
	});

	it("renders description when present", () => {
		render(
			<ListItem shape={makeShape()} {...defaultProps} />,
		);
		expect(screen.getByText("测试描述")).toBeInTheDocument();
	});

	it("renders 未命名 default title when no title", () => {
		render(
			<ListItem
				shape={makeShape({ content: { description: "desc" } })}
				{...defaultProps}
			/>,
		);
		expect(screen.getByText("未命名")).toBeInTheDocument();
	});

	it("renders type badge with label", () => {
		render(
			<ListItem
				shape={makeShape({ type: "character-section" })}
				{...defaultProps}
			/>,
		);
		expect(screen.getByText("角色")).toBeInTheDocument();
	});

	it("shows selected state (checkbox checked)", () => {
		render(
			<ListItem shape={makeShape()} {...defaultProps} isSelected />,
		);
		const checkbox = screen.getByRole("checkbox");
		expect(checkbox).toBeChecked();
	});

	it("shows unselected state (checkbox unchecked)", () => {
		render(
			<ListItem
				shape={makeShape()}
				{...defaultProps}
				isSelected={false}
			/>,
		);
		const checkbox = screen.getByRole("checkbox");
		expect(checkbox).not.toBeChecked();
	});

	it("checkbox calls onSelect with correct value", async () => {
		const user = userEvent.setup();
		const onSelect = vi.fn();
		render(
			<ListItem
				shape={makeShape()}
				{...defaultProps}
				onSelect={onSelect}
			/>,
		);

		await user.click(screen.getByRole("checkbox"));
		expect(onSelect).toHaveBeenCalledWith(true);
	});

	it("click calls onClick", async () => {
		const user = userEvent.setup();
		const onClick = vi.fn();
		render(
			<ListItem shape={makeShape()} {...defaultProps} onClick={onClick} />,
		);

		await user.click(screen.getByText("测试标题"));
		expect(onClick).toHaveBeenCalledTimes(1);
	});

	it("edit button calls onEdit", async () => {
		const user = userEvent.setup();
		const onEdit = vi.fn();
		render(
			<ListItem shape={makeShape()} {...defaultProps} onEdit={onEdit} />,
		);

		await user.click(screen.getByTitle("编辑"));
		expect(onEdit).toHaveBeenCalledTimes(1);
	});

	it("renders thumbnail image when imageUrl present", () => {
		const { container } = render(
			<ListItem
				shape={makeShape({
					content: {
						title: "有图",
						imageUrl: "/test-thumb.jpg",
					},
				})}
				{...defaultProps}
			/>,
		);
		const img = container.querySelector("img");
		expect(img).toHaveAttribute("src", "/test-thumb.jpg");
	});

	it("does NOT render thumbnail when no imageUrl", () => {
		render(
			<ListItem shape={makeShape()} {...defaultProps} />,
		);
		expect(screen.queryByRole("img")).not.toBeInTheDocument();
	});
});
