import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ListEmpty } from "./ListEmpty";

describe("ListEmpty", () => {
	it("renders empty state message when no search query", () => {
		render(<ListEmpty />);
		expect(screen.getByText("还没有内容")).toBeInTheDocument();
		expect(
			screen.getByText("在画布上创建内容后会显示在这里"),
		).toBeInTheDocument();
	});

	it("renders no matches message when search query is provided", () => {
		render(<ListEmpty searchQuery="test" />);
		expect(screen.getByText("没有找到匹配的内容")).toBeInTheDocument();
		expect(
			screen.getByText("尝试调整搜索关键词"),
		).toBeInTheDocument();
	});

	it("renders DocumentIcon", () => {
		const { container } = render(<ListEmpty />);
		const icon = container.querySelector("svg");
		expect(icon).toBeInTheDocument();
	});
});
