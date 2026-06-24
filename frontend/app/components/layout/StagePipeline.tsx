import {
	CheckIcon,
	ExclamationTriangleIcon,
	FilmIcon,
	LightBulbIcon,
	SparklesIcon,
	CubeIcon,
	ArrowPathIcon,
	StopIcon,
	UserIcon,
	PaintBrushIcon,
} from "@heroicons/react/24/outline";
import type { WorkflowStage } from "~/types";
import { STAGE_PIPELINE, getPipelineStageIndex } from "~/utils/pipeline";
import { Button } from "~/components/ui/Button";

const STAGE_ICONS: Record<string, typeof LightBulbIcon> = {
	bulb: LightBulbIcon,
	sparkle: SparklesIcon,
	film: FilmIcon,
	cube: CubeIcon,
	user: UserIcon,
	palette: PaintBrushIcon,
};

interface StagePipelineProps {
	currentStage: WorkflowStage;
	isGenerating: boolean;
	awaitingConfirm: boolean;
	hasRecovery: boolean;
	onResume: () => void;
	onCancel: () => void;
}

export function StagePipeline({
	currentStage,
	isGenerating,
	awaitingConfirm,
	hasRecovery,
	onResume,
	onCancel,
}: StagePipelineProps) {
	const currentIndex = getPipelineStageIndex(currentStage);

	return (
		<div className="flex-shrink-0 flex items-center h-8 px-3 bg-base-100 border-b-2 border-base-content/15 z-20 gap-3">
			<div className="flex-1 flex items-center justify-center gap-4">
				<nav className="flex items-center" aria-label="Pipeline stages">
					{STAGE_PIPELINE.map((stage, index) => {
						const isCurrent = stage.key === currentStage;
						const isPast = index < currentIndex;
						const isGeneratingHere = isCurrent && isGenerating;
						const isAwaiting = isCurrent && awaitingConfirm;
						const isRecoveryPoint = isCurrent && hasRecovery;
						const IconComponent = STAGE_ICONS[stage.icon];

						let dotClass = "bg-base-content/20 border-base-content/20";
						if (isPast) dotClass = "bg-success border-success/50";
						if (isCurrent) dotClass = "bg-primary border-primary/50";
						if (isGeneratingHere) dotClass = "bg-warning border-warning/50 animate-pulse";
						if (isAwaiting) dotClass = "bg-info border-info/50";

						return (
							<div key={stage.key} className="flex items-center">
								<div
									className={`flex items-center gap-1.5 px-2 py-0.5 rounded-md transition-colors duration-150 ${
										isCurrent ? "bg-primary/10 border border-primary/25" : "border border-transparent"
									}`}
								>
									<div className={`w-3 h-3 rounded-full border ${dotClass}`} />
									<IconComponent className={`w-3.5 h-3.5 ${isPast ? "text-success" : isCurrent ? "text-primary" : "text-base-content/25"}`} />
									<span className={`text-xs font-heading font-bold tracking-wide ${isPast ? "text-success" : isCurrent ? "text-primary" : "text-base-content/25"}`}>
										{stage.label}
									</span>
									{isPast && <CheckIcon className="w-2.5 h-2.5 text-success" />}
									{isRecoveryPoint && !isGenerating && (
										<ExclamationTriangleIcon className="w-2.5 h-2.5 text-warning" />
									)}
								</div>
								{index < STAGE_PIPELINE.length - 1 && (
									<div className={`w-5 h-[3px] mx-1 rounded-full ${index < currentIndex ? "bg-success/70" : "bg-base-content/12"}`} />
								)}
							</div>
						);
					})}
				</nav>

				{hasRecovery && !isGenerating && (
					<div className="flex items-center gap-1">
						<Button variant="primary" size="sm" className="!px-2 !py-0 !min-h-0 !h-6 text-xs gap-0.5 border shadow-aperture" onClick={onResume}>
							<ArrowPathIcon className="w-2.5 h-2.5" />
							恢复
						</Button>
						<Button variant="ghost" size="sm" className="!px-0.5 !py-0 !min-h-0 !h-5" onClick={onCancel}>
							<StopIcon className="w-2.5 h-2.5" />
						</Button>
					</div>
				)}
			</div>
		</div>
	);
}
