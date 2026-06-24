import type { EntityDecision, VersionEntityType } from "~/types";
import { ChatDrawer } from "~/components/chat/ChatDrawer";
import { AssetDrawer } from "~/components/panels/AssetDrawer";
import { HistoryDrawer } from "~/components/panels/HistoryDrawer";
import { VersionCompareDrawer } from "~/components/panels/VersionCompareDrawer";

interface DrawerPortalProps {
	assetsOpen: boolean;
	onAssetsClose: () => void;
	historyOpen: boolean;
	onHistoryClose: () => void;
	onHistoryNavigate?: (projectId: number) => void;
	chatProjectId?: number;
	chatIsGenerating: boolean;
	onChatSendFeedback: (content: string) => void;
	onChatConfirm: (feedback?: string) => void;
	onChatEntityConfirm: (decisions: EntityDecision[]) => void;
	onChatGenerate: () => void;
	onChatCancel: () => void;
	chatGenerateDisabled?: boolean;
	chatGenerateDisabledReason?: string;
	versionCompareOpen: boolean;
	versionCompareProjectId: number;
	versionCompareEntityType?: VersionEntityType;
	versionCompareEntityId?: number | null;
	onVersionCompareClose: () => void;
}

export function DrawerPortal({
	assetsOpen,
	onAssetsClose,
	historyOpen,
	onHistoryClose,
	onHistoryNavigate,
	chatProjectId,
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
}: DrawerPortalProps) {
	return (
		<>
			<AssetDrawer
				open={assetsOpen}
				onClose={onAssetsClose}
				projectId={chatProjectId}
			/>
			<HistoryDrawer
				open={historyOpen}
				onClose={onHistoryClose}
				onNavigate={onHistoryNavigate}
			/>
			<ChatDrawer
				projectId={chatProjectId}
				onSendFeedback={onChatSendFeedback}
				onConfirm={onChatConfirm}
				onEntityConfirm={onChatEntityConfirm}
				onGenerate={onChatGenerate}
				onCancel={onChatCancel}
				isGenerating={chatIsGenerating}
				generateDisabled={chatGenerateDisabled}
				generateDisabledReason={chatGenerateDisabledReason}
			/>
			<VersionCompareDrawer
				open={versionCompareOpen}
				projectId={versionCompareProjectId}
				initialEntityType={versionCompareEntityType}
				initialEntityId={versionCompareEntityId}
				onClose={onVersionCompareClose}
			/>
		</>
	);
}
