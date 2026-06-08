import { ALL_GATES, type GateName, GATE_LABELS } from "~/stores/editorStore";
import { BoltIcon, AdjustmentsHorizontalIcon } from "@heroicons/react/24/outline";

interface GateModePanelProps {
	gateModes: Set<GateName>;
	onToggle: (gate: GateName, enabled: boolean) => void;
	onSetAll: (gates: GateName[]) => void;
}

const PRESETS: Record<string, { label: string; gates: GateName[] }> = {
	all_manual: { label: "全部手动", gates: [] },
	all_yolo: { label: "全部 YOLO", gates: [...ALL_GATES] },
	plan_only: { label: "仅规划自动", gates: ["outline", "characters", "shots"] },
	render_only: {
		label: "仅渲染自动",
		gates: [
			"character_images",
			"shot_images",
			"compose",
			"critique_characters",
			"critique_shots",
		],
	},
};

function getSummaryText(gateModes: Set<GateName>): string {
	const count = gateModes.size;
	if (count === 0) return "全部手动";
	if (count === ALL_GATES.length) return "全部自动";
	return `自定义: ${count}/8 自动`;
}

export function GateModePanel({ gateModes, onToggle, onSetAll }: GateModePanelProps) {
	const summaryText = getSummaryText(gateModes);
	const isAllYolo = gateModes.size === ALL_GATES.length;

	return (
		<div className="bg-card/75 backdrop-blur-sm border border-base-content/10 rounded-lg overflow-hidden">
			<div className="collapse collapse-arrow min-h-0">
				<input type="checkbox" aria-label="展开/收起 YOLO 模式配置" />

				<div className="collapse-title p-2 min-h-0 flex items-center justify-between text-xs">
					<div className="flex items-center gap-1.5">
						{isAllYolo ? (
							<BoltIcon className="w-3 h-3 text-primary" aria-hidden="true" />
						) : (
							<AdjustmentsHorizontalIcon
								className="w-3 h-3 text-base-content/60"
								aria-hidden="true"
							/>
						)}
						<span className="font-medium">YOLO 配置</span>
					</div>
					<span
						className={`text-xs ${isAllYolo ? "text-primary font-medium" : "text-base-content/60"}`}
					>
						{summaryText}
					</span>
				</div>

				<div className="collapse-content p-2 pt-0">
					<div className="space-y-1 mb-3">
						{ALL_GATES.map((gate) => (
							<div
								key={gate}
								className="flex items-center justify-between py-1 px-1.5 rounded hover:bg-base-content/5"
							>
								<span className="text-xs text-base-content/80">{GATE_LABELS[gate]}</span>
								<input
									type="checkbox"
									className="toggle toggle-xs toggle-primary"
									checked={gateModes.has(gate)}
									onChange={(e) => onToggle(gate, e.target.checked)}
									aria-label={`${GATE_LABELS[gate]} 自动确认`}
								/>
							</div>
						))}
					</div>

					<div className="flex flex-wrap gap-1 pt-2 border-t border-base-content/10">
						{Object.entries(PRESETS).map(([key, preset]) => (
							<button
								key={key}
								type="button"
								onClick={() => onSetAll(preset.gates)}
								className="btn btn-xs btn-ghost !min-h-0 !h-6 px-2 text-xs"
							>
								{preset.label}
							</button>
						))}
					</div>
				</div>
			</div>
		</div>
	);
}
