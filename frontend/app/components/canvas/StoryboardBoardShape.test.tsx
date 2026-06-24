import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { StoryboardBoardShapeUtil } from "./shapes/StoryboardBoardShape";
import type { StoryboardBoardShape } from "./shapes/types";

vi.mock("~/services/api", () => ({
	getStaticUrl: (path: string | null | undefined) => path,
}));

vi.mock("~/hooks/useDomSize", () => ({
	useDomSize: () => ({ current: null }),
	getShapeSize: () => undefined,
}));

const shapeUtil = new StoryboardBoardShapeUtil({} as never);

function createShape(
	props: Partial<StoryboardBoardShape["props"]> = {},
): StoryboardBoardShape {
	return {
		id: "shape:storyboard-board",
		type: "storyboard-board",
		x: 0,
		y: 0,
		props: {
			w: 920,
			h: 600,
			projectId: 1,
			story: "小猫喝水",
			summary: "小猫在阳光下喝水",
			characters: [],
			shots: [],
			videoUrl: "",
			videoTitle: "小猫喝水",
			visibleSections: ["plan", "render", "compose"],
			sectionStates: {
				plan: "complete",
				render: "complete",
				compose: "draft",
			},
			placeholders: {
				plan: false,
				render: true,
				compose: true,
			},
			statusLabels: {
				plan: "已完成",
				render: "已完成",
				compose: "待生成",
			},
			placeholderTexts: {
				render: "等待角色和分镜渲染生成...",
				compose: "等待视频合成...",
			},
			downloadUrl: "/api/v1/projects/1/final-video",
			...props,
		},
	} as StoryboardBoardShape;
}

describe("StoryboardBoardShape", () => {
	it("renders all visible sections inside one board", () => {
		render(shapeUtil.component(createShape()));

		expect(screen.getByText("编剧规划")).toBeInTheDocument();
		expect(screen.getByText("视觉渲染")).toBeInTheDocument();
		expect(screen.getByText("最终输出")).toBeInTheDocument();
	});

	it("renders curved flow connector labels between adjacent sections", () => {
		render(shapeUtil.component(createShape()));

		expect(screen.getByText("角色与分镜接力")).toBeInTheDocument();
		expect(screen.getByText("镜头汇成成片")).toBeInTheDocument();
	});
});
