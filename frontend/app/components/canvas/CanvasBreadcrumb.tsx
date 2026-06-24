import { ArrowsPointingOutIcon } from "@heroicons/react/24/outline";
import type { WorkflowStage } from "~/types";

interface CanvasBreadcrumbProps {
  projectId: number;
  currentStage: WorkflowStage;
  selectedShapeId?: string;
  onStageClick: (stage: WorkflowStage) => void;
  onShapeClick: (shapeId: string) => void;
  onFitToContent: () => void;
}

export function CanvasBreadcrumb({
  projectId: _projectId,
  currentStage,
  selectedShapeId,
  onStageClick,
  onShapeClick,
  onFitToContent,
}: CanvasBreadcrumbProps) {
  return (
    <div className="absolute top-4 left-4 z-10 flex items-center gap-2 px-3 py-2 bg-base-100/90 backdrop-blur-sm rounded-lg shadow-aperture border border-base-content/10">
      <button
        onClick={onFitToContent}
        className="text-xs text-base-content/60 hover:text-primary transition-colors"
        title="适应内容"
      >
        <ArrowsPointingOutIcon className="w-4 h-4" />
      </button>
      <span className="text-xs text-base-content/30">/</span>
      <button
        onClick={() => onStageClick(currentStage)}
        className="text-xs font-mono text-primary hover:text-primary-focus transition-colors"
      >
        {currentStage}
      </button>
      {selectedShapeId && (
        <>
          <span className="text-xs text-base-content/30">/</span>
          <button
            onClick={() => onShapeClick(selectedShapeId)}
            className="text-xs text-base-content/60 hover:text-primary transition-colors truncate max-w-[120px]"
          >
            {selectedShapeId}
          </button>
        </>
      )}
    </div>
  );
}
