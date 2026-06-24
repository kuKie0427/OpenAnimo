import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
	createShapeId,
	type Editor,
	type TLComponents,
	Tldraw,
	type TLShape,
	type TLShapeId,
	type TLShapePartial,
} from "tldraw";
import "tldraw/tldraw.css";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCanvasLayout } from "~/hooks/useCanvasLayout";
import type { SectionKey } from "~/hooks/useCanvasLayout";
import { SECTION_ORDER } from "~/hooks/useCanvasLayout";
import {
	getStaticUrl,
	projectsApi,
	assetsApi,
	charactersApi,
	shotsApi,
} from "~/services/api";
import { useEditorStore, useShallow } from "~/stores/editorStore";
import { CanvasToolbar } from "./CanvasToolbar";
import { canvasEvents, type CanvasEvents } from "./canvasEvents";
import { ImagePreviewModal, VideoPreviewModal } from "./PreviewModals";
import { customShapeUtils } from "./shapes";
import { getPipelineStageIndex } from "~/utils/pipeline";
import { toast } from "~/utils/toast";
import { ApiError } from "~/types/errors";
import { ShapeContextMenu } from "./ShapeContextMenu";
import { CanvasBreadcrumb } from "./CanvasBreadcrumb";
import { CanvasSearch } from "./CanvasSearch";
import { CanvasMinimap } from "./CanvasMinimap";
import { CanvasQuickActions } from "./CanvasQuickActions";
import { useViewStore } from "~/stores/viewStore";

type CanvasShapeType = "plan-section" | "character-section" | "storyboard-section" | "compose-section";

interface InfiniteCanvasProps {
	projectId: number;
}

const components: TLComponents = {
	PageMenu: null,
	MainMenu: null,
	Toolbar: null,
	StylePanel: null,
	NavigationPanel: undefined,
	Minimap: undefined,
	HelpMenu: null,
	DebugPanel: null,
	DebugMenu: null,
	MenuPanel: null,
	TopPanel: null,
	SharePanel: null,
	ActionsMenu: null,
	QuickActions: null,
	KeyboardShortcutsDialog: null,
	HelperButtons: null,
	ZoomMenu: null,
	ContextMenu: null,
};

const PROJECTED_SHAPE_TYPES = new Set([
	"plan-section",
	"character-section",
	"storyboard-section",
	"compose-section",
]);

const STALE_SHAPE_TYPES = new Set([
	"connector",
	"ConnectorShape",
	"storyboard-board",
	"script-section",
	"video-section",
]);

const WORKFLOW_ARROW_META = "openanimo-workflow-arrow";
const MANUAL_POSITION_META = "manualPosition";
const CARD_PADDING = 32;

interface ShapeBounds {
	x: number;
	y: number;
	w: number;
	h: number;
}

function getShapeSize(shape: TLShapePartial | TLShape): { w: number; h: number } {
	const props = shape.props as { w?: number; h?: number } | undefined;
	return {
		w: props?.w ?? 420,
		h: props?.h ?? 260,
	};
}

function toBounds(shape: TLShapePartial | TLShape): ShapeBounds {
	const size = getShapeSize(shape);
	return {
		x: shape.x ?? 0,
		y: shape.y ?? 0,
		w: size.w,
		h: size.h,
	};
}

function boundsOverlap(a: ShapeBounds, b: ShapeBounds): boolean {
	return !(
		a.x + a.w + CARD_PADDING <= b.x ||
		b.x + b.w + CARD_PADDING <= a.x ||
		a.y + a.h + CARD_PADDING <= b.y ||
		b.y + b.h + CARD_PADDING <= a.y
	);
}

function isManualShape(
	shape: TLShape | TLShapePartial | undefined,
	lastProjected?: { x: number; y: number },
): boolean {
	if (!shape) return false;
	if (shape.meta?.[MANUAL_POSITION_META] === true) return true;
	if (!lastProjected) return false;
	return shape.x !== lastProjected.x || shape.y !== lastProjected.y;
}

function avoidCollisions(
	desired: TLShapePartial,
	occupied: ShapeBounds[],
): TLShapePartial {
	let next = { ...desired };
	let guard = 0;
	while (occupied.some((bounds) => boundsOverlap(toBounds(next), bounds))) {
		const size = getShapeSize(next);
		next = { ...next, y: (next.y ?? 0) + size.h + CARD_PADDING };
		guard += 1;
		if (guard > 50) break;
	}
	occupied.push(toBounds(next));
	return next;
}

function resolveShapeLayout(
	desiredShapes: TLShapePartial[],
	existingShapes: TLShape[],
	lastProjected: Map<string, { x: number; y: number }>,
): TLShapePartial[] {
	const existingMap = new Map(existingShapes.map((shape) => [shape.id, shape]));
	const occupied = existingShapes
		.filter((shape) => !PROJECTED_SHAPE_TYPES.has(shape.type))
		.map(toBounds);
	const resolved: TLShapePartial[] = [];

	for (const desired of desiredShapes) {
		const existing = existingMap.get(desired.id);
		const manual = isManualShape(existing, lastProjected.get(desired.id));
		const next = existing && manual
			? ({ ...desired, x: existing.x, y: existing.y, meta: existing.meta } as TLShapePartial)
			: avoidCollisions(desired, occupied);
		if (manual) occupied.push(toBounds(next));
		resolved.push(next);
	}

	return resolved;
}

function shapesEqual(existing: TLShape, desired: TLShapePartial): boolean {
	return (
		existing.type === desired.type &&
		existing.x === (desired.x ?? 0) &&
		existing.y === (desired.y ?? 0) &&
		JSON.stringify(existing.props ?? {}) === JSON.stringify(desired.props ?? {}) &&
		JSON.stringify(existing.meta ?? {}) === JSON.stringify(desired.meta ?? {})
	);
}

function errorMessage(error: unknown, fallback: string): string {
	if (error instanceof ApiError) return error.message;
	if (error instanceof Error) return error.message;
	return fallback;
}

function workflowArrowId(fromId: TLShapeId, toId: TLShapeId): TLShapeId {
	return createShapeId(`workflow-${fromId.replace("shape:", "")}-to-${toId.replace("shape:", "")}`);
}

function syncWorkflowArrows(editor: Editor, cardShapes: TLShapePartial[]) {
	const orderedCards = cardShapes.filter((shape) =>
		PROJECTED_SHAPE_TYPES.has(shape.type ?? ""),
	);
	const desiredPairs = orderedCards.slice(0, -1).map((shape, index) => ({
		fromId: shape.id as TLShapeId,
		toId: orderedCards[index + 1]?.id as TLShapeId,
	}));
	const desiredArrowIds = new Set(
		desiredPairs.map((pair) => workflowArrowId(pair.fromId, pair.toId)),
	);
	const currentArrows = editor
		.getCurrentPageShapes()
		.filter(
			(shape) =>
				shape.type === "arrow" &&
				shape.meta?.[WORKFLOW_ARROW_META] === true,
		);
	const staleArrowIds = currentArrows
		.filter((shape) => !desiredArrowIds.has(shape.id))
		.map((shape) => shape.id);

	if (staleArrowIds.length > 0) {
		editor.deleteShapes(staleArrowIds);
	}

	const existingArrowIds = new Set(
		currentArrows.map((shape) => shape.id).filter((id) => !staleArrowIds.includes(id)),
	);
	const arrowsToCreate: TLShapePartial[] = [];
	const bindingsToCreate: Parameters<Editor["createBindings"]>[0] = [];

	for (const [index, pair] of desiredPairs.entries()) {
		const arrowId = workflowArrowId(pair.fromId, pair.toId);
		if (existingArrowIds.has(arrowId)) continue;
		arrowsToCreate.push({
			id: arrowId,
			type: "arrow",
			x: 0,
			y: 0,
			meta: { [WORKFLOW_ARROW_META]: true },
			props: {
				kind: "arc",
				bend: index % 2 === 0 ? 48 : -48,
				color: "blue",
				dash: "draw",
				fill: "none",
				labelColor: "black",
				size: "m",
				arrowheadStart: "none",
				arrowheadEnd: "arrow",
				font: "draw",
				start: { x: 0, y: 0 },
				end: { x: 160, y: 0 },
				labelPosition: 0.5,
				scale: 1,
				elbowMidPoint: 0.5,
				richText: { type: "doc", content: [] },
			},
		});
		bindingsToCreate.push(
			{
				fromId: arrowId,
				toId: pair.fromId,
				type: "arrow",
				props: {
					terminal: "start",
					normalizedAnchor: { x: 0.5, y: 0.5 },
					isExact: false,
					isPrecise: false,
					snap: "none",
				},
			},
			{
				fromId: arrowId,
				toId: pair.toId,
				type: "arrow",
				props: {
					terminal: "end",
					normalizedAnchor: { x: 0.5, y: 0.5 },
					isExact: false,
					isPrecise: false,
					snap: "none",
				},
			},
		);
	}

	if (arrowsToCreate.length > 0) editor.createShapes(arrowsToCreate);
	if (bindingsToCreate.length > 0) editor.createBindings(bindingsToCreate);
}

export function InfiniteCanvas({ projectId }: InfiniteCanvasProps) {
	const queryClient = useQueryClient();
	const editorRef = useRef<Editor | null>(null);
	const [isInitialized, setIsInitialized] = useState(false);
	const lastAppliedShapesSignatureRef = useRef<string | null>(null);
	const shapesRef = useRef<TLShapePartial[]>([]);
	const shapesSignatureRef = useRef("");
	const projectedPositionRef = useRef(new Map<string, { x: number; y: number }>());

	const {
		characters,
		shots,
		projectVideoUrl,
		projectTitle,
		projectSummary,
		projectStory,
		currentStage,
		isGenerating,
		awaitingConfirm,
		recoverySummary,
		currentRunId,
		blockingClips,
		updateCharacter,
		updateShot,
	} = useEditorStore(
		useShallow((s) => ({
			characters: s.characters,
			shots: s.shots,
			projectVideoUrl: s.projectVideoUrl,
			projectTitle: s.projectTitle,
			projectSummary: s.projectSummary,
			projectStory: s.projectStory,
			currentStage: s.currentStage,
			isGenerating: s.isGenerating,
			awaitingConfirm: s.awaitingConfirm,
			recoverySummary: s.recoverySummary,
			currentRunId: s.currentRunId,
			blockingClips: s.blockingClips,
			updateCharacter: s.updateCharacter,
			updateShot: s.updateShot,
		})),
	);

	const {
		isSearchOpen, setSearchOpen,
		isMinimapVisible,
		selectedShapeIds, setSelectedShapeIds,
		setSearchQuery,
		searchResults, setSearchResults,
		currentSearchIndex, setCurrentSearchIndex,
	} = useViewStore();

	const { data: project } = useQuery({
		queryKey: ["project", projectId],
		queryFn: () => projectsApi.get(projectId),
	});

	const [previewImage, setPreviewImage] = useState<{
		src: string;
		alt: string;
	} | null>(null);
	const [previewVideo, setPreviewVideo] = useState<{
		src: string;
		title: string;
	} | null>(null);

	// Force re-render for minimap on editor changes
	const [, forceRender] = useState(0);

	const rawVideoUrl = projectVideoUrl;
	const finalVideoUrl = rawVideoUrl ? getStaticUrl(rawVideoUrl) : null;
	const story = projectStory ?? project?.story ?? null;
	const summary = projectSummary ?? project?.summary ?? null;
	const videoTitle = projectTitle ?? project?.title ?? "最终视频";

	const currentStageIndex = useMemo(
		() => getPipelineStageIndex(recoverySummary?.current_stage ?? currentStage),
		[recoverySummary, currentStage],
	);

	const visibleSections = useMemo((): SectionKey[] => {
		const sectionIndex = Math.max(
			currentStageIndex >= 0 ? currentStageIndex : 0,
			recoverySummary?.preserved_stages?.reduce(
				(max, s) => Math.max(max, getPipelineStageIndex(s)),
				0,
			) ?? 0,
		);

		return SECTION_ORDER.filter((section) => {
			if (section === "plan") return true;
			if (section === "render")
				return (
					characters.length > 0 ||
					shots.some((s) => Boolean(s.image_url)) ||
					sectionIndex >= 1
				);
			if (section === "compose")
				return (
					Boolean(finalVideoUrl) ||
					shots.some((s) => Boolean(s.video_url)) ||
					sectionIndex >= 2
				);
			return false;
		});
	}, [characters, shots, finalVideoUrl, currentStageIndex, recoverySummary]);

	const layout = useCanvasLayout({
		projectId,
		story,
		summary,
		characters,
		shots,
		videoUrl: finalVideoUrl,
		videoTitle,
		visibleSections,
		isGenerating,
		awaitingConfirm,
		currentRunId,
		currentStage,
		blockingClips,
	});

	const shapesSignature = useMemo(() => JSON.stringify(layout.shapes), [layout.shapes]);
	shapesRef.current = layout.shapes;
	shapesSignatureRef.current = shapesSignature;

	const invalidateProjectData = useCallback(() => {
		queryClient.invalidateQueries({ queryKey: ["project", projectId] });
		queryClient.invalidateQueries({ queryKey: ["projects"] });
		queryClient.invalidateQueries({ queryKey: ["characters", projectId] });
		queryClient.invalidateQueries({ queryKey: ["shots", projectId] });
	}, [projectId, queryClient]);

	const handleShapeAction = useCallback(
		(data: CanvasEvents["shape-action"]) => {
			if (data.action === "history") {
				canvasEvents.emit("version-history", {
					entityType: data.entityType,
					entityId: data.entityId,
				});
				return;
			}

			if (data.action === "add-to-assets" && data.entityId) {
				const request = data.entityType === "character"
					? assetsApi.createFromCharacter(data.entityId)
					: assetsApi.createFromShot(data.entityId);
				request
					.then(() => {
						queryClient.invalidateQueries({ queryKey: ["assets"] });
						toast.success({ title: "资产库", message: data.entityType === "character" ? "已添加到资产库" : "已保存为场景资产" });
					})
					.catch((error) => toast.error({ title: "资产库", message: errorMessage(error, "保存失败") }));
				return;
			}

			if (data.action === "approve") {
				const request = data.entityType === "character"
					? charactersApi.approve(data.entityId)
					: shotsApi.approve(data.entityId);
				request
					.then((entity) => {
						if (data.entityType === "character") updateCharacter(entity as typeof characters[number]);
						else updateShot(entity as typeof shots[number]);
						invalidateProjectData();
						toast.success({ title: "审批", message: "已批准" });
					})
					.catch((error) => toast.error({ title: "审批", message: errorMessage(error, "批准失败") }));
				return;
			}

			if (data.action === "regenerate") {
				const request = data.entityType === "character"
					? charactersApi.regenerate(data.entityId)
					: shotsApi.regenerate(data.entityId, "image");
				request
					.then(() => {
						invalidateProjectData();
						toast.success({ title: "重新生成", message: "任务已启动" });
					})
					.catch((error) => toast.error({ title: "重新生成", message: errorMessage(error, "启动失败") }));
				return;
			}

			if (data.action === "edit" && data.entityType === "shot" && data.shotPatch) {
				shotsApi.update(data.entityId, data.shotPatch)
					.then((shot) => {
						updateShot(shot);
						invalidateProjectData();
						toast.success({ title: "镜头", message: "已保存修改" });
					})
					.catch((error) => toast.error({ title: "镜头", message: errorMessage(error, "保存失败") }));
				return;
			}

			if (data.action === "edit") {
				const content = data.feedbackContent?.trim();
				if (!content) return;
				projectsApi.feedback(projectId, content, currentRunId ?? undefined, data.feedbackType, data.entityType, data.entityId)
					.then(() => {
						invalidateProjectData();
						toast.success({ title: "修改意见", message: "已提交" });
					})
					.catch((error) => toast.error({ title: "修改意见", message: errorMessage(error, "提交失败") }));
			}
		},
		[projectId, currentRunId, queryClient, updateCharacter, updateShot, invalidateProjectData],
	);

	const handleSearch = useCallback((query: string) => {
		setSearchQuery(query);
		const editor = editorRef.current;
		if (!editor) return;
		const allShapes = editor.getCurrentPageShapes();
		const filtered = allShapes
			.filter((s) => s.type !== "arrow")
			.filter((s) => {
				if (!query) return true;
				const nameMatch = (s.props as { name?: string } | undefined)?.name?.toLowerCase()?.includes(query.toLowerCase());
				const idMatch = s.id.toLowerCase().includes(query.toLowerCase());
				return nameMatch || idMatch;
			})
			.map((s) => s.id);
		setSearchResults(filtered.map((id) => id.toString()));
		setCurrentSearchIndex(0);
	}, [setSearchQuery, setSearchResults, setCurrentSearchIndex]);

	const handleFilterType = useCallback((type: CanvasShapeType | "all") => {
		const editor = editorRef.current;
		if (!editor) return;
		const allShapes = editor.getCurrentPageShapes();
		const filtered = type === "all"
			? allShapes.filter((s) => s.type !== "arrow")
			: allShapes.filter((s) => s.type === type);
		setSearchResults(filtered.map((s) => s.id.toString()));
		setCurrentSearchIndex(0);
	}, [setSearchResults, setCurrentSearchIndex]);

	useEffect(() => {
		const unsubscribers = [
			canvasEvents.on("preview-image", setPreviewImage),
			canvasEvents.on("preview-video", setPreviewVideo),
			canvasEvents.on("shape-action", handleShapeAction),
		];
		return () => {
			unsubscribers.forEach((unsub) => unsub());
		};
	}, [handleShapeAction]);

	useEffect(() => {
		const editor = editorRef.current;
		if (!editor) return;
		const handleChange = () => {
			const ids = editor.getSelectedShapeIds();
			setSelectedShapeIds(ids.map((id) => id.toString()));
		};
		editor.on("change", handleChange);
		return () => {
			editor.off("change", handleChange);
		};
	}, [editorRef, setSelectedShapeIds]);

	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			const editor = editorRef.current;
			if (!editor) return;

			const target = e.target as HTMLElement;
			if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) return;

			// Cmd+F / Ctrl+F — open search
			if ((e.metaKey || e.ctrlKey) && e.key === "f") {
				e.preventDefault();
				setSearchOpen(true);
				return;
			}

			// Cmd+0 / Ctrl+0 — fit to content
			if ((e.metaKey || e.ctrlKey) && e.key === "0") {
				e.preventDefault();
				editor.zoomToFit({ animation: { duration: 300 } });
				return;
			}

			// Cmd+G / Ctrl+G — next search result
			if ((e.metaKey || e.ctrlKey) && e.key === "g" && !e.shiftKey) {
				e.preventDefault();
				if (searchResults.length > 0) {
					const nextIndex = (currentSearchIndex + 1) % searchResults.length;
					const shapeId = searchResults[nextIndex];
					const shape = editor.getShape(shapeId as TLShapeId);
					if (shape) {
						const props = shape.props as { w?: number; h?: number } | undefined;
						editor.centerOnPoint(
							{ x: shape.x + (props?.w ?? 420) / 2, y: shape.y + (props?.h ?? 260) / 2 },
							{ animation: { duration: 300 } },
						);
						editor.select(shapeId as TLShapeId);
						setCurrentSearchIndex(nextIndex);
					}
				}
				return;
			}

			// Cmd+Shift+G / Ctrl+Shift+G — previous search result
			if ((e.metaKey || e.ctrlKey) && e.key === "g" && e.shiftKey) {
				e.preventDefault();
				if (searchResults.length > 0) {
					const prevIndex = (currentSearchIndex - 1 + searchResults.length) % searchResults.length;
					const shapeId = searchResults[prevIndex];
					const shape = editor.getShape(shapeId as TLShapeId);
					if (shape) {
						const props = shape.props as { w?: number; h?: number } | undefined;
						editor.centerOnPoint(
							{ x: shape.x + (props?.w ?? 420) / 2, y: shape.y + (props?.h ?? 260) / 2 },
							{ animation: { duration: 300 } },
						);
						editor.select(shapeId as TLShapeId);
						setCurrentSearchIndex(prevIndex);
					}
				}
				return;
			}

			// Escape — close search / deselect
			if (e.key === "Escape") {
				if (isSearchOpen) {
					setSearchOpen(false);
					return;
				}
				editor.selectNone();
				return;
			}

			// Delete / Backspace — delete selected shapes
			if (e.key === "Delete" || e.key === "Backspace") {
				const selectedIds = editor.getSelectedShapeIds();
				if (selectedIds.length > 0) {
					e.preventDefault();
					editor.deleteShapes(selectedIds);
				}
			}
		};

		document.addEventListener("keydown", handleKeyDown);
		return () => document.removeEventListener("keydown", handleKeyDown);
	}, [editorRef, isSearchOpen, setSearchOpen, setCurrentSearchIndex, searchResults, currentSearchIndex]);

	// Force re-render for minimap on editor changes
	useEffect(() => {
		const editor = editorRef.current;
		if (!editor) return;
		const handleChange = () => forceRender((n) => n + 1);
		editor.on("change", handleChange);
		return () => {
			editor.off("change", handleChange);
		};
	}, [editorRef]);

	const handleMount = useCallback((editor: Editor) => {
		editorRef.current = editor;


		// Delete any stale shapes from previous layout architectures
		const allShapes = editor.getCurrentPageShapes();
		const staleShapeIds = allShapes
			.filter((s) => STALE_SHAPE_TYPES.has(s.type))
			.map((s) => s.id);
		if (staleShapeIds.length > 0) {
			editor.deleteShapes(staleShapeIds);
		}

		const currentShapes = shapesRef.current;
		const currentSignature = shapesSignatureRef.current;
		const resolvedShapes = resolveShapeLayout(
			currentShapes,
			editor.getCurrentPageShapes(),
			projectedPositionRef.current,
		);

		if (resolvedShapes.length > 0) {
			editor.run(() => {
				editor.createShapes(resolvedShapes);
				syncWorkflowArrows(editor, resolvedShapes);
			});
			projectedPositionRef.current = new Map(
				resolvedShapes.map((shape) => [
					shape.id,
					{ x: shape.x ?? 0, y: shape.y ?? 0 },
				]),
			);
			lastAppliedShapesSignatureRef.current = currentSignature;
			setTimeout(() => {
				editor.zoomToFit({ animation: { duration: 300 } });
			}, 100);
		} else {
			lastAppliedShapesSignatureRef.current = currentSignature;
		}

		setIsInitialized(true);
	}, []);

	// Sync projected cards when backend data changes; manual card positions stay user-owned.
	useEffect(() => {
		const editor = editorRef.current;
		if (!editor || !isInitialized) return;
		if (lastAppliedShapesSignatureRef.current === shapesSignature) return;

		const desiredShapes = layout.shapes;
		if (desiredShapes.length === 0) return;

		const existingShapes = editor.getCurrentPageShapes();
		const desiredIds = new Set(desiredShapes.map((s) => s.id));
		const resolvedShapes = resolveShapeLayout(
			desiredShapes,
			existingShapes,
			projectedPositionRef.current,
		);
		const existingMap = new Map(existingShapes.map((s) => [s.id, s]));

		editor.run(() => {
			const toDelete = existingShapes.filter((s) => {
				if (s.type === "arrow" && s.meta?.[WORKFLOW_ARROW_META] === true) {
					return false;
				}
				return STALE_SHAPE_TYPES.has(s.type) || !desiredIds.has(s.id);
			});
			if (toDelete.length > 0) {
				editor.deleteShapes(toDelete.map((s) => s.id));
			}

			const toCreate: TLShapePartial[] = [];
			const toUpdate: TLShapePartial[] = [];
			for (const desired of resolvedShapes) {
				if (!existingMap.has(desired.id)) {
					toCreate.push(desired);
				} else {
					const existing = existingMap.get(desired.id);
					if (existing && !shapesEqual(existing, desired)) toUpdate.push(desired);
				}
			}

			if (toCreate.length > 0) editor.createShapes(toCreate);
			if (toUpdate.length > 0) editor.updateShapes(toUpdate);
			syncWorkflowArrows(editor, resolvedShapes);
		});

		projectedPositionRef.current = new Map(
			resolvedShapes.map((shape) => [
				shape.id,
				{ x: shape.x ?? 0, y: shape.y ?? 0 },
			]),
		);

		// If this is the first time we're adding shapes, zoom to fit
		if (existingShapes.length === 0 && desiredShapes.length > 0) {
			setTimeout(() => {
				editor.zoomToFit({ animation: { duration: 400 } });
			}, 100);
		}

		lastAppliedShapesSignatureRef.current = shapesSignature;
	}, [layout, shapesSignature, isInitialized]);

	return (
		<>
			<div className="h-full w-full infinite-canvas-container relative">
				<Tldraw
					shapeUtils={customShapeUtils}
					components={components}
					onMount={handleMount}
					persistenceKey="openanimo-canvas-v12"
				>
					<CanvasToolbar projectId={projectId} />
					<ShapeContextMenu />
				</Tldraw>

				<CanvasBreadcrumb
					projectId={projectId}
					currentStage={currentStage}
					selectedShapeId={selectedShapeIds[0]}
					onStageClick={(stage) => {
						useEditorStore.getState().setCurrentStage(stage);
					}}
					onShapeClick={(shapeId) => {
						const editor = editorRef.current;
						if (editor) {
							editor.select(shapeId as TLShapeId);
						}
					}}
					onFitToContent={() => {
						editorRef.current?.zoomToFit({ animation: { duration: 300 } });
					}}
				/>

				{isSearchOpen && (
					<CanvasSearch
						onSearch={handleSearch}
						onFilterType={handleFilterType}
						resultCount={searchResults.length}
						currentIndex={currentSearchIndex}
						onNavigateResult={(direction) => {
							if (searchResults.length === 0) return;
							const nextIndex = direction === "next"
								? (currentSearchIndex + 1) % searchResults.length
								: (currentSearchIndex - 1 + searchResults.length) % searchResults.length;
							const shapeId = searchResults[nextIndex];
							const editor = editorRef.current;
							if (editor) {
								const shape = editor.getShape(shapeId as TLShapeId);
								if (shape) {
									const props = shape.props as { w?: number; h?: number } | undefined;
									editor.centerOnPoint(
										{ x: shape.x + (props?.w ?? 420) / 2, y: shape.y + (props?.h ?? 260) / 2 },
										{ animation: { duration: 300 } },
									);
									editor.select(shapeId as TLShapeId);
								}
							}
							setCurrentSearchIndex(nextIndex);
						}}
					/>
				)}

				{isMinimapVisible && (
					<CanvasMinimap
						shapes={(() => {
							const editor = editorRef.current;
							if (!editor) return [];
							return editor.getCurrentPageShapes()
								.filter((s) => s.type !== "arrow")
								.map((s) => {
									const props = s.props as { w?: number; h?: number } | undefined;
									return {
										id: s.id.toString(),
										x: s.x,
										y: s.y,
										width: props?.w ?? 420,
										height: props?.h ?? 260,
										type: s.type,
									};
								});
						})()}
						viewport={(() => {
							const editor = editorRef.current;
							if (!editor) return { x: 0, y: 0, width: 800, height: 600 };
							const bounds = editor.getViewportPageBounds();
							return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
						})()}
						canvasBounds={(() => {
							const editor = editorRef.current;
							if (!editor) return { width: 1200, height: 900 };
							const allShapes = editor.getCurrentPageShapes();
							if (allShapes.length === 0) return { width: 1200, height: 900 };
							let maxX = 0;
							let maxY = 0;
							for (const s of allShapes) {
								const props = s.props as { w?: number; h?: number } | undefined;
								const w = props?.w ?? 420;
								const h = props?.h ?? 260;
								if (s.x + w > maxX) maxX = s.x + w;
								if (s.y + h > maxY) maxY = s.y + h;
							}
							return { width: Math.max(maxX, 1200), height: Math.max(maxY, 900) };
						})()}
						onNavigate={(x, y) => {
							editorRef.current?.centerOnPoint({ x, y }, { animation: { duration: 300 } });
						}}
					/>
				)}

				<CanvasQuickActions
					selectedCount={selectedShapeIds.length}
					onAlignH={() => {}}
					onAlignV={() => {}}
					onDistributeH={() => {}}
					onDistributeV={() => {}}
					onGroup={() => {}}
					onUngroup={() => {}}
					onDelete={() => {
						const editor = editorRef.current;
						if (editor) {
							const ids = editor.getSelectedShapeIds();
							if (ids.length > 0) editor.deleteShapes(ids);
						}
					}}
				/>
			</div>

			{previewImage && (
				<ImagePreviewModal
					src={previewImage.src}
					alt={previewImage.alt}
					onClose={() => setPreviewImage(null)}
				/>
			)}

			{previewVideo && (
				<VideoPreviewModal
					src={previewVideo.src}
					title={previewVideo.title}
					onClose={() => setPreviewVideo(null)}
					showDownload={false}
				/>
			)}
		</>
	);
}
