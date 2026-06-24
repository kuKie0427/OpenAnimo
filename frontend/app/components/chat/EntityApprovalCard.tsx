import { useState, useMemo } from "react";
import { Button } from "~/components/ui/Button";
import { CheckIcon, XMarkIcon } from "@heroicons/react/24/outline";
import type { EntitySummary, EntityDecision } from "~/types";

interface EntityApprovalCardProps {
	entityType: "character" | "shot";
	entityLabel: string;
	entities: EntitySummary[];
	onConfirm: (decisions: EntityDecision[]) => void;
	onRegenerate: (decisions: EntityDecision[]) => void;
}

interface EntityRowProps {
	entity: EntitySummary;
	decision: EntityDecision;
	onToggleApprove: (entityId: number, approved: boolean) => void;
	isExpanded: boolean;
	onToggleExpand: (entityId: number) => void;
	onFeedbackChange: (entityId: number, feedback: string) => void;
}

function truncateText(text: string, maxLength: number): string {
	if (text.length <= maxLength) return text;
	return `${text.slice(0, maxLength)}...`;
}

function EntityRow({
	entity,
	decision,
	onToggleApprove,
	isExpanded,
	onToggleExpand,
	onFeedbackChange,
}: EntityRowProps) {
	const [imageError, setImageError] = useState(false);

	return (
		<div className="bg-base-200/50 rounded-lg p-3 space-y-2">
			<div className="flex items-center gap-3">
				<div className="flex-shrink-0">
					{entity.image_url && !imageError ? (
						<img
							src={entity.image_url}
							alt={entity.entity_name}
							className="w-12 h-12 rounded-lg object-cover"
							onError={() => setImageError(true)}
						/>
					) : (
						<div className="w-12 h-12 rounded-lg bg-base-300 flex items-center justify-center">
							<span className="text-lg font-bold text-base-content/50">
								{entity.entity_name.charAt(0).toUpperCase()}
							</span>
						</div>
					)}
				</div>

				<div className="flex-1 min-w-0">
					<h4 className="font-bold text-sm truncate">{entity.entity_name}</h4>
					{entity.description && (
						<p className="text-xs text-base-content/60 truncate">
							{truncateText(entity.description, 60)}
						</p>
					)}
				</div>

			<div className="flex items-center gap-1">
				{entity.approval_state === "approved" ? (
					<span className="badge badge-success badge-sm gap-1">
						<CheckIcon className="w-3 h-3" />
						已确认
					</span>
				) : (
					<>
						<button
							type="button"
							onClick={() => onToggleApprove(entity.entity_id, true)}
							className={`btn btn-xs gap-1 ${
								decision.approved
									? "btn-success"
									: "btn-ghost text-base-content/30"
							}`}
							aria-label="通过"
							aria-pressed={decision.approved}
						>
							<CheckIcon className="w-3 h-3" />
						</button>
						<button
							type="button"
							onClick={() => onToggleApprove(entity.entity_id, false)}
							className={`btn btn-xs gap-1 ${
								!decision.approved
									? "btn-error"
									: "btn-ghost text-base-content/30"
							}`}
							aria-label="拒绝"
							aria-pressed={!decision.approved}
						>
							<XMarkIcon className="w-3 h-3" />
						</button>
					</>
				)}
			</div>
			</div>

			<div className="flex items-center justify-between pt-1">
				<button
					type="button"
					onClick={() => onToggleExpand(entity.entity_id)}
					className="btn btn-ghost btn-xs px-0 min-h-0 h-auto text-xs text-base-content/50 hover:text-base-content"
				>
					{isExpanded ? "收起反馈" : "添加反馈"}
				</button>
			</div>

			{isExpanded && (
				<div className="pt-1">
					<textarea
						value={decision.feedback || ""}
						onChange={(e) => onFeedbackChange(entity.entity_id, e.target.value)}
						placeholder="对此实体的修改意见..."
						className="textarea textarea-bordered textarea-xs w-full"
						rows={2}
					/>
				</div>
			)}
		</div>
	);
}

export function EntityApprovalCard({
	entityType: _entityType,
	entityLabel,
	entities,
	onConfirm,
	onRegenerate,
}: EntityApprovalCardProps) {
	const [decisions, setDecisions] = useState<Map<number, EntityDecision>>(
		new Map(
			entities.map((e) => [
				e.entity_id,
				{ entity_id: e.entity_id, approved: true },
			])
		)
	);
	const [expandedFeedback, setExpandedFeedback] = useState<Set<number>>(
		new Set()
	);

	const approvedCount = useMemo(() => {
		return Array.from(decisions.values()).filter((d) => d.approved).length;
	}, [decisions]);

	const totalCount = entities.length;
	const hasApproved = approvedCount > 0;

	const handleToggleApprove = (entityId: number, approved: boolean) => {
		setDecisions((prev) => {
			const next = new Map(prev);
			const existing = next.get(entityId);
			if (existing) {
				next.set(entityId, { ...existing, approved });
			}
			return next;
		});
	};

	const handleToggleExpand = (entityId: number) => {
		setExpandedFeedback((prev) => {
			const next = new Set(prev);
			if (next.has(entityId)) {
				next.delete(entityId);
			} else {
				next.add(entityId);
			}
			return next;
		});
	};

	const handleFeedbackChange = (entityId: number, feedback: string) => {
		setDecisions((prev) => {
			const next = new Map(prev);
			const existing = next.get(entityId);
			if (existing) {
				next.set(entityId, { ...existing, feedback });
			}
			return next;
		});
	};

	const handleSetAllPass = () => {
		setDecisions((prev) => {
			const next = new Map(prev);
			for (const [entityId, decision] of next) {
				// Skip already-approved entities
				const entity = entities.find((e) => e.entity_id === entityId);
				if (entity?.approval_state === "approved") continue;
				next.set(entityId, { ...decision, approved: true });
			}
			return next;
		});
	};

	const handleSetAllReject = () => {
		setDecisions((prev) => {
			const next = new Map(prev);
			for (const [entityId, decision] of next) {
				// Skip already-approved entities
				const entity = entities.find((e) => e.entity_id === entityId);
				if (entity?.approval_state === "approved") continue;
				next.set(entityId, { ...decision, approved: false });
			}
			return next;
		});
	};

	const handleConfirm = () => {
		const decisionsArray = Array.from(decisions.values());
		onConfirm(decisionsArray);
	};

	const handleRegenerate = () => {
		const decisionsArray = Array.from(decisions.values());
		onRegenerate(decisionsArray);
	};

	if (entities.length === 0) {
		return (
			<div className="card-feature bg-base-100 p-4 space-y-3 text-sm">
				<div>
					<p className="text-[10px] tracking-widest text-base-content/40 font-bold">
						{entityLabel}审批
					</p>
					<h3 className="font-heading font-bold text-base">
						无可审批的{entityLabel}
					</h3>
				</div>
				<p className="text-base-content/60 text-xs">
					当前没有需要审批的{entityLabel}，请继续下一步操作。
				</p>
			</div>
		);
	}

	return (
		<div className="card-feature bg-base-100 p-3 space-y-3 text-sm">
			<div>
				<p className="text-[10px] tracking-widest text-base-content/40 font-bold">
					{entityLabel}审批
				</p>
				<div className="flex items-center justify-between">
					<h3 className="font-heading font-bold text-base">
						{entityLabel}审批 ({approvedCount}/{totalCount} 已确认)
					</h3>
				</div>
			</div>

			<div className="flex items-center gap-2">
				<button
					type="button"
					onClick={handleSetAllPass}
					className="btn btn-ghost btn-xs flex-1"
				>
					<CheckIcon className="w-3 h-3" />
					全部通过
				</button>
				<button
					type="button"
					onClick={handleSetAllReject}
					className="btn btn-ghost btn-xs flex-1"
				>
					<XMarkIcon className="w-3 h-3" />
					全部拒绝
				</button>
			</div>

			<div className="max-h-80 overflow-y-auto space-y-2 pr-1">
				{entities.map((entity) => (
					<EntityRow
						key={entity.entity_id}
						entity={entity}
						decision={
							decisions.get(entity.entity_id) || {
								entity_id: entity.entity_id,
								approved: true,
							}
						}
						onToggleApprove={handleToggleApprove}
						isExpanded={expandedFeedback.has(entity.entity_id)}
						onToggleExpand={handleToggleExpand}
						onFeedbackChange={handleFeedbackChange}
					/>
				))}
			</div>

			<div className="pt-2 border-t border-base-content/10">
				<div className="flex items-center justify-between text-xs text-base-content/60 mb-2">
					<span>
						{approvedCount === totalCount
							? "全部通过"
							: `${totalCount - approvedCount} 个待修改`}
					</span>
					<span>
						{expandedFeedback.size > 0
							? `${expandedFeedback.size} 个已添加反馈`
							: ""}
					</span>
				</div>
				<div className="flex gap-2">
					<Button
						size="sm"
						variant="ghost"
						onClick={handleRegenerate}
						className="flex-1"
					>
						重新生成
					</Button>
					<Button
						size="sm"
						variant="primary"
						onClick={handleConfirm}
						disabled={!hasApproved}
						className="flex-1 gap-0.5 !px-2.5 !py-0.5 !min-h-0 !h-6 text-xs border shadow-aperture"
					>
						<CheckIcon className="w-3 h-3" />
						确认并继续 →
					</Button>
				</div>
			</div>
		</div>
	);
}
