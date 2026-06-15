import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { DetailPanel } from "./DetailPanel";

const itemWithContent = {
	id: 1,
	title: "Scene One",
	content: "A beautiful sunset over the mountains.",
};

const itemWithMedia = {
	id: 2,
	title: "Scene Two",
	content: "An action sequence in the city.",
	images: ["/img/scene2-1.jpg", "/img/scene2-2.jpg"],
	videos: ["/video/scene2.mp4"],
};

describe("DetailPanel", () => {
	it("shows empty state when item is null", () => {
		render(<DetailPanel item={null} />);
		expect(screen.getByText("选择一个项目查看详情")).toBeInTheDocument();
	});

	it("shows DocumentTextIcon placeholder in empty state", () => {
		const { container } = render(<DetailPanel item={null} />);
		const icon = container.querySelector(".w-12.h-12");
		expect(icon).toBeInTheDocument();
	});

	it("renders title when item is provided", () => {
		render(<DetailPanel item={itemWithContent} />);
		expect(screen.getByRole("heading", { name: /scene one/i })).toBeInTheDocument();
	});

	it("renders content text", () => {
		render(<DetailPanel item={itemWithContent} />);
		expect(screen.getByText("A beautiful sunset over the mountains.")).toBeInTheDocument();
	});

	it("does not render empty state when item is provided", () => {
		render(<DetailPanel item={itemWithContent} />);
		expect(screen.queryByText("选择一个项目查看详情")).not.toBeInTheDocument();
	});

	it("renders images when images are provided", () => {
		render(<DetailPanel item={itemWithMedia} />);
		const images = screen.getAllByRole("img");
		expect(images).toHaveLength(2);
		expect(images[0]).toHaveAttribute("src", "/img/scene2-1.jpg");
		expect(images[1]).toHaveAttribute("src", "/img/scene2-2.jpg");
	});

	it("does not render images when images array is empty", () => {
		const item = { ...itemWithContent, images: [] as string[] };
		render(<DetailPanel item={item} />);
		expect(screen.queryAllByRole("img")).toHaveLength(0);
	});

	it("does not render images when images not provided", () => {
		render(<DetailPanel item={itemWithContent} />);
		expect(screen.queryAllByRole("img")).toHaveLength(0);
	});

	it("renders videos when videos are provided", () => {
		const { container } = render(<DetailPanel item={itemWithMedia} />);
		const videos = container.querySelectorAll("video");
		expect(videos).toHaveLength(1);
		expect(videos[0]).toHaveAttribute("src", "/video/scene2.mp4");
	});

	it("does not render videos when not provided", () => {
		const { container } = render(<DetailPanel item={itemWithContent} />);
		expect(container.querySelectorAll("video")).toHaveLength(0);
	});

	it("shows edit button when onEdit is provided", async () => {
		const user = userEvent.setup();
		const onEdit = vi.fn();
		render(<DetailPanel item={itemWithContent} onEdit={onEdit} />);

		const editButton = screen.getByRole("button", { name: /编辑/i });
		expect(editButton).toBeInTheDocument();

		await user.click(editButton);
		expect(onEdit).toHaveBeenCalledWith(1);
	});

	it("shows regenerate button when onRegenerate is provided", async () => {
		const user = userEvent.setup();
		const onRegenerate = vi.fn();
		render(<DetailPanel item={itemWithContent} onRegenerate={onRegenerate} />);

		const regenButton = screen.getByRole("button", { name: /重新生成/i });
		expect(regenButton).toBeInTheDocument();

		await user.click(regenButton);
		expect(onRegenerate).toHaveBeenCalledWith(1);
	});

	it("hides edit button when onEdit is not provided", () => {
		render(<DetailPanel item={itemWithContent} />);
		expect(screen.queryByRole("button", { name: /编辑/i })).not.toBeInTheDocument();
	});

	it("hides regenerate button when onRegenerate is not provided", () => {
		render(<DetailPanel item={itemWithContent} />);
		expect(screen.queryByRole("button", { name: /重新生成/i })).not.toBeInTheDocument();
	});

	it("shows both buttons when both callbacks provided", () => {
		render(
			<DetailPanel
				item={itemWithContent}
				onEdit={vi.fn()}
				onRegenerate={vi.fn()}
			/>,
		);
		expect(screen.getByRole("button", { name: /编辑/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /重新生成/i })).toBeInTheDocument();
	});

	it("renders metadata when provided", () => {
		const item = { ...itemWithContent, metadata: { style: "watercolor", fps: "24" } };
		render(<DetailPanel item={item} />);

		expect(screen.getByText("元数据")).toBeInTheDocument();
		expect(screen.getByText("style:")).toBeInTheDocument();
		expect(screen.getByText("watercolor")).toBeInTheDocument();
		expect(screen.getByText("fps:")).toBeInTheDocument();
		expect(screen.getByText("24")).toBeInTheDocument();
	});

	it("does not render metadata when empty", () => {
		const item = { ...itemWithContent, metadata: {} };
		render(<DetailPanel item={item} />);
		expect(screen.queryByText("元数据")).not.toBeInTheDocument();
	});
});
