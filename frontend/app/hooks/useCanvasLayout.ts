import { useMemo } from "react";
import { createShapeId, type TLShapePartial } from "tldraw";
import { SHAPE_TYPES } from "~/components/canvas/shapes";
import type {
	CharacterSectionShape,
	ComposeSectionShape,
	PlanSectionShape,
	StoryboardSectionShape,
} from "~/components/canvas/shapes";
import type { BlockingClip, Character, Shot, WorkflowStage } from "~/types";

type SectionKey = "plan" | "render" | "compose";
type SectionState = "draft" | "generating" | "blocked" | "complete";

interface LayoutConfig {
	startX: number;
	startY: number;
	columnGap: number;
	cardWidth: number;
}

const DEFAULT_CONFIG: LayoutConfig = {
	startX: 100,
	startY: 100,
	columnGap: 80,
	cardWidth: 420,
};

const SECTION_ORDER: SectionKey[] = ["plan", "render", "compose"];

const SECTION_LABELS: Record<SectionKey, string> = {
	plan: "规划",
	render: "渲染",
	compose: "合成",
};

const SECTION_PLACEHOLDER_TEXT: Record<SectionKey, string> = {
	plan: "等待规划生成...",
	render: "等待角色和分镜渲染生成...",
	compose: "等待视频合成...",
};

const SECTION_STATUS_LABELS: Record<SectionState, string> = {
	draft: "待生成",
	generating: "生成中",
	blocked: "待生成",
	complete: "已完成",
};

const PLAN_CARD_H = 260;
const CHARACTER_CARD_H = 360;
const STORYBOARD_CARD_H = 420;
const COMPOSE_CARD_H = 280;
const RENDER_COLUMN_EXTRA_GAP = 80;

interface UseCanvasLayoutProps {
	projectId: number;
	story: string | null;
	summary: string | null;
	characters: Character[];
	shots: Shot[];
	videoUrl: string | null;
	videoTitle: string;
	visibleSections: readonly SectionKey[];
	isGenerating: boolean;
	awaitingConfirm: boolean;
	currentRunId: number | null;
	currentStage: WorkflowStage;
	blockingClips?: BlockingClip[] | null;
	config?: Partial<LayoutConfig>;
}

function deriveSectionState(
	key: SectionKey,
	data: {
		story: string | null;
		summary: string | null;
		characters: Character[];
		shots: Shot[];
		videoUrl: string | null;
		isGenerating: boolean;
		awaitingConfirm: boolean;
		currentRunId: number | null;
		blockingClips?: BlockingClip[] | null;
	},
): SectionState {
	const isActive =
		data.isGenerating || data.awaitingConfirm || Boolean(data.currentRunId);
	const hasContent = Boolean(data.story) || Boolean(data.summary);
	const hasCharImages = data.characters.some((c) => Boolean(c.image_url));
	const hasStoryboardImg = data.shots.some((s) => Boolean(s.image_url));

	switch (key) {
		case "plan":
			return isActive && !hasContent
				? "generating"
				: hasContent
					? "complete"
					: "draft";
		case "render":
			if (data.characters.length === 0 && data.shots.length === 0)
				return "blocked";
			if (hasCharImages && hasStoryboardImg) return "complete";
			if (isActive) return "generating";
			return "draft";
		case "compose":
			if (data.blockingClips?.length) return "blocked";
			return data.videoUrl
				? "complete"
				: isActive
					? "generating"
					: data.shots.length === 0
						? "blocked"
						: "draft";
	}
}

function isPlaceholder(
	key: SectionKey,
	data: {
		story: string | null;
		summary: string | null;
		characters: Character[];
		shots: Shot[];
		videoUrl: string | null;
	},
): boolean {
	switch (key) {
		case "plan":
			return !data.story && !data.summary;
		case "render":
			return data.characters.length === 0 && data.shots.length === 0;
		case "compose":
			return !data.videoUrl;
	}
}

export type { SectionKey, SectionState };
export {
	SECTION_ORDER,
	SECTION_LABELS,
	SECTION_PLACEHOLDER_TEXT,
	SECTION_STATUS_LABELS,
};

export interface CanvasLayoutResult {
	shapes: TLShapePartial[];
}

export function useCanvasLayout({
	projectId,
	story,
	summary,
	characters,
	shots,
	videoUrl,
	videoTitle,
	visibleSections,
	isGenerating,
	awaitingConfirm,
	currentRunId,
	blockingClips,
	config: partialConfig,
}: UseCanvasLayoutProps): CanvasLayoutResult {
	const config = useMemo(
		() => ({ ...DEFAULT_CONFIG, ...partialConfig }),
		[partialConfig],
	);

	const sectionData = useMemo(
		() => ({
			story,
			summary,
			characters,
			shots,
			videoUrl,
			isGenerating,
			awaitingConfirm,
			currentRunId,
			blockingClips,
		}),
		[
			story,
			summary,
			characters,
			shots,
			videoUrl,
			isGenerating,
			awaitingConfirm,
			currentRunId,
			blockingClips,
		],
	);

	return useMemo(() => {
		const visibleSet = new Set(visibleSections);
		const sectionStates: Partial<Record<SectionKey, SectionState>> = {};
		const placeholders: Partial<Record<SectionKey, boolean>> = {};
		const statusLabels: Partial<Record<SectionKey, string>> = {};
		const placeholderTexts: Partial<Record<SectionKey, string>> = {};

		for (const section of SECTION_ORDER) {
			const state = deriveSectionState(section, sectionData);
			sectionStates[section] = state;
			placeholders[section] = isPlaceholder(section, sectionData);
			statusLabels[section] = SECTION_STATUS_LABELS[state];
			placeholderTexts[section] = SECTION_PLACEHOLDER_TEXT[section];
		}

		if (blockingClips?.length) {
			placeholderTexts.compose = blockingClips
				.map((clip) => `镜头 ${clip.order}: ${clip.reason}`)
				.join("；");
		}

		const { startX, startY, columnGap, cardWidth } = config;
		const shapes: TLShapePartial[] = [];
		const planX = startX;
		const renderX = startX + cardWidth + columnGap;
		const composeX = startX + (cardWidth + columnGap) * 2;

		if (visibleSet.has("plan")) {
			shapes.push({
				id: createShapeId("plan-section"),
				type: SHAPE_TYPES.PLAN_SECTION,
				x: planX,
				y: startY,
				props: {
					w: cardWidth,
					h: PLAN_CARD_H,
					projectId,
					story: story || "",
					summary: summary || "",
					characters,
					shots,
					sectionState: sectionStates.plan ?? "draft",
					placeholder: placeholders.plan ?? true,
					statusLabel: statusLabels.plan ?? SECTION_STATUS_LABELS.draft,
					placeholderText:
						placeholderTexts.plan ?? SECTION_PLACEHOLDER_TEXT.plan,
				},
			} satisfies TLShapePartial<PlanSectionShape>);
		}

		if (visibleSet.has("render")) {
			const characterRows = Math.max(1, Math.ceil(characters.length / 2));
			const characterHeight = Math.max(
				CHARACTER_CARD_H,
				140 + characterRows * 220,
			);
			const shotRows = Math.max(1, Math.ceil(shots.length / 2));
			const shotHeight = Math.max(STORYBOARD_CARD_H, 150 + shotRows * 230);
			const characterY = startY;
			const shotY = characterY + characterHeight + RENDER_COLUMN_EXTRA_GAP;

			shapes.push({
				id: createShapeId("character-section"),
				type: SHAPE_TYPES.CHARACTER_SECTION,
				x: renderX,
				y: characterY,
				props: {
					w: cardWidth,
					h: characterHeight,
					characters,
					sectionTitle: "角色设定",
					sectionState: sectionStates.render ?? "draft",
					placeholder: characters.length === 0,
					statusLabel: statusLabels.render ?? SECTION_STATUS_LABELS.draft,
					placeholderText:
						placeholderTexts.render ?? SECTION_PLACEHOLDER_TEXT.render,
				},
			} satisfies TLShapePartial<CharacterSectionShape>);

			shapes.push({
				id: createShapeId("storyboard-section"),
				type: SHAPE_TYPES.STORYBOARD_SECTION,
				x: renderX,
				y: shotY,
				props: {
					w: cardWidth,
					h: shotHeight,
					shots,
					sectionTitle: "分镜画面",
					sectionState: sectionStates.render ?? "draft",
					placeholder: shots.length === 0,
					statusLabel: statusLabels.render ?? SECTION_STATUS_LABELS.draft,
					placeholderText:
						placeholderTexts.render ?? SECTION_PLACEHOLDER_TEXT.render,
				},
			} satisfies TLShapePartial<StoryboardSectionShape>);
		}

		if (visibleSet.has("compose")) {
			shapes.push({
				id: createShapeId("compose-section"),
				type: SHAPE_TYPES.COMPOSE_SECTION,
				x: composeX,
				y: startY,
				props: {
					w: cardWidth,
					h: COMPOSE_CARD_H,
					projectId,
					videoUrl: videoUrl || "",
					videoTitle,
					downloadUrl: `/api/v1/projects/${projectId}/final-video`,
					sectionState: sectionStates.compose ?? "draft",
					placeholder: placeholders.compose ?? true,
					statusLabel: statusLabels.compose ?? SECTION_STATUS_LABELS.draft,
					placeholderText:
						placeholderTexts.compose ?? SECTION_PLACEHOLDER_TEXT.compose,
				},
			} satisfies TLShapePartial<ComposeSectionShape>);
		}

		return { shapes };
	}, [
		visibleSections,
		sectionData,
		blockingClips,
		config,
		projectId,
		story,
		summary,
		characters,
		shots,
		videoUrl,
		videoTitle,
	]);
}
