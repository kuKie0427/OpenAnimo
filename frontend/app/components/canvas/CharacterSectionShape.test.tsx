import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CharacterSectionShapeUtil } from "./shapes/CharacterSectionShape";
import type { CharacterSectionShape } from "./shapes/types";

vi.mock("~/services/api", () => ({
	getStaticUrl: (path: string | null | undefined) => path,
}));

vi.mock("~/hooks/useDomSize", () => ({
	useDomSize: () => ({ current: null }),
	getShapeSize: () => undefined,
}));

describe("CharacterSectionShape", () => {
	const shapeUtil = new CharacterSectionShapeUtil({} as never);

	const createShape = (props: Partial<CharacterSectionShape["props"]> = {}) =>
		({
			id: "char-shape",
			type: "character-section",
			x: 0,
			y: 0,
			props: {
				w: 800,
				h: 400,
				characters: [
					{
						id: 1,
						project_id: 1,
						name: "阿宁",
						description: "冷静的侦探",
						image_url: "/static/characters/aning.png",
						approval_state: "approved",
						approval_version: 2,
						approved_at: "2026-04-11T10:00:00Z",
						approved_name: "阿宁",
						approved_description: "冷静的侦探",
						approved_image_url: "/static/characters/aning-approved.png",
					},
				],
				sectionState: "complete",
				placeholder: false,
				statusLabel: "已完成",
				placeholderText: "等待角色生成...",
				...props,
			},
		}) as CharacterSectionShape;

	it("shows approval state dot and character info", () => {
		render(shapeUtil.component(createShape()));
		expect(screen.getByText("阿宁")).toBeInTheDocument();
		expect(screen.getByText("冷静的侦探")).toBeInTheDocument();
		expect(screen.getByText("v2")).toBeInTheDocument();
	});

	it("marks superseded characters with neutral dot", () => {
		render(
			shapeUtil.component(
				createShape({
					characters: [
						{
							id: 2,
							project_id: 1,
							name: "旧阿宁",
							description: "旧版本",
							image_url: "/static/characters/old.png",
							approval_state: "superseded",
							approval_version: 1,
							approved_at: null,
							approved_name: null,
							approved_description: null,
							approved_image_url: null,
						},
					],
				}),
			),
		);
		expect(screen.getByText("旧阿宁")).toBeInTheDocument();
	});

	it("shows placeholder when no characters", () => {
		render(
			shapeUtil.component(
				createShape({
					characters: [],
					placeholder: true,
					placeholderText: "等待角色生成...",
				}),
			),
		);
		expect(screen.getByText("等待角色生成...")).toBeInTheDocument();
	});

	it("renders multiple characters in grid", () => {
		render(
			shapeUtil.component(
				createShape({
					characters: [
						{
							id: 1,
							project_id: 1,
							name: "阿宁",
							description: "侦探",
							image_url: null,
							approval_state: "approved",
							approval_version: 1,
							approved_at: null,
							approved_name: null,
							approved_description: null,
							approved_image_url: null,
						},
						{
							id: 2,
							project_id: 1,
							name: "小李",
							description: "助手",
							image_url: null,
							approval_state: "draft",
							approval_version: 1,
							approved_at: null,
							approved_name: null,
							approved_description: null,
							approved_image_url: null,
						},
					],
				}),
			),
		);
		expect(screen.getByText("阿宁")).toBeInTheDocument();
		expect(screen.getByText("小李")).toBeInTheDocument();
	});

	it("returns null indicator", () => {
		expect(shapeUtil.indicator()).toBeNull();
	});

	it("has correct static type", () => {
		expect(CharacterSectionShapeUtil.type).toBe("character-section");
	});

	it("can select but cannot resize", () => {
		expect(shapeUtil.canEdit()).toBe(true);
		expect(shapeUtil.canResize()).toBe(false);
	});
});
