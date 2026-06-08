import { XMarkIcon } from "@heroicons/react/24/outline";
import { useEffect } from "react";
import { useEditorStore, useShallow } from "~/stores/editorStore";
import { useChatPanelStore } from "~/stores/chatPanelStore";
import { ChatPanel } from "~/components/chat/ChatPanel";

interface ChatDrawerProps {
	projectId?: number;
	onSendFeedback: (content: string) => void;
	onConfirm: (feedback?: string) => void;
	onEntityConfirm: (decisions: import("~/types").EntityDecision[]) => void;
	onGenerate: () => void;
	onCancel: () => void;
	isGenerating: boolean;
	generateDisabled?: boolean;
	generateDisabledReason?: string;
}

export function ChatDrawer({
	projectId,
	onSendFeedback,
	onConfirm,
	onEntityConfirm,
	onGenerate,
	onCancel,
	isGenerating,
	generateDisabled = false,
	generateDisabledReason,
}: ChatDrawerProps) {
	const { isOpen, close } = useChatPanelStore();
	const { awaitingConfirm, runMode } = useEditorStore(useShallow((s) => ({ awaitingConfirm: s.awaitingConfirm, runMode: s.runMode })));

	useEffect(() => {
		if (awaitingConfirm && runMode === "manual") {
			useChatPanelStore.getState().open();
		}
	}, [awaitingConfirm, runMode]);

	if (!isOpen) return null;

	return (
		<div className="flex-shrink-0 w-[280px] lg:w-[360px] flex flex-col bg-base-100 border-l border-base-300 h-full">
			<div className="flex items-center justify-end px-2 py-1.5 border-b border-base-300">
				<button
					className="btn btn-xs btn-circle btn-ghost"
					onClick={close}
					aria-label="关闭对话面板"
				>
					<XMarkIcon className="w-4 h-4" />
				</button>
			</div>

			<div className="flex-1 overflow-hidden">
			<ChatPanel
				projectId={projectId}
				onSendFeedback={onSendFeedback}
				onConfirm={onConfirm}
				onEntityConfirm={onEntityConfirm}
				onGenerate={onGenerate}
				onCancel={onCancel}
				isGenerating={isGenerating}
				generateDisabled={generateDisabled}
				generateDisabledReason={generateDisabledReason}
			/>
			</div>
		</div>
	);
}
