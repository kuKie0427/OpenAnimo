import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { StoryboardSectionShapeUtil } from "./shapes/StoryboardSectionShape";
import type { StoryboardSectionShape } from "./shapes/types";

vi.mock("~/services/api", () => ({
	getStaticUrl: (path: string | null | undefined) => path,
}));

vi.mock("~/hooks/useDomSize", () => ({
	useDomSize: () => ({ current: null }),
	getShapeSize: () => undefined,
}));

describe("StoryboardSectionShape", () => {
	const shapeUtil = new StoryboardSectionShapeUtil({} as never);

	const createShape = (props: Partial<StoryboardSectionShape["props"]> = {}) =>
		({
			id: "shot-shape",
			type: "storyboard-section",
			x: 0,
			y: 0,
			props: {
				w: 800,
				h: 500,
				shots: [
					{
						id: 11,
						project_id: 1,
						order: 1,
						description: "阿宁走进雨夜街道",
						prompt: "Wide shot of a detective in the rain",
						image_prompt: "雨夜街道，侦探，电影感",
						image_url: "/static/shots/1.png",
						video_url: "/static/shots/1.mp4",
						duration: 7,
						camera: "wide",
						motion_note: "slow push in",
						scene: null,
						action: null,
						expression: null,
						lighting: null,
						dialogue: null,
						sfx: null,
						character_ids: [1, 2],
						approval_state: "approved",
						approval_version: 3,
						approved_at: "2026-04-11T10:10:00Z",
						approved_description: "阿宁走进雨夜街道",
						approved_prompt: "Wide shot of a detective in the rain",
						approved_image_prompt: "雨夜街道，侦探，电影感",
						approved_duration: 7,
						approved_camera: "wide",
						approved_motion_note: "slow push in",
						approved_scene: null,
						approved_action: null,
						approved_expression: null,
						approved_lighting: null,
						approved_dialogue: null,
						approved_sfx: null,
						approved_character_ids: [1, 2],
						seed: null,
					},
				],
				sectionTitle: "分镜画面",
				sectionState: "complete",
				placeholder: false,
				statusLabel: "已完成",
				placeholderText: "等待分镜生成...",
				...props,
			},
		}) as unknown as StoryboardSectionShape;

	it("shows shot info, duration badge, and description", () => {
		render(shapeUtil.component(createShape()));
		expect(screen.getByText("7s")).toBeInTheDocument();
		expect(screen.getByText(/阿宁走进雨夜街道/)).toBeInTheDocument();
		expect(screen.getByText("镜头 1")).toBeInTheDocument();
		expect(screen.getByText("wide")).toBeInTheDocument();
	});

	it("does not duplicate character cards in shot section", () => {
		render(shapeUtil.component(createShape()));
		expect(screen.queryByText("角色")).not.toBeInTheDocument();
		expect(screen.queryByText("阿宁、老王")).not.toBeInTheDocument();
	});

	it("shows placeholder for shots without image", () => {
		render(
			shapeUtil.component(
				createShape({
					shots: [
						{
							id: 12,
							project_id: 1,
							order: 1,
							description: "无图镜头",
							prompt: "",
							image_prompt: "",
							image_url: null,
							video_url: null,
							duration: 3,
							camera: null,
							motion_note: null,
							scene: null,
							action: null,
							expression: null,
							lighting: null,
							dialogue: null,
							sfx: null,
							character_ids: [],
							approval_state: "draft",
							approval_version: 1,
							approved_at: null,
							approved_description: null,
							approved_prompt: null,
							approved_image_prompt: null,
							approved_duration: null,
							approved_camera: null,
							approved_motion_note: null,
							approved_scene: null,
							approved_action: null,
							approved_expression: null,
							approved_lighting: null,
							approved_dialogue: null,
							approved_sfx: null,
							approved_character_ids: [],
							seed: null,
						},
					],
				}),
			),
		);
		expect(screen.getByText("生成中...")).toBeInTheDocument();
		expect(screen.getByText("无图镜头")).toBeInTheDocument();
	});

	it("shows placeholder when no shots", () => {
		render(
			shapeUtil.component(
				createShape({
					shots: [],
					placeholder: true,
					placeholderText: "等待分镜生成...",
				}),
			),
		);
		expect(screen.getByText("等待分镜生成...")).toBeInTheDocument();
	});

	it("returns null indicator", () => {
		expect(shapeUtil.indicator()).toBeNull();
	});

	it("has correct static type", () => {
		expect(StoryboardSectionShapeUtil.type).toBe("storyboard-section");
	});

	it("can select but cannot resize", () => {
		expect(shapeUtil.canEdit()).toBe(true);
		expect(shapeUtil.canResize()).toBe(false);
	});
});
