import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ListView } from "./ListView";

const mockShapes = [
	{
		id: "plan_1",
		type: "plan-section",
		content: { title: "剧情大纲", description: "故事的主线规划" },
		x: 0,
		y: 0,
	},
	{
		id: "char_1",
		type: "character-section",
		content: { title: "主角小明", description: "勇敢的少年" },
		x: 100,
		y: 0,
	},
	{
		id: "shot_1",
		type: "storyboard-section",
		content: { title: "开场镜头", imageUrl: "/shot.jpg" },
		x: 200,
		y: 0,
	},
	{
		id: "comp_1",
		type: "compose-section",
		content: { title: "最终合成" },
		x: 300,
		y: 0,
	},
];

describe("ListView", () => {
	const defaultProps = {
		projectId: 1,
		shapes: mockShapes,
		onShapeSelect: vi.fn(),
		onShapeEdit: vi.fn(),
		onShapeDelete: vi.fn(),
	};

	it("renders all shapes in the list", () => {
		render(<ListView {...defaultProps} />);
		expect(screen.getByText("剧情大纲")).toBeInTheDocument();
		expect(screen.getByText("主角小明")).toBeInTheDocument();
		expect(screen.getByText("开场镜头")).toBeInTheDocument();
		expect(screen.getByText("最终合成")).toBeInTheDocument();
	});

	it("filters shapes by search query (match title)", async () => {
		const user = userEvent.setup();
		render(<ListView {...defaultProps} />);

		await user.type(screen.getByPlaceholderText("搜索..."), "小明");
		expect(screen.getByText("主角小明")).toBeInTheDocument();
		expect(screen.queryByText("剧情大纲")).not.toBeInTheDocument();
	});

	it("filters shapes by search query (match description)", async () => {
		const user = userEvent.setup();
		render(<ListView {...defaultProps} />);

		await user.type(screen.getByPlaceholderText("搜索..."), "主线");
		expect(screen.getByText("剧情大纲")).toBeInTheDocument();
		expect(screen.queryByText("主角小明")).not.toBeInTheDocument();
	});

	it("filters shapes by type filter", async () => {
		const user = userEvent.setup();
		render(<ListView {...defaultProps} />);

		await user.selectOptions(
			screen.getByDisplayValue("全部类型"),
			"character-section",
		);
		expect(screen.getByText("主角小明")).toBeInTheDocument();
		expect(screen.queryByText("剧情大纲")).not.toBeInTheDocument();
	});

	it("sorts shapes by name", async () => {
		const user = userEvent.setup();
		render(<ListView {...defaultProps} />);

		await user.selectOptions(screen.getByDisplayValue("按位置"), "name");

		const titles = screen.getAllByRole("heading", { level: 4 });
		const texts = titles.map((el) => el.textContent);
		expect(texts).toEqual(["剧情大纲", "开场镜头", "主角小明", "最终合成"]);
	});

	it("sorts shapes by type", async () => {
		const user = userEvent.setup();
		render(<ListView {...defaultProps} />);

		await user.selectOptions(screen.getByDisplayValue("按位置"), "type");

		const titles = screen.getAllByRole("heading", { level: 4 });
		const texts = titles.map((el) => el.textContent);
		expect(texts).toEqual(["主角小明", "最终合成", "剧情大纲", "开场镜头"]);
	});

	it("multi-select: clicking checkbox selects item", async () => {
		const user = userEvent.setup();
		render(<ListView {...defaultProps} />);

		const checkboxes = screen.getAllByRole("checkbox");
		await user.click(checkboxes[0]);
		expect(checkboxes[0]).toBeChecked();
	});

	it("select all / deselect all", async () => {
		const user = userEvent.setup();
		render(<ListView {...defaultProps} />);

		await user.click(screen.getByText("全选"));
		const checkboxes = screen.getAllByRole("checkbox");
		for (const cb of checkboxes) {
			expect(cb).toBeChecked();
		}

		await user.click(screen.getByText("取消全选"));
		for (const cb of checkboxes) {
			expect(cb).not.toBeChecked();
		}
	});

	it("delete calls onShapeDelete with selected IDs", async () => {
		const user = userEvent.setup();
		const onShapeDelete = vi.fn();
		render(<ListView {...defaultProps} onShapeDelete={onShapeDelete} />);

		const checkboxes = screen.getAllByRole("checkbox");
		await user.click(checkboxes[0]);
		await user.click(checkboxes[1]);

		await user.click(screen.getByText("删除"));
		expect(onShapeDelete).toHaveBeenCalledWith(
			expect.arrayContaining(["plan_1", "char_1"]),
		);
	});

	it("shows empty state when no shapes and no search", () => {
		render(<ListView {...defaultProps} shapes={[]} />);
		expect(screen.getByText("还没有内容")).toBeInTheDocument();
	});

	it("shows no matches empty state when search yields no results", async () => {
		const user = userEvent.setup();
		render(<ListView {...defaultProps} />);

		await user.type(screen.getByPlaceholderText("搜索..."), "不存在的内容");
		expect(screen.getByText("没有找到匹配的内容")).toBeInTheDocument();
	});
});
