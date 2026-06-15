import { clsx } from "clsx";
import { useCallback, useEffect, useRef } from "react";
import {
	CheckIcon,
	ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";
import type { WorkflowStage } from "~/types";

interface StageTabsProps {
	currentStage: WorkflowStage;
	stages: Array<{
		key: WorkflowStage;
		label: string;
		icon: React.ComponentType<{ className?: string }>;
		status: "completed" | "active" | "pending" | "error";
	}>;
	onStageChange: (stage: WorkflowStage) => void;
}

export function StageTabs({
	currentStage,
	stages,
	onStageChange,
}: StageTabsProps) {
	const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

	const handleKeyDown = useCallback(
		(event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
			if (event.key === "ArrowLeft") {
				event.preventDefault();
				const prevIndex = index === 0 ? stages.length - 1 : index - 1;
				const prevStage = stages[prevIndex];
				if (prevStage) {
					onStageChange(prevStage.key);
					tabRefs.current[prevIndex]?.focus();
				}
			} else if (event.key === "ArrowRight") {
				event.preventDefault();
				const nextIndex = index === stages.length - 1 ? 0 : index + 1;
				const nextStage = stages[nextIndex];
				if (nextStage) {
					onStageChange(nextStage.key);
					tabRefs.current[nextIndex]?.focus();
				}
			}
		},
		[stages, onStageChange],
	);

	useEffect(() => {
		const currentIndex = stages.findIndex((s) => s.key === currentStage);
		if (currentIndex !== -1) {
			tabRefs.current[currentIndex]?.focus();
		}
	}, [currentStage, stages]);

	const getStatusIcon = (status: StageTabsProps["stages"][number]["status"]) => {
		switch (status) {
			case "completed":
				return <CheckIcon className="w-3 h-3 text-success" />;
			case "error":
				return <ExclamationTriangleIcon className="w-3 h-3 text-error" />;
			default:
				return null;
		}
	};

	return (
		<div className="flex-shrink-0 flex items-center h-10 px-4 bg-base-200 border-b border-base-content/10">
			{stages.map((stage, index) => {
				const isActive = stage.key === currentStage;
				const Icon = stage.icon;
				const statusIcon = getStatusIcon(stage.status);
				const isClickable = stage.status !== "pending";

				return (
					<button
						key={stage.key}
						ref={(el) => {
							tabRefs.current[index] = el;
						}}
						type="button"
						role="tab"
						aria-selected={isActive}
						aria-controls={`stage-panel-${stage.key}`}
						tabIndex={isActive ? 0 : -1}
						onClick={() => isClickable && onStageChange(stage.key)}
						onKeyDown={(e) => handleKeyDown(e, index)}
						disabled={!isClickable}
						className={clsx(
							"flex items-center gap-2 px-4 py-2 text-sm font-heading transition-all duration-200",
							isActive
								? "text-primary border-b-2 border-primary"
								: "text-base-content/60 hover:text-base-content hover:bg-base-300",
						)}
					>
						<Icon className="w-4 h-4" />
						<span>{stage.label}</span>
						{statusIcon}
					</button>
				);
			})}
		</div>
	);
}
