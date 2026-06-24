import {
  LightBulbIcon,
  DocumentTextIcon,
  UserCircleIcon,
  FilmIcon,
  SparklesIcon,
  CubeIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  StopIcon,
  CheckIcon,
  PaintBrushIcon,
} from "@heroicons/react/24/outline";
import type { WorkflowStage } from "~/types";
import { STAGE_PIPELINE, getPipelineStageIndex } from "~/utils/pipeline";
import { Button } from "~/components/ui/Button";

const STAGE_ICONS: Record<string, typeof LightBulbIcon> = {
  bulb: LightBulbIcon,
  document: DocumentTextIcon,
  user: UserCircleIcon,
  film: FilmIcon,
  sparkle: SparklesIcon,
  cube: CubeIcon,
  palette: PaintBrushIcon,
};

interface StagePipelineProps {
  currentStage: WorkflowStage;
  isGenerating: boolean;
  awaitingConfirm: boolean;
  onResume: () => void;
  onCancel: () => void;
  hasRecovery: boolean;
}

export function StagePipeline({
  currentStage,
  isGenerating,
  awaitingConfirm,
  onResume,
  onCancel,
  hasRecovery,
}: StagePipelineProps) {
  const currentIndex = getPipelineStageIndex(currentStage);

  return (
    <div className="flex items-center gap-1 px-3 py-1.5 bg-base-100 border-b border-base-300 z-20">
      {STAGE_PIPELINE.map((stage, index) => {
        const isCurrent = stage.key === currentStage;
        const isPast = index < currentIndex;
        const isGeneratingHere = isCurrent && isGenerating;
        const isAwaiting = isCurrent && awaitingConfirm;
        const isRecoveryPoint = isCurrent && hasRecovery;

        const IconComponent = STAGE_ICONS[stage.icon];

        let stageClass = "text-base-content/40";
        if (isPast) stageClass = "text-success";
        if (isCurrent) stageClass = "text-primary font-semibold";
        if (isGeneratingHere) stageClass = "text-warning font-semibold animate-pulse";
        if (isAwaiting) stageClass = "text-info font-semibold";
        if (isRecoveryPoint) stageClass = "text-warning font-semibold";

        let dotClass = "bg-base-content/20";
        if (isPast) dotClass = "bg-success";
        if (isCurrent) dotClass = "bg-primary";
        if (isGeneratingHere) dotClass = "bg-warning animate-pulse";
        if (isAwaiting) dotClass = "bg-info";
        if (isRecoveryPoint) dotClass = "bg-warning";

        return (
          <div key={stage.key} className="flex items-center">
            <div className={`flex items-center gap-1.5 px-2 py-1 rounded-lg transition-colors ${isCurrent ? "bg-primary/10" : ""}`}>
              <div className={`w-2 h-2 rounded-full ${dotClass}`} />
              <IconComponent className={`w-4 h-4 ${stageClass}`} />
              <span className={`text-xs ${stageClass} hidden sm:inline`}>
                {stage.label}
              </span>
              {isPast && (
                <CheckIcon className="w-3 h-3 text-success" />
              )}
              {isRecoveryPoint && !isGenerating && (
                <ExclamationTriangleIcon className="w-3 h-3 text-warning" />
              )}
            </div>

            {index < STAGE_PIPELINE.length - 1 && (
              <div className={`w-4 h-px mx-0.5 ${index < currentIndex ? "bg-success" : "bg-base-content/15"}`} />
            )}
          </div>
        );
      })}

      {hasRecovery && !isGenerating && (
        <div className="ml-2 flex items-center gap-1.5">
          <Button variant="primary" size="sm" onClick={onResume}>
            <ArrowPathIcon className="w-3.5 h-3.5" />
            <span className="text-xs">恢复</span>
          </Button>
          <Button variant="ghost" size="sm" onClick={onCancel}>
            <StopIcon className="w-3.5 h-3.5" />
          </Button>
        </div>
      )}
    </div>
  );
}
