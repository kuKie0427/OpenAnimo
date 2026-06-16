import { TopBar } from "./TopBar";
import { StagePipeline } from "./StagePipeline";
import { DrawerPortal } from "./DrawerPortal";
import type { WorkflowStage, EntityDecision, VersionEntityType } from "~/types";

interface AppShellProps {
	children: React.ReactNode;
	variant?: "default" | "workbench";
	showStagePipeline?: boolean;
	onToggleAssets?: () => void;
	onToggleHistory?: () => void;
	assetsOpen?: boolean;
	historyOpen?: boolean;
	projectId?: number;
	currentStage?: WorkflowStage;
	isGenerating?: boolean;
	awaitingConfirm?: boolean;
	hasRecovery?: boolean;
	onResume?: () => void;
	onCancelPipeline?: () => void;
	onAssetsClose?: () => void;
	onHistoryClose?: () => void;
	onHistoryNavigate?: (projectId: number) => void;
	chatIsGenerating?: boolean;
	onChatSendFeedback?: (content: string) => void;
	onChatConfirm?: (feedback?: string) => void;
	onChatEntityConfirm?: (decisions: EntityDecision[]) => void;
	onChatGenerate?: () => void;
	onChatCancel?: () => void;
	chatGenerateDisabled?: boolean;
	chatGenerateDisabledReason?: string;
	versionCompareOpen?: boolean;
	versionCompareProjectId?: number;
	versionCompareEntityType?: VersionEntityType;
	versionCompareEntityId?: number | null;
	onVersionCompareClose?: () => void;
}

export function AppShell({
	children,
	variant = "default",
	showStagePipeline = false,
	onToggleAssets,
	onToggleHistory,
	assetsOpen,
	historyOpen,
	projectId,
	currentStage,
	isGenerating,
	awaitingConfirm,
	hasRecovery,
	onResume,
	onCancelPipeline,
	onAssetsClose,
	onHistoryClose,
	onHistoryNavigate,
	chatIsGenerating,
	onChatSendFeedback,
	onChatConfirm,
	onChatEntityConfirm,
	onChatGenerate,
	onChatCancel,
	chatGenerateDisabled,
	chatGenerateDisabledReason,
	versionCompareOpen,
	versionCompareProjectId,
	versionCompareEntityType,
	versionCompareEntityId,
	onVersionCompareClose,
}: AppShellProps) {
	return (
		<div className="h-screen flex flex-col bg-base-100 font-sans overflow-hidden">
			<TopBar
				variant={variant}
				onToggleAssets={onToggleAssets ?? (() => {})}
				onToggleHistory={onToggleHistory ?? (() => {})}
				assetsOpen={assetsOpen ?? false}
				historyOpen={historyOpen ?? false}
				projectId={projectId}
			/>
			{showStagePipeline && currentStage && (
				<StagePipeline
					currentStage={currentStage}
					isGenerating={isGenerating ?? false}
					awaitingConfirm={awaitingConfirm ?? false}
					hasRecovery={hasRecovery ?? false}
					onResume={onResume ?? (() => {})}
					onCancel={onCancelPipeline ?? (() => {})}
				/>
			)}
			<div className="flex-1 flex overflow-hidden relative">{children}</div>
			<DrawerPortal
				assetsOpen={assetsOpen ?? false}
				onAssetsClose={onAssetsClose ?? (() => {})}
				historyOpen={historyOpen ?? false}
				onHistoryClose={onHistoryClose ?? (() => {})}
				onHistoryNavigate={onHistoryNavigate}
				chatProjectId={projectId}
			chatIsGenerating={chatIsGenerating ?? false}
			onChatSendFeedback={onChatSendFeedback ?? (() => {})}
			onChatConfirm={onChatConfirm ?? (() => {})}
			onChatEntityConfirm={onChatEntityConfirm ?? (() => {})}
			onChatGenerate={onChatGenerate ?? (() => {})}
			onChatCancel={onChatCancel ?? (() => {})}
				chatGenerateDisabled={chatGenerateDisabled}
				chatGenerateDisabledReason={chatGenerateDisabledReason}
			versionCompareOpen={versionCompareOpen ?? false}
			versionCompareProjectId={versionCompareProjectId ?? 0}
				versionCompareEntityType={versionCompareEntityType}
				versionCompareEntityId={versionCompareEntityId}
				onVersionCompareClose={onVersionCompareClose ?? (() => {})}
			/>
		</div>
	);
}
