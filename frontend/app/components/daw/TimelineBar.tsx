import { clsx } from "clsx";
import type { WorkflowStage } from "~/types";

interface TimelineBarProps {
	currentStage: WorkflowStage;
	stages: Array<{
		key: WorkflowStage;
		label: string;
		progress: number; // 0-100
	}>;
	currentItem?: {
		id: number;
		title: string;
	};
	onStageClick?: (stage: WorkflowStage) => void;
}

export function TimelineBar({
	currentStage,
	stages,
	currentItem,
	onStageClick,
}: TimelineBarProps) {
	const currentIndex = stages.findIndex((s) => s.key === currentStage);

	return (
		<div className="flex-shrink-0 flex items-center h-10 px-4 bg-base-200 border-t border-base-content/10">
			<div className="flex-1 flex items-center gap-1">
				{stages.map((stage, i) => (
					<button
						key={stage.key}
						type="button"
						title={`${stage.label}: ${stage.progress}%`}
						onClick={() => onStageClick?.(stage.key)}
						className={clsx(
							"flex-1 h-1.5 rounded-full transition-all duration-200",
							i < currentIndex && "bg-success",
							i === currentIndex && "bg-primary",
							i > currentIndex && "bg-base-content/10",
						)}
					/>
				))}
			</div>
			{currentItem && (
				<div className="ml-4 text-xs text-base-content/60">
					<span className="font-mono">{currentStage}</span>
					<span className="mx-1">›</span>
					<span>{currentItem.title}</span>
				</div>
			)}
		</div>
	);
}
