import { render, waitFor } from "@testing-library/react";
import { type ReactNode, useEffect } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InfiniteCanvas } from "./InfiniteCanvas";
import type { SectionKey } from "~/hooks/useCanvasLayout";
import type { Character, RecoverySummaryRead, Shot } from "~/types";

interface LayoutMockArgs {
	story?: string | null;
	summary?: string | null;
	visibleSections?: SectionKey[];
	videoUrl?: string | null;
	blockingClips?: unknown[] | null;
}

interface MockShape {
	id: string;
	type?: string;
	x?: number;
	y?: number;
	parentId?: string;
	props?: Record<string, unknown>;
	meta?: Record<string, unknown>;
}

interface MockEditor {
	run: ReturnType<typeof vi.fn<(fn: () => void) => void>>;
	createShapes: ReturnType<typeof vi.fn<(nextShapes: MockShape[]) => void>>;
	updateShapes: ReturnType<typeof vi.fn<(nextShapes: MockShape[]) => void>>;
	deleteShapes: ReturnType<typeof vi.fn<(ids: string[]) => void>>;
	getCurrentPageShapes: ReturnType<typeof vi.fn<() => MockShape[]>>;
	getBindingsFromShape: ReturnType<typeof vi.fn<() => unknown[]>>;
	createBindings: ReturnType<typeof vi.fn<(bindings: unknown[]) => void>>;
	deleteBindings: ReturnType<typeof vi.fn>;
	getShape: ReturnType<typeof vi.fn<(id: string) => MockShape | null>>;
	getShapeGeometry: ReturnType<
		typeof vi.fn<
			() => { bounds: { x: number; y: number; w: number; h: number } }
		>
	>;
	zoomToBounds: ReturnType<typeof vi.fn>;
	getZoomLevel: ReturnType<typeof vi.fn<() => number>>;
	store: { listen: ReturnType<typeof vi.fn<() => () => void>> };
	zoomToFit: ReturnType<typeof vi.fn>;
	animateShape: ReturnType<typeof vi.fn>;
	sideEffects: {
		registerBeforeChangeHandler: ReturnType<typeof vi.fn<() => () => void>>;
		registerAfterChangeHandler: ReturnType<typeof vi.fn<() => () => void>>;
	};
	// New methods for canvas enhancement features
	on: ReturnType<typeof vi.fn<(event: string, handler: () => void) => void>>;
	off: ReturnType<typeof vi.fn<(event: string, handler: () => void) => void>>;
	getSelectedShapeIds: ReturnType<typeof vi.fn<() => MockShape["id"][]>>;
	centerOnPoint: ReturnType<typeof vi.fn>;
	selectNone: ReturnType<typeof vi.fn>;
	select: ReturnType<typeof vi.fn<(id: string) => void>>;
	getViewportPageBounds: ReturnType<typeof vi.fn<() => { x: number; y: number; width: number; height: number }>>;
	reset: () => void;
}

interface MockEditorStoreState {
	characters: Character[];
	shots: Shot[];
	projectVideoUrl: string | null;
	projectTitle: string | null;
	projectSummary: string | null;
	projectStory: string | null;
	currentStage: string | null;
	recoverySummary: RecoverySummaryRead | null;
	currentRunId: number | null;
	isGenerating: boolean;
	awaitingConfirm: boolean;
	blockingClips: unknown[] | null;
}

const useCanvasLayoutMock = vi.hoisted(() =>
	vi.fn((args: LayoutMockArgs) => ({
		shapes: [
			{
				id: "shape:plan-section",
				type: "plan-section",
				x: 100,
				y: 100,
				props: {
					w: 420,
					h: 260,
					projectId: 1,
					story: "",
					summary: "",
					characters: [],
					shots: [],
					sectionState: "complete",
					placeholder: false,
					statusLabel: "已完成",
					placeholderText: "",
				},
			},
			...(args.visibleSections?.includes("render")
				? [
						{
							id: "shape:character-section",
							type: "character-section",
							x: 600,
							y: 100,
							props: { w: 420, h: 360 },
						},
					]
				: []),
		],
	})),
);

const mockEditor = vi.hoisted(() => {
	let shapes: MockShape[] = [];

	const editor: MockEditor = {
		run: vi.fn((fn: () => void) => fn()),
		createShapes: vi.fn((nextShapes: MockShape[]) => {
			shapes = nextShapes.map((shape) => ({ ...shape }));
		}),
		updateShapes: vi.fn((nextShapes: MockShape[]) => {
			for (const shape of nextShapes) {
				shapes = shapes.map((current) =>
					current.id === shape.id ? { ...current, ...shape } : current,
				);
			}
		}),
		deleteShapes: vi.fn((ids: string[]) => {
			shapes = shapes.filter((s) => !ids.includes(s.id));
		}),
		getCurrentPageShapes: vi.fn(() => shapes.map((shape) => ({ ...shape }))),
		getBindingsFromShape: vi.fn(() => []),
		createBindings: vi.fn((_bindings: unknown[]) => undefined),
		deleteBindings: vi.fn(),
		getShape: vi.fn((id: string) => shapes.find((s) => s.id === id) ?? null),
		getShapeGeometry: vi.fn(() => ({ bounds: { x: 0, y: 0, w: 100, h: 100 } })),
		zoomToBounds: vi.fn(),
		getZoomLevel: vi.fn(() => 1),
		store: { listen: vi.fn(() => vi.fn()) },
		zoomToFit: vi.fn(),
		animateShape: vi.fn(),
		sideEffects: {
			registerBeforeChangeHandler: vi.fn(() => vi.fn()),
			registerAfterChangeHandler: vi.fn(() => vi.fn()),
		},
		on: vi.fn() as MockEditor["on"],
		off: vi.fn(),
		getSelectedShapeIds: vi.fn(() => []),
		centerOnPoint: vi.fn(),
		selectNone: vi.fn(),
		select: vi.fn(),
		getViewportPageBounds: vi.fn(() => ({ x: 0, y: 0, width: 1600, height: 1200 })),
		reset() {
			shapes = [];
			editor.createShapes.mockClear();
			editor.updateShapes.mockClear();
			editor.deleteShapes.mockClear();
			editor.getCurrentPageShapes.mockClear();
			editor.getBindingsFromShape.mockClear();
			editor.createBindings.mockClear();
			editor.deleteBindings.mockClear();
			editor.getShape.mockClear();
			editor.getShapeGeometry.mockClear();
			editor.zoomToBounds.mockClear();
			editor.getZoomLevel.mockClear();
			editor.zoomToFit.mockClear();
			editor.animateShape.mockClear();
			editor.store.listen.mockClear();
			editor.sideEffects.registerBeforeChangeHandler.mockClear();
			editor.sideEffects.registerAfterChangeHandler.mockClear();
			editor.on.mockClear();
			editor.off.mockClear();
			editor.getSelectedShapeIds.mockClear();
			editor.centerOnPoint.mockClear();
			editor.selectNone.mockClear();
			editor.select.mockClear();
			editor.getViewportPageBounds.mockClear();
		},
	};

	return editor;
});

vi.mock("@tanstack/react-query", () => ({
	useQueryClient: () => ({ invalidateQueries: vi.fn() }),
	useQuery: () => ({
		data: {
			id: 1,
			title: "测试项目",
			story: "一个侦探在雨夜的城市中寻找真相",
			style: null,
			summary: "创作了3个角色和8个镜头的剧本",
			video_url: null,
			status: "active",
			created_at: "2026-04-11T00:00:00Z",
			updated_at: "2026-04-11T00:00:00Z",
		},
	}),
}));

vi.mock("tldraw", async (importOriginal) => {
	const actual = await importOriginal<typeof import("tldraw")>();
	return {
		...actual,
		Tldraw: ({
			children,
			onMount,
		}: {
			children: ReactNode;
			onMount: (editor: unknown) => void;
		}) => {
			useEffect(() => {
				onMount(mockEditor);
			}, [onMount]);

			return <div>{children}</div>;
		},
	};
});

vi.mock("./CanvasToolbar", () => ({
	CanvasToolbar: () => <div data-testid="canvas-toolbar" />,
}));

vi.mock("./ShapeContextMenu", () => ({
	ShapeContextMenu: () => <div data-testid="shape-context-menu" />,
}));

vi.mock("./shapes", async (importOriginal) => {
	const actual = await importOriginal<typeof import("./shapes")>();
	return {
		...actual,
		customShapeUtils: [],
	};
});

vi.mock("~/hooks/useCanvasLayout", async (importOriginal) => {
	const actual =
		await importOriginal<typeof import("~/hooks/useCanvasLayout")>();
	return {
		...actual,
		useCanvasLayout: useCanvasLayoutMock,
	};
});

beforeEach(() => {
	mockEditor.reset();
	mockStoreState.projectVideoUrl = null;
	mockStoreState.blockingClips = null;
	vi.clearAllMocks();
});

const mockStoreState: MockEditorStoreState = {
	characters: [
		{
			id: 1,
			project_id: 1,
			name: "阿宁",
			description: "冷静的侦探",
			image_url: null,
			approval_state: "draft",
			approval_version: 1,
			approved_at: null,
			approved_name: null,
			approved_description: null,
			approved_image_url: null,
		},
	],
	shots: [
		{
			id: 11,
			project_id: 1,
			order: 1,
			description: "阿宁走进雨夜街道",
			prompt: "prompt",
			image_prompt: "image prompt",
			image_url: null,
			video_url: null,
			seed: null,
			duration: 7,
			camera: "wide",
			motion_note: "slow push in",
			scene: null,
			action: null,
			expression: null,
			lighting: null,
			dialogue: null,
			sfx: null,
			character_ids: [1],
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
		},
	],
	projectVideoUrl: null,
	projectTitle: "Store 标题",
	projectSummary: "Store 摘要",
	projectStory: "Store 故事",
	currentStage: "render",
	recoverySummary: null,
	currentRunId: 77,
	isGenerating: false,
	awaitingConfirm: false,
	blockingClips: null,
};

vi.mock("~/stores/editorStore", () => ({
	useEditorStore: () => mockStoreState,
	useShallow: <T,>(selector: (state: MockEditorStoreState) => T) => {
		const result = selector(mockStoreState);
		return () => result;
	},
}));

vi.mock("~/services/api", () => ({
	projectsApi: {
		get: () => Promise.resolve({}),
		feedback: vi.fn(() => Promise.resolve({ status: "queued", run_id: 1 })),
	},
	charactersApi: {
		approve: vi.fn(() => Promise.resolve({})),
		regenerate: vi.fn(() => Promise.resolve({})),
	},
	shotsApi: {
		approve: vi.fn(() => Promise.resolve({})),
		regenerate: vi.fn(() => Promise.resolve({})),
		update: vi.fn(() => Promise.resolve({})),
	},
	assetsApi: {
		createFromCharacter: vi.fn(() => Promise.resolve({})),
		createFromShot: vi.fn(() => Promise.resolve({})),
	},
	getStaticUrl: (path: string | null | undefined) => path,
}));

describe("InfiniteCanvas", () => {
	it("mounts independent section cards that are revealed for the current stage", async () => {
		render(<InfiniteCanvas projectId={1} />);

		await waitFor(() => {
			expect(useCanvasLayoutMock).toHaveBeenCalled();
		});

		expect(useCanvasLayoutMock.mock.calls[0]?.[0].visibleSections).toEqual([
			"plan",
			"render",
		]);
		expect(mockEditor.createShapes).toHaveBeenCalledWith(
			expect.arrayContaining([
				expect.objectContaining({
					type: "plan-section",
				}),
				expect.objectContaining({
					type: "character-section",
				}),
			]),
		);
	});

	it("passes live store story and summary to canvas layout", async () => {
		render(<InfiniteCanvas projectId={1} />);

		await waitFor(() => {
			expect(useCanvasLayoutMock).toHaveBeenCalled();
		});

		expect(useCanvasLayoutMock.mock.calls[0]?.[0].story).toBe("Store 故事");
		expect(useCanvasLayoutMock.mock.calls[0]?.[0].summary).toBe("Store 摘要");
	});

	it("uses explicit store final video state and passes blocking clips", async () => {
		mockStoreState.projectVideoUrl = null;
		mockStoreState.blockingClips = [
			{ shot_id: 1, order: 1, status: "missing", reason: "缺少视频" },
		];

		render(<InfiniteCanvas projectId={1} />);

		await waitFor(() => {
			expect(useCanvasLayoutMock).toHaveBeenCalled();
		});

		expect(useCanvasLayoutMock.mock.calls[0]?.[0].videoUrl).toBeNull();
		expect(useCanvasLayoutMock.mock.calls[0]?.[0].blockingClips).toEqual(
			mockStoreState.blockingClips,
		);
	});

	it("creates bound workflow arrows between adjacent cards", async () => {
		render(<InfiniteCanvas projectId={1} />);

		await waitFor(() => {
			expect(mockEditor.createBindings).toHaveBeenCalled();
		});

		expect(mockEditor.createShapes).toHaveBeenCalledWith(
			expect.arrayContaining([
				expect.objectContaining({
					type: "arrow",
					meta: { "openanimo-workflow-arrow": true },
				}),
			]),
		);
		expect(mockEditor.createBindings).toHaveBeenCalledWith(
			expect.arrayContaining([
				expect.objectContaining({
					fromId: expect.stringContaining("workflow-plan-section-to-character-section"),
					toId: "shape:plan-section",
					type: "arrow",
					props: expect.objectContaining({ terminal: "start" }),
				}),
				expect.objectContaining({
					fromId: expect.stringContaining("workflow-plan-section-to-character-section"),
					toId: "shape:character-section",
					type: "arrow",
					props: expect.objectContaining({ terminal: "end" }),
				}),
			]),
		);
	});

	it("does not rewrite the projected canvas when backend data is unchanged", async () => {
		const { rerender } = render(<InfiniteCanvas projectId={1} />);

		await waitFor(() => {
			expect(mockEditor.createShapes).toHaveBeenCalled();
		});

		mockEditor.createShapes.mockClear();
		mockEditor.updateShapes.mockClear();
		mockEditor.deleteShapes.mockClear();

		rerender(<InfiniteCanvas projectId={1} />);

		expect(mockEditor.createShapes).not.toHaveBeenCalled();
		expect(mockEditor.updateShapes).not.toHaveBeenCalled();
		expect(mockEditor.deleteShapes).not.toHaveBeenCalled();
	});
});
