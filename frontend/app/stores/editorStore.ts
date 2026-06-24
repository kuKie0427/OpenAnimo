import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { useShallow } from "zustand/react/shallow";
import type {
	AgentMessage,
	BlockingClip,
	Character,
	CritiqueReviewEventData,
	EntityDecision,
	ProjectProviderSettings,
	RecoveryControlRead,
	RecoverySummaryRead,
	RunAwaitingConfirmEventData,
	Shot,
	StoryOutline,
	WorkflowStage,
} from "~/types";

export type RunMode = "manual" | "yolo";

export const ALL_GATES = [
	"outline", "characters", "shots",
	"character_images", "shot_images", "compose",
	"critique_characters", "critique_shots",
] as const;
export type GateName = typeof ALL_GATES[number];

export const GATE_LABELS: Record<GateName, string> = {
	outline: "大纲审批",
	characters: "角色规划审批",
	shots: "分镜规划审批",
	character_images: "角色图片审批",
	shot_images: "分镜图片审批",
	compose: "视频合成审批",
	critique_characters: "Critic 角色审查",
	critique_shots: "Critic 分镜审查",
};

interface EditorState {
	selectedShotId: number | null;
	selectedCharacterId: number | null;
	highlightedMessageIndex: number | null;
	isGenerating: boolean;
	currentStage: WorkflowStage;
	currentAgent: string | null;
	progress: number;
	messages: AgentMessage[];
	recoveryControl: RecoveryControlRead | null;
	recoverySummary: RecoverySummaryRead | null;
	recoveryGate: RunAwaitingConfirmEventData | null;
	awaitingConfirm: boolean;
	awaitingAgent: string | null;
	currentRunId: number | null;
	currentRunProviderSnapshot: ProjectProviderSettings | null;
	runMode: RunMode;
	gateModes: Set<GateName>;
	characters: Character[];
	shots: Shot[];
	projectVideoUrl: string | null;
	projectStatus: string | null;
	projectUpdatedAt: number | null;
	shotSyncCompleted: number | null;
	projectTitle: string | null;
	projectSummary: string | null;
	projectStoryOutline: StoryOutline | null;
	projectVisualBible: string | null;
	projectOutlineApproved: boolean;
	projectStory: string | null;
	projectStyle: string | null;
	projectTargetShotCount: number | null;
	projectCharacterHints: string[] | null;
	projectCreationMode: string | null;
	projectReferenceImages: string[] | null;
	projectExports: string[] | null;
	projectProviderSettings: ProjectProviderSettings | null;
	projectUniverseId: number | null;
	projectChapterNumber: number | null;
	projectChapterTitle: string | null;
	blockingClips: BlockingClip[] | null;
	// Critic override state
	critiqueReviewCard: CritiqueReviewEventData | null;
	critiqueOverrides: Record<number, boolean>;
	// Entity approval state
	entityApprovalDecisions: EntityDecision[];

	setSelectedShot: (id: number | null) => void;
	setSelectedCharacter: (id: number | null) => void;
	setHighlightedMessage: (index: number | null) => void;
	setGenerating: (isGenerating: boolean) => void;
	setCurrentStage: (stage: WorkflowStage) => void;
	setCurrentAgent: (agent: string | null) => void;
	setProgress: (progress: number) => void;
	addMessage: (message: AgentMessage) => void;
	setMessages: (messages: AgentMessage[]) => void;
	clearMessages: () => void;
	setRecoveryControl: (control: RecoveryControlRead | null) => void;
	setRecoverySummary: (summary: RecoverySummaryRead | null) => void;
	setRecoveryGate: (gate: RunAwaitingConfirmEventData | null) => void;
	setCharacters: (characters: Character[]) => void;
	setShots: (shots: Shot[]) => void;
	setProjectVideoUrl: (url: string | null) => void;
	setProjectStatus: (status: string | null) => void;
	setProjectUpdatedAt: (timestamp: number) => void;
	setShotSyncCompleted: (timestamp: number) => void;
	setProjectTitle: (title: string | null) => void;
	setProjectSummary: (summary: string | null) => void;
	setProjectStoryOutline: (outline: StoryOutline | null) => void;
	setProjectVisualBible: (visualBible: string | null) => void;
	setProjectOutlineApproved: (approved: boolean) => void;
	setProjectStory: (story: string | null) => void;
	setProjectStyle: (style: string | null) => void;
	setProjectTargetShotCount: (count: number | null) => void;
	setProjectCharacterHints: (hints: string[] | null) => void;
	setProjectCreationMode: (mode: string | null) => void;
	setProjectReferenceImages: (images: string[] | null) => void;
	setProjectExports: (exports: string[] | null) => void;
	setProjectProviderSettings: (settings: ProjectProviderSettings | null) => void;
	setProjectUniverseId: (id: number | null) => void;
	setProjectChapterNumber: (chapter: number | null) => void;
	setProjectChapterTitle: (title: string | null) => void;
	setBlockingClips: (clips: BlockingClip[] | null) => void;
	setCritiqueReviewCard: (data: CritiqueReviewEventData | null) => void;
	setCritiqueOverride: (entityId: number, shouldRegenerate: boolean) => void;
	clearCritiqueReview: () => void;
	setEntityApprovalDecisions: (decisions: EntityDecision[]) => void;
	clearEntityApprovalDecisions: () => void;
	setAwaitingConfirm: (
		awaiting: boolean,
		agent?: string | null,
		runId?: number | null,
	) => void;
	setCurrentRunId: (runId: number | null) => void;
	setCurrentRunProviderSnapshot: (
		snapshot: ProjectProviderSettings | null,
	) => void;
	setRunMode: (mode: RunMode) => void;
	setGateMode: (gate: GateName, enabled: boolean) => void;
	setGateModes: (gates: GateName[]) => void;
	resetGateModes: () => void;
	updateCharacter: (character: Character) => void;
	updateShot: (shot: Shot) => void;
	removeCharacter: (characterId: number) => void;
	removeShot: (shotId: number) => void;
	resetRunState: () => void;
	reset: () => void;
}

const initialRunState = {
	isGenerating: false,
	currentAgent: null,
	progress: 0,
	recoveryControl: null,
	recoverySummary: null,
	recoveryGate: null,
	awaitingConfirm: false,
	awaitingAgent: null,
	critiqueReviewCard: null,
	critiqueOverrides: {},
	entityApprovalDecisions: [],
	currentRunId: null,
	currentRunProviderSnapshot: null,
};

const initialState = {
	selectedShotId: null,
	selectedCharacterId: null,
	highlightedMessageIndex: null,
	currentStage: "plan" as WorkflowStage,
	runMode: "manual" as RunMode,
	gateModes: new Set<GateName>(),
	messages: [],
	characters: [],
	shots: [],
	projectVideoUrl: null,
	projectStatus: null,
	projectUpdatedAt: null,
	shotSyncCompleted: null,
	projectTitle: null,
	projectSummary: null,
	projectStoryOutline: null,
	projectVisualBible: null,
	projectOutlineApproved: false,
	projectStory: null,
	projectStyle: null,
	projectTargetShotCount: null,
	projectCharacterHints: null,
	projectCreationMode: null,
	projectReferenceImages: null,
	projectExports: null,
	projectProviderSettings: null,
	projectUniverseId: null,
	projectChapterNumber: null,
	projectChapterTitle: null,
	blockingClips: null,
	...initialRunState,
};

export const useEditorStore = create<EditorState>()(
	devtools(
		(set) => ({
			...initialState,

			setSelectedShot: (id) =>
				set({ selectedShotId: id }, false, "setSelectedShot"),
			setSelectedCharacter: (id) =>
				set({ selectedCharacterId: id }, false, "setSelectedCharacter"),
			setHighlightedMessage: (index) =>
				set({ highlightedMessageIndex: index }, false, "setHighlightedMessage"),
			setGenerating: (isGenerating) =>
				set({ isGenerating }, false, "setGenerating"),
			setCurrentStage: (stage) =>
				set({ currentStage: stage }, false, "setCurrentStage"),
			setCurrentAgent: (agent) =>
				set({ currentAgent: agent }, false, "setCurrentAgent"),
			setProgress: (progress) => set({ progress }, false, "setProgress"),
			addMessage: (message) =>
				set(
					(state) => ({ messages: [...state.messages, message] }),
					false,
					"addMessage",
				),
			setMessages: (messages) => set({ messages }, false, "setMessages"),
			clearMessages: () =>
				set(
					{ messages: [], highlightedMessageIndex: null },
					false,
					"clearMessages",
				),
			setRecoveryControl: (control) =>
				set({ recoveryControl: control }, false, "setRecoveryControl"),
			setRecoverySummary: (summary) =>
				set({ recoverySummary: summary }, false, "setRecoverySummary"),
			setRecoveryGate: (gate) =>
				set({ recoveryGate: gate }, false, "setRecoveryGate"),
			setCharacters: (characters) =>
				set({ characters }, false, "setCharacters"),
			setShots: (shots) => set({ shots }, false, "setShots"),
			setProjectVideoUrl: (url) =>
				set({ projectVideoUrl: url }, false, "setProjectVideoUrl"),
			setProjectStatus: (status) =>
				set({ projectStatus: status }, false, "setProjectStatus"),
			setProjectUpdatedAt: (timestamp) =>
				set({ projectUpdatedAt: timestamp }, false, "setProjectUpdatedAt"),
			setShotSyncCompleted: (timestamp) =>
				set({ shotSyncCompleted: timestamp }, false, "setShotSyncCompleted"),
			setProjectTitle: (title) =>
				set({ projectTitle: title }, false, "setProjectTitle"),
			setProjectSummary: (summary) =>
				set({ projectSummary: summary }, false, "setProjectSummary"),
			setProjectStoryOutline: (outline) =>
				set({ projectStoryOutline: outline }, false, "setProjectStoryOutline"),
			setProjectVisualBible: (visualBible) =>
				set({ projectVisualBible: visualBible }, false, "setProjectVisualBible"),
			setProjectOutlineApproved: (approved) =>
				set({ projectOutlineApproved: approved }, false, "setProjectOutlineApproved"),
			setProjectStory: (story) =>
				set({ projectStory: story }, false, "setProjectStory"),
			setProjectStyle: (style) =>
				set({ projectStyle: style }, false, "setProjectStyle"),
			setProjectTargetShotCount: (count) =>
				set(
					{ projectTargetShotCount: count },
					false,
					"setProjectTargetShotCount",
				),
			setProjectCharacterHints: (hints) =>
				set(
					{ projectCharacterHints: hints },
					false,
					"setProjectCharacterHints",
				),
			setProjectCreationMode: (mode) =>
				set({ projectCreationMode: mode }, false, "setProjectCreationMode"),
			setProjectReferenceImages: (images) =>
				set(
					{ projectReferenceImages: images },
					false,
					"setProjectReferenceImages",
				),
			setProjectExports: (exports) =>
				set({ projectExports: exports }, false, "setProjectExports"),
			setProjectProviderSettings: (settings) =>
				set(
					{ projectProviderSettings: settings },
					false,
					"setProjectProviderSettings",
				),
			setProjectUniverseId: (id) =>
				set({ projectUniverseId: id }, false, "setProjectUniverseId"),
			setProjectChapterNumber: (chapter) =>
				set(
					{ projectChapterNumber: chapter },
					false,
					"setProjectChapterNumber",
				),
			setProjectChapterTitle: (title) =>
				set({ projectChapterTitle: title }, false, "setProjectChapterTitle"),
			setBlockingClips: (clips) =>
				set({ blockingClips: clips }, false, "setBlockingClips"),
			setCritiqueReviewCard: (data) =>
				set(
					{
						critiqueReviewCard: data,
						awaitingConfirm: data !== null,
						awaitingAgent: data !== null ? "critic" : null,
					},
					false,
					"setCritiqueReviewCard",
				),
			setCritiqueOverride: (entityId, shouldRegenerate) =>
				set(
					(state) => ({
						critiqueOverrides: {
							...state.critiqueOverrides,
							[entityId]: shouldRegenerate,
						},
					}),
					false,
					"setCritiqueOverride",
				),
			clearCritiqueReview: () =>
				set(
					{
						critiqueReviewCard: null,
						critiqueOverrides: {},
						awaitingConfirm: false,
						awaitingAgent: null,
					},
					false,
					"clearCritiqueReview",
				),
			setEntityApprovalDecisions: (decisions) =>
				set({ entityApprovalDecisions: decisions }, false, "setEntityApprovalDecisions"),
			clearEntityApprovalDecisions: () =>
				set({ entityApprovalDecisions: [] }, false, "clearEntityApprovalDecisions"),
			setAwaitingConfirm: (awaiting, agent = null, runId) =>
				set(
					(state) => ({
						awaitingConfirm: awaiting,
						awaitingAgent: agent,
						currentRunId: runId !== undefined ? runId : state.currentRunId,
					}),
					false,
					"setAwaitingConfirm",
				),
			setCurrentRunId: (runId) =>
				set({ currentRunId: runId }, false, "setCurrentRunId"),
			setCurrentRunProviderSnapshot: (snapshot) =>
				set(
					{ currentRunProviderSnapshot: snapshot },
					false,
					"setCurrentRunProviderSnapshot",
				),
			setRunMode: (mode) => set({ runMode: mode }, false, "setRunMode"),
			setGateMode: (gate, enabled) =>
				set((state) => {
					const next = new Set(state.gateModes);
					if (enabled) next.add(gate);
					else next.delete(gate);
					return { gateModes: next };
				}, false, "setGateMode"),
			setGateModes: (gates) =>
				set({ gateModes: new Set(gates) }, false, "setGateModes"),
			resetGateModes: () =>
				set({ gateModes: new Set() }, false, "resetGateModes"),
			updateCharacter: (character) =>
				set(
					(state) => ({
						characters: state.characters.some((c) => c.id === character.id)
							? state.characters.map((c) =>
									c.id === character.id ? character : c,
								)
							: [...state.characters, character],
					}),
					false,
					"updateCharacter",
				),
			updateShot: (shot) =>
				set(
					(state) => ({
						shots: state.shots.some((s) => s.id === shot.id)
							? state.shots.map((s) => (s.id === shot.id ? shot : s))
							: [...state.shots, shot],
					}),
					false,
					"updateShot",
				),
			removeCharacter: (characterId) =>
				set(
					(state) => ({
						characters: state.characters.filter((c) => c.id !== characterId),
					}),
					false,
					"removeCharacter",
				),
			removeShot: (shotId) =>
				set(
					(state) => ({
						shots: state.shots.filter((s) => s.id !== shotId),
					}),
					false,
					"removeShot",
				),
			resetRunState: () => set(initialRunState, false, "resetRunState"),
			reset: () => set(initialState, false, "reset"),
		}),
		{ name: "EditorStore", enabled: import.meta.env.DEV },
	),
);

export { useShallow };
