import { useState, useRef, useEffect } from "react";
import { useEditorStore, useShallow } from "~/stores/editorStore";
import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";
import { OutlinePreviewCard } from "./OutlinePreviewCard";
import { CritiqueResultCard } from "./CritiqueResultCard";
import { EntityApprovalCard } from "./EntityApprovalCard";
import { VersionCompareInline } from "./VersionCompareInline";
import { GateModePanel } from "./GateModePanel";
import { Button } from "~/components/ui/Button";
import type { EntityDecision, WorkflowStage, VersionEntityType } from "~/types";
import { projectsApi } from "~/services/api";
import { AGENT_NAME_MAP } from "~/types";
import { ALL_GATES } from "~/stores/editorStore";
import {
  CheckIcon,
  LightBulbIcon,
  PaintBrushIcon,
  RocketLaunchIcon,
  StopIcon,
  BoltIcon,
  AdjustmentsHorizontalIcon,
} from "@heroicons/react/24/outline";
import { getWorkflowStageInfo } from "~/utils/workflowStage";

interface ChatPanelProps {
	projectId?: number;
	onSendFeedback: (content: string) => void;
	onConfirm: (feedback?: string) => void;
	onEntityConfirm?: (decisions: import("~/types").EntityDecision[]) => void;
	onGenerate: () => void;
	onCancel: () => void;
	isGenerating: boolean;
  generateDisabled?: boolean;
  generateDisabledReason?: string;
  isPaused?: boolean;
  onPause?: () => void;
  onResume?: () => void;
}

function getStageIcon(stage: WorkflowStage) {
  if (stage === "compose") return RocketLaunchIcon;
  if (stage === "render" || stage === "render_approval") return PaintBrushIcon;
  if (stage === "plan" || stage === "plan_approval") return LightBulbIcon;
  return LightBulbIcon;
}

const agentNameMap = AGENT_NAME_MAP;

export function ChatPanel({
	projectId,
	onSendFeedback,
	onConfirm,
	onEntityConfirm,
	onGenerate,
	onCancel,
	isGenerating,
  generateDisabled = false,
  generateDisabledReason,
  isPaused = false,
  onPause: _onPause,
  onResume,
}: ChatPanelProps) {
  const generateDisabledReasonId = generateDisabledReason ? "generate-disabled-reason" : undefined;
	const {
		messages,
		currentAgent,
		awaitingConfirm,
		awaitingAgent,
		currentStage,
		currentRunId,
		runMode,
		recoveryGate,
		critiqueReviewCard,
	} = useEditorStore(useShallow((s) => ({
		messages: s.messages,
		currentAgent: s.currentAgent,
		awaitingConfirm: s.awaitingConfirm,
		awaitingAgent: s.awaitingAgent,
		currentStage: s.currentStage,
		currentRunId: s.currentRunId,
		runMode: s.runMode,
		recoveryGate: s.recoveryGate,
		critiqueReviewCard: s.critiqueReviewCard,
	})));

	const setRunMode = useEditorStore((s) => s.setRunMode);
	const gateModes = useEditorStore((s) => s.gateModes);
	const setGateMode = useEditorStore((s) => s.setGateMode);
	const setGateModes = useEditorStore((s) => s.setGateModes);
	const resetGateModes = useEditorStore((s) => s.resetGateModes);
	const clearCritiqueReview = useEditorStore((s) => s.clearCritiqueReview);
	const [input, setInput] = useState("");
	const [showVersionCompare, setShowVersionCompare] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;
    if (currentRunId || isGenerating || awaitingConfirm) {
      onConfirm(input.trim());
      setInput("");
      return;
    }
    onSendFeedback(input);
    setInput("");
  };

	const handleCritiqueConfirm = async (overrides: Record<number, boolean>) => {
		const id = projectId;
		const runId = currentRunId;
		if (!id || !runId) return;
		try {
			await projectsApi.resume(id, runId, { overrides });
			clearCritiqueReview();
		} catch (err) {
			console.error("Failed to resume with critique overrides:", err);
		}
	};

	const handleCritiqueCancel = () => {
		const id = projectId;
		const runId = currentRunId;
		if (!id || !runId) return;
		projectsApi.resume(id, runId, { overrides: {} });
		clearCritiqueReview();
	};

	const handleEntityConfirm = async (decisions: EntityDecision[]) => {
		onEntityConfirm?.(decisions);
	};

	const handleEntityRegenerate = async (decisions: EntityDecision[]) => {
		const id = projectId;
		const runId = currentRunId;
		if (!id || !runId) return;
		try {
			const feedback = decisions
				.map((d) => `[${d.entity_id}] ${d.feedback || "请重新生成"}`)
				.join("\n");
			await projectsApi.resume(id, runId, { feedback });
		} catch (err) {
			console.error("Failed to resume with entity feedback:", err);
		}
	};

	const info = getWorkflowStageInfo(currentStage);
  const StageIcon = getStageIcon(currentStage);
  const hasMessages = messages.length > 0;
  const agentDisplayName = awaitingAgent ? agentNameMap[awaitingAgent] || awaitingAgent : "";
  const hasCustomGates = gateModes.size > 0;
  const allGatesAuto = gateModes.size === ALL_GATES.length;
  const isYolo = runMode === "yolo" || allGatesAuto;

  const showManualConfirm = awaitingConfirm && !isYolo;
  const showOutlinePreview =
    showManualConfirm && awaitingAgent === "outline" && recoveryGate?.story_outline;

  return (
    <div className="flex flex-col h-full bg-base-100">
      <div className="px-2.5 py-1.5 border-b border-base-content/10 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <StageIcon className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
          <span className="text-xs font-heading font-bold">{info.title}</span>
        </div>

        <div className="flex items-center gap-1.5">
          {/* 快速 YOLO 开关（无自定义时使用） */}
          {!hasCustomGates && (
            <button
              type="button"
              onClick={() => {
                const newVal = isYolo ? "manual" : "yolo";
                setRunMode(newVal);
                if (newVal === "yolo") {
                  setGateModes([...ALL_GATES]);
                } else {
                  resetGateModes();
                }
              }}
              className={`btn btn-xs gap-0.5 ${isYolo ? "btn-primary btn-sm border" : "btn-ghost"} !min-h-0 !h-6 text-xs`}
              aria-label={isYolo ? "切换手动模式" : "切换YOLO模式"}
              title={isYolo ? "YOLO：自动确认" : "手动：逐阶段确认"}
            >
              {isYolo ? (
                <>
                  <BoltIcon className="w-2.5 h-2.5" />
                  YOLO
                </>
              ) : (
                <>
                  <AdjustmentsHorizontalIcon className="w-2.5 h-2.5" />
                  手动
                </>
              )}
            </button>
          )}
          {/* Per-gate 自定义面板 */}
          <GateModePanel
            gateModes={gateModes}
            onToggle={setGateMode}
            onSetAll={(gates) => setGateModes(gates)}
          />
        </div>
      </div>

      {isGenerating && !awaitingConfirm && (
        <div className="px-2.5 py-1 border-b border-base-content/10 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs text-base-content/50">
            <span className="loading loading-dots loading-xs text-primary" />
            {agentNameMap[currentAgent || ""] || currentAgent || "处理中"}...
            {isYolo && (
              <span className="badge badge-primary badge-outline badge-xs gap-0.5 border">
                <BoltIcon className="w-2 h-2" /> AUTO
              </span>
            )}
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={onCancel}
            className="text-error hover:bg-error/10 gap-0.5 !px-1 !py-0 !min-h-0 !h-auto text-xs"
            aria-label="停止生成"
          >
            <StopIcon className="w-3 h-3" /> 停止
          </Button>
        </div>
      )}

      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto px-2.5 py-2 grain-subtle">
        {!hasMessages && !isGenerating ? (
          <div className="flex flex-col h-full">
            <div className="flex-1 flex flex-col items-center justify-center text-center px-3">
              <div className="w-10 h-10 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center mb-2">
                <StageIcon className="w-4 h-4 text-primary" aria-hidden="true" />
              </div>
              <p className="text-xs text-base-content/50 mb-3 max-w-xs">
                {isYolo
                  ? "点击开始，AI 全自动生成"
                  : "点击开始，AI 根据你的故事生成漫剧"}
              </p>
              <Button
                variant="primary"
                size="lg"
                onClick={onGenerate}
                disabled={generateDisabled}
                className="gap-1.5 touch-target"
                aria-label="开始生成漫剧"
                aria-describedby={generateDisabledReasonId}
              >
                <RocketLaunchIcon className="w-4 h-4" aria-hidden="true" />
                开始生成
              </Button>
              {generateDisabledReason && (
                <p id={generateDisabledReasonId} className="mt-1.5 max-w-xs text-xs text-warning" aria-live="polite">
                  {generateDisabledReason}
                </p>
              )}
            </div>
          </div>
        ) : (
          <MessageList messages={messages} />
        )}
      </div>

		{showOutlinePreview && recoveryGate?.story_outline && (
		<div className="px-2.5 py-2 border-t-2 border-primary/30 bg-primary/5">
			<OutlinePreviewCard
			outline={recoveryGate.story_outline}
			visualBible={recoveryGate.visual_bible}
			onConfirm={() => {
				onConfirm(undefined);
				setInput("");
			}}
			onRegenerate={(feedback) => {
				onConfirm(feedback);
				setInput("");
			}}
			/>
		</div>
		)}

		{critiqueReviewCard && (
		<div className="px-2.5 py-2 border-t-2 border-primary/30 bg-primary/5">
			<CritiqueResultCard
			data={critiqueReviewCard}
			onConfirm={handleCritiqueConfirm}
			onCancel={handleCritiqueCancel}
			/>
		</div>
		)}

		{showManualConfirm && !showOutlinePreview && (
			<>
				{recoveryGate?.entity_summaries && recoveryGate.entity_summaries.length > 0 ? (
					<div className="px-2.5 py-2 border-t-2 border-primary/30 bg-primary/5">
						<EntityApprovalCard
							entityType={recoveryGate.entity_type as "character" | "shot"}
							entityLabel={recoveryGate.entity_type === "character" ? "角色" : "分镜"}
							entities={recoveryGate.entity_summaries}
							onConfirm={handleEntityConfirm}
							onRegenerate={handleEntityRegenerate}
						/>
					</div>
				) : (
					<div className="px-2.5 py-1.5 border-t-2 border-primary/30 bg-primary/5">
						{showVersionCompare && recoveryGate?.entity_type && recoveryGate?.entity_ids?.[0] != null && (
							<div className="mb-3">
								<VersionCompareInline
									projectId={projectId!}
									entityType={recoveryGate.entity_type as VersionEntityType}
									entityId={recoveryGate.entity_ids[0]}
									onClose={() => setShowVersionCompare(false)}
								/>
							</div>
						)}
						<div className="flex items-center justify-between gap-2">
							<div className="flex items-center gap-2">
								<span className="text-xs text-base-content/60 font-medium">
									{agentDisplayName} 已完成 — 确认继续？
								</span>
								{recoveryGate?.entity_ids?.length ? (
									<Button
										variant="ghost"
										size="sm"
										onClick={() => setShowVersionCompare(!showVersionCompare)}
										className="gap-0.5 !px-2 !py-0.5 !min-h-0 !h-6 text-xs"
									>
										查看版本对比 {showVersionCompare ? "▴" : "▾"}
									</Button>
								) : null}
							</div>
							<Button
								variant="primary"
								size="sm"
								onClick={() => {
									const feedback = input.trim();
									onConfirm(feedback || undefined);
									setInput("");
								}}
								className="gap-0.5 !px-2.5 !py-0.5 !min-h-0 !h-6 text-xs border shadow-aperture"
							>
								<CheckIcon className="w-3 h-3" />
								通过
							</Button>
						</div>
					</div>
				)}
			</>
		)}

      {awaitingConfirm && isYolo && isPaused && onResume && (
        <div className="px-2.5 py-1 border-t border-base-content/10 bg-primary/5 flex items-center gap-1.5 text-xs text-base-content/50">
          <BoltIcon className="w-2.5 h-2.5" />
          YOLO 已暂停
          <Button size="sm" variant="ghost" onClick={onResume} className="ml-auto !px-1.5 !py-0 !min-h-0 !h-auto text-xs">
            继续
          </Button>
        </div>
      )}

      <div className="p-2 border-t border-base-content/10">
        <MessageInput
          value={input}
          onChange={setInput}
          onSend={handleSend}
          disabled={false}
          placeholder={
            awaitingConfirm
              ? "修改意见（可选）..."
              : isGenerating
                ? "反馈..."
                : "你的想法..."
          }
        />
      </div>
    </div>
  );
}
