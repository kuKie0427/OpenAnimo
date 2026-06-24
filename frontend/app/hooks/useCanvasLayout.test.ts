import { describe, it, expect } from "vitest";
import { useCanvasLayout } from "./useCanvasLayout";
import { renderHook } from "@testing-library/react";
import type { SectionKey } from "./useCanvasLayout";
import type { Character, Shot } from "~/types";
import type { TLShapePartial } from "tldraw";

const defaultProps = {
	projectId: 1,
	story: "test story",
	summary: "test summary",
	characters: [] as Character[],
	shots: [] as Shot[],
	videoUrl: null as string | null,
	videoTitle: "Video",
	visibleSections: ["plan"] as SectionKey[],
	isGenerating: false,
	awaitingConfirm: false,
	currentRunId: null as number | null,
	currentStage: "plan" as const,
};

function makeCharacter(id: number, name: string): Character {
	return {
		id,
		project_id: 1,
		name,
		description: "",
		image_url: null,
		approval_state: "draft",
		approval_version: 1,
		approved_at: null,
		approved_name: null,
		approved_description: null,
		approved_image_url: null,
	} as unknown as Character;
}

function makeShot(id: number, order: number): Shot {
	return {
		id,
		project_id: 1,
		order,
		description: "",
		prompt: "",
		image_prompt: "",
		image_url: null,
		video_url: null,
		seed: null,
		duration: null,
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
	} as unknown as Shot;
}

function shapeProps(
	result: { current: { shapes: TLShapePartial[] } },
	type: string,
) {
	return result.current.shapes.find((shape) => shape.type === type)?.props as
		| Record<string, unknown>
		| undefined;
}

describe("useCanvasLayout", () => {
	it("returns an independently movable plan card when plan section is visible", () => {
		const { result } = renderHook(() =>
			useCanvasLayout({
				...defaultProps,
				visibleSections: ["plan"] as SectionKey[],
			}),
		);

		expect(result.current.shapes).toHaveLength(1);
		expect(result.current.shapes[0]?.type).toBe("plan-section");
	});

	it("returns no cards when no sections are visible", () => {
		const { result } = renderHook(() =>
			useCanvasLayout({
				...defaultProps,
				visibleSections: [] as SectionKey[],
			}),
		);

		expect(result.current.shapes).toHaveLength(0);
	});

	it("passes characters through the character section props", () => {
		const characters = [makeCharacter(1, "Alice"), makeCharacter(2, "Bob")];
		const { result } = renderHook(() =>
			useCanvasLayout({
				...defaultProps,
				characters,
				visibleSections: ["plan", "render"] as SectionKey[],
			}),
		);

		expect(shapeProps(result, "character-section")?.characters).toHaveLength(2);
	});

	it("passes shots through the storyboard section props", () => {
		const shots = [makeShot(10, 1), makeShot(20, 2)];
		const { result } = renderHook(() =>
			useCanvasLayout({
				...defaultProps,
				shots,
				visibleSections: ["plan", "render"] as SectionKey[],
			}),
		);

		expect(shapeProps(result, "storyboard-section")?.shots).toHaveLength(2);
	});

	it("includes compose card when compose is visible", () => {
		const { result } = renderHook(() =>
			useCanvasLayout({
				...defaultProps,
				videoUrl: "http://example.com/video.mp4",
				visibleSections: ["plan", "render", "compose"] as SectionKey[],
			}),
		);

		expect(result.current.shapes.map((shape) => shape.type)).toContain(
			"compose-section",
		);
	});

	it("does not include compose card when compose is not visible", () => {
		const { result } = renderHook(() =>
			useCanvasLayout({
				...defaultProps,
				videoUrl: "http://example.com/video.mp4",
				visibleSections: ["plan"] as SectionKey[],
			}),
		);

		expect(result.current.shapes.map((shape) => shape.type)).not.toContain(
			"compose-section",
		);
	});

	it("marks compose card blocked when blocking clips exist", () => {
		const { result } = renderHook(() =>
			useCanvasLayout({
				...defaultProps,
				videoUrl: "http://example.com/stale.mp4",
				visibleSections: ["compose"] as SectionKey[],
				blockingClips: [
					{ shot_id: 3, order: 2, status: "missing", reason: "视频缺失" },
				],
			}),
		);
		const props = shapeProps(result, "compose-section");

		expect(props?.sectionState).toBe("blocked");
		expect(props?.placeholderText).toBe("镜头 2: 视频缺失");
	});

	it("assigns stable card IDs", () => {
		const characters = [makeCharacter(42, "Test")];
		const { result } = renderHook(() =>
			useCanvasLayout({
				...defaultProps,
				characters,
				visibleSections: ["plan", "render"] as SectionKey[],
			}),
		);
		const ids = result.current.shapes.map((shape) => shape.id);

		const { result: result2 } = renderHook(() =>
			useCanvasLayout({
				...defaultProps,
				characters,
				visibleSections: ["plan", "render"] as SectionKey[],
			}),
		);

		expect(result2.current.shapes.map((shape) => shape.id)).toEqual(ids);
	});

	it("marks plan card state as generating when generating", () => {
		const { result } = renderHook(() =>
			useCanvasLayout({
				...defaultProps,
				isGenerating: true,
				story: null,
				summary: null,
				visibleSections: ["plan"] as SectionKey[],
			}),
		);

		expect(shapeProps(result, "plan-section")?.sectionState).toBe("generating");
	});

	it("marks plan card state as complete when story exists", () => {
		const { result } = renderHook(() =>
			useCanvasLayout({
				...defaultProps,
				story: "hello",
				summary: "world",
				visibleSections: ["plan"] as SectionKey[],
			}),
		);

		expect(shapeProps(result, "plan-section")?.sectionState).toBe("complete");
	});
});
