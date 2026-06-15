import { useState } from "react";
import {
	RadarChart,
	Radar,
	PolarGrid,
	PolarAngleAxis,
	PolarRadiusAxis,
	ResponsiveContainer,
} from "recharts";
import {
	CheckIcon,
	ArrowPathIcon,
	ChevronDownIcon,
	ChevronUpIcon,
} from "@heroicons/react/24/outline";
import { useEditorStore } from "~/stores/editorStore";
import { Button } from "~/components/ui/Button";
import type { CritiqueReviewEventData, CritiqueEntityResult } from "~/types";

interface CritiqueResultCardProps {
	data: CritiqueReviewEventData;
	onConfirm: (overrides: Record<number, boolean>) => void;
	onCancel: () => void;
}

interface EntityRowProps {
	entity: CritiqueEntityResult;
	isOverridden: boolean;
	overrideValue?: boolean;
	onToggleOverride: (entityId: number, shouldRegenerate: boolean) => void;
}

function getScoreColor(score: number): string {
	if (score < 5) return "var(--er)";
	if (score < 8) return "var(--wa)";
	return "var(--su)";
}

function getScoreBadgeClass(score: number): string {
	if (score < 5) return "badge-error";
	if (score < 8) return "badge-warning";
	return "badge-success";
}

function EntityRow({
	entity,
	isOverridden,
	overrideValue,
	onToggleOverride,
}: EntityRowProps) {
	const [expanded, setExpanded] = useState(false);
	const [imageError, setImageError] = useState(false);

	const radarData = [
		{
			dimension: "一致性",
			value: entity.dimensions.consistency ?? entity.dimensions.face_similarity ?? 0,
		},
		{
			dimension: "质量",
			value: entity.dimensions.quality ?? entity.dimensions.overall ?? entity.score,
		},
		{
			dimension: "构图",
			value: entity.dimensions.composition ?? entity.dimensions.presence ?? 0,
		},
	];

	const verdictColor = entity.will_regenerate ? "text-warning" : "text-success";

	const effectiveWillRegenerate = isOverridden
		? overrideValue!
		: entity.will_regenerate;

	return (
		<div className="bg-base-200/50 rounded-lg p-3 space-y-2">
			<div className="flex items-start gap-3">
				<div className="flex-shrink-0">
					{entity.image_url && !imageError ? (
						<img
							src={entity.image_url}
							alt={entity.entity_name}
							className="w-16 h-16 rounded-lg object-cover"
							onError={() => setImageError(true)}
						/>
					) : (
						<div className="w-16 h-16 rounded-lg bg-base-300 flex items-center justify-center">
							<span className="text-2xl font-bold text-base-content/50">
								{entity.entity_name.charAt(0).toUpperCase()}
							</span>
						</div>
					)}
				</div>

				<div className="flex-1 min-w-0">
					<div className="flex items-center gap-2 mb-1">
						<h4 className="font-bold text-sm truncate">{entity.entity_name}</h4>
						<span
							className={`badge badge-sm ${getScoreBadgeClass(entity.score)}`}
						>
							{entity.score.toFixed(1)}
						</span>
					</div>

					<div className="flex items-center gap-1 text-xs">
						<span className="text-base-content/50">AI判定:</span>
						<span
							className={`font-medium ${verdictColor} ${isOverridden ? "line-through opacity-50" : ""}`}
						>
							{entity.will_regenerate ? (
								<>
									<ArrowPathIcon className="w-3 h-3 inline mr-0.5" />
									重生成
								</>
							) : (
								<>
									<CheckIcon className="w-3 h-3 inline mr-0.5" />
									通过
								</>
							)}
						</span>
						{isOverridden && (
							<span
								className={`font-medium ${overrideValue ? "text-warning" : "text-success"}`}
							>
								(已改为: {overrideValue ? "重生成" : "通过"})
							</span>
						)}
					</div>
				</div>

				<div className="flex-shrink-0 w-24 h-24">
					<ResponsiveContainer width="100%" height="100%">
						<RadarChart data={radarData}>
							<PolarGrid stroke="var(--n)" strokeOpacity={0.3} />
							<PolarAngleAxis
								dataKey="dimension"
								tick={{ fontSize: 8, fill: "var(--bc)" }}
							/>
							<PolarRadiusAxis
								angle={90}
								domain={[0, 10]}
								tick={{ fontSize: 6, fill: "var(--bc)", opacity: 0.5 }}
								tickCount={3}
							/>
							<Radar
								name={entity.entity_name}
								dataKey="value"
								stroke={getScoreColor(entity.score)}
								fill={getScoreColor(entity.score)}
								fillOpacity={0.2}
							/>
						</RadarChart>
					</ResponsiveContainer>
				</div>
			</div>

			<div className="flex items-center justify-between pt-1 border-t border-base-content/10">
				<button
					type="button"
					onClick={() => setExpanded(!expanded)}
					className="btn btn-ghost btn-xs gap-1 px-0 min-h-0 h-auto text-xs"
				>
					{expanded ? (
						<ChevronUpIcon className="w-3 h-3" />
					) : (
						<ChevronDownIcon className="w-3 h-3" />
					)}
					{expanded ? "收起详情" : "查看问题与建议"}
					{(entity.issues.length > 0 || entity.suggestions.length > 0) && (
						<span className="badge badge-xs badge-ghost">
							{entity.issues.length + entity.suggestions.length}
						</span>
					)}
				</button>

				<div className="flex items-center gap-2">
					<span className="text-xs text-base-content/60">
						{effectiveWillRegenerate ? "重新生成" : "跳过"}
					</span>
					<input
						type="checkbox"
						className="toggle toggle-sm"
						checked={effectiveWillRegenerate}
						onChange={(e) =>
							onToggleOverride(entity.entity_id, e.target.checked)
						}
						aria-label={effectiveWillRegenerate ? "重新生成" : "跳过"}
					/>
				</div>
			</div>

			{expanded && (
				<div className="space-y-2 pt-2">
					{entity.issues.length > 0 && (
						<div className="bg-error/10 rounded-md p-2">
							<p className="text-xs font-bold text-error mb-1">检测到的问题</p>
							<ul className="space-y-1">
								{entity.issues.slice(0, 3).map((issue, idx) => (
									<li key={idx} className="text-xs text-error/90">
										• {issue}
									</li>
								))}
								{entity.issues.length > 3 && (
									<li className="text-xs text-base-content/50 italic">
										...还有 {entity.issues.length - 3} 个问题
									</li>
								)}
							</ul>
						</div>
					)}

					{entity.suggestions.length > 0 && (
						<div className="bg-info/10 rounded-md p-2">
							<p className="text-xs font-bold text-info mb-1">改进建议</p>
							<ul className="space-y-1">
								{entity.suggestions.slice(0, 3).map((suggestion, idx) => (
									<li key={idx} className="text-xs text-info/90">
										• {suggestion}
									</li>
								))}
								{entity.suggestions.length > 3 && (
									<li className="text-xs text-base-content/50 italic">
										...还有 {entity.suggestions.length - 3} 条建议
									</li>
								)}
							</ul>
						</div>
					)}

					{entity.failed_checks.length > 0 && (
						<div className="bg-warning/10 rounded-md p-2">
							<p className="text-xs font-bold text-warning mb-1">未通过检查</p>
							<div className="flex flex-wrap gap-1">
								{entity.failed_checks.map((check, idx) => (
									<span key={idx} className="badge badge-xs badge-warning">
										{check}
									</span>
								))}
							</div>
						</div>
					)}
				</div>
			)}
		</div>
	);
}

export function CritiqueResultCard({
	data,
	onConfirm,
	onCancel,
}: CritiqueResultCardProps) {
	const critiqueOverrides = useEditorStore((s) => s.critiqueOverrides);
	const setCritiqueOverride = useEditorStore((s) => s.setCritiqueOverride);
	const clearCritiqueReview = useEditorStore((s) => s.clearCritiqueReview);

	const entityLabel = data.entity_type === "character" ? "角色" : "分镜";

	const anyRegenerate = data.results.some((r) => {
		const override = critiqueOverrides[r.entity_id];
		return override !== undefined ? override : r.will_regenerate;
	});

	const handleSetAllPass = () => {
		for (const entity of data.results) {
			setCritiqueOverride(entity.entity_id, false);
		}
	};

	const handleSetAllRegenerate = () => {
		for (const entity of data.results) {
			setCritiqueOverride(entity.entity_id, true);
		}
	};

	const handleConfirm = () => {
		onConfirm(critiqueOverrides);
	};

	const handleCancel = () => {
		clearCritiqueReview();
		onCancel();
	};

	if (data.results.length === 0) {
		return (
			<div className="card-feature bg-base-100 p-4 space-y-3 text-sm">
				<div>
					<p className="text-[10px] tracking-widest text-base-content/40 font-bold">
						Critique Review
					</p>
					<h3 className="font-heading font-bold text-base">审查完成</h3>
				</div>
				<p className="text-base-content/60">无需审查 — 所有 {entityLabel} 均通过质量检查</p>
				<Button size="sm" variant="primary" onClick={handleConfirm} className="w-full">
					确认
				</Button>
			</div>
		);
	}

	return (
		<div className="card-feature bg-base-100 p-3 space-y-3 text-sm">
			<div>
				<p className="text-[10px] tracking-widest text-base-content/40 font-bold">
					Critique Review
				</p>
				<div className="flex items-center justify-between">
					<h3 className="font-heading font-bold text-base">
						审查完成 — {data.total} 个{entityLabel}
					</h3>
				</div>
			</div>

			<div className="flex gap-2">
				<button
					type="button"
					onClick={handleSetAllPass}
					className="btn btn-xs btn-ghost flex-1"
				>
					<CheckIcon className="w-3 h-3" />
					全部通过
				</button>
				<button
					type="button"
					onClick={handleSetAllRegenerate}
					className="btn btn-xs btn-warning flex-1"
				>
					<ArrowPathIcon className="w-3 h-3" />
					全部重生成
				</button>
			</div>

			<div className="max-h-80 overflow-y-auto space-y-2 pr-1">
				{data.results.map((entity) => (
					<EntityRow
						key={entity.entity_id}
						entity={entity}
						isOverridden={critiqueOverrides[entity.entity_id] !== undefined}
						overrideValue={critiqueOverrides[entity.entity_id]}
						onToggleOverride={setCritiqueOverride}
					/>
				))}
			</div>

			<div className="pt-2 border-t border-base-content/10">
				<div className="flex items-center justify-between text-xs text-base-content/60 mb-2">
					<span>
						{Object.keys(critiqueOverrides).length > 0
							? `已覆盖 ${Object.keys(critiqueOverrides).length} 个判定`
							: "未覆盖任何判定"}
					</span>
					<span>
						{anyRegenerate
							? `将重生成 ${data.results.filter((r) => critiqueOverrides[r.entity_id] !== undefined ? critiqueOverrides[r.entity_id] : r.will_regenerate).length} 个${entityLabel}`
							: "全部通过"}
					</span>
				</div>
				<div className="flex gap-2">
					<Button
						size="sm"
						variant="ghost"
						onClick={handleCancel}
						className="flex-1"
					>
						取消
					</Button>
					<Button
						size="sm"
						variant={anyRegenerate ? "secondary" : "primary"}
						onClick={handleConfirm}
						className="flex-1"
					>
						{anyRegenerate ? "确认并重生成" : "确认"}
					</Button>
				</div>
			</div>
		</div>
	);
}
