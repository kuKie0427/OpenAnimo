import { useQuery } from "@tanstack/react-query";
import { versionsApi } from "~/services/api";
import type { VersionEntityType } from "~/types";
import { VersionColumn, DiffRow } from "~/components/panels/VersionCompareDrawer";
import { SvgIcon } from "~/components/ui/SvgIcon";

interface VersionCompareInlineProps {
	projectId: number;
	entityType: VersionEntityType;
	entityId: number;
	onClose?: () => void;
}

const LABELS: Record<string, string> = {
	name: "名称",
	character: "角色",
	shot: "分镜",
};

export function VersionCompareInline({
	projectId,
	entityType,
	entityId,
	onClose,
}: VersionCompareInlineProps) {
	const versionsQuery = useQuery({
		queryKey: ["versions", projectId, entityType, entityId],
		queryFn: () => versionsApi.list(projectId, entityType, entityId),
		enabled: projectId > 0 && entityId > 0,
	});

	const versions = versionsQuery.data?.versions ?? [];
	const latestVersion = versions[0];
	const previousVersion = versions[1];

	const compareQuery = useQuery({
		queryKey: ["versions", "compare", projectId, entityType, entityId, previousVersion?.version, latestVersion?.version],
		queryFn: () =>
			versionsApi.compare(
				projectId,
				entityType,
				entityId,
				previousVersion?.version ?? 1,
				latestVersion?.version ?? 1,
				),
		enabled: Boolean(previousVersion && latestVersion),
	});

	const entityName = latestVersion?.snapshot?.name as string | undefined;
	const displayName = entityName || `${LABELS[entityType] || entityType} #${entityId}`;

	if (versionsQuery.isLoading) {
		return (
			<div className="rounded-box border border-base-content/10 bg-base-200/40 p-4">
				<div className="flex items-center gap-2 text-sm text-base-content/60">
					<span className="loading loading-spinner loading-xs" />
					加载版本中...
				</div>
			</div>
		);
	}

	if (versionsQuery.isError) {
		return (
			<div className="rounded-box border border-base-content/10 bg-base-200/40 p-4">
				<div className="text-sm text-error">
					加载失败: {versionsQuery.error instanceof Error ? versionsQuery.error.message : "未知错误"}
				</div>
			</div>
		);
	}

	if (versions.length <= 1) {
		return (
			<div className="rounded-box border border-base-content/10 bg-base-200/40 p-4">
				<div className="text-sm text-base-content/60">暂无历史版本</div>
			</div>
		);
	}

	return (
		<div className="rounded-box border border-base-content/10 bg-base-200/40 p-3">
			<div className="mb-3 flex items-center justify-between">
				<div className="flex items-center gap-2">
					<SvgIcon name="clock-3" size={16} className="text-base-content/60" />
					<span className="font-heading text-sm font-bold">
						版本对比: {displayName} (v{previousVersion?.version} → v{latestVersion?.version})
					</span>
				</div>
				{onClose && (
					<button
						type="button"
						className="btn btn-ghost btn-xs"
						onClick={onClose}
						aria-label="关闭"
					>
						<SvgIcon name="x" size={14} />
					</button>
				)}
			</div>

			<div className="mb-3 grid gap-3 md:grid-cols-2">
				<VersionColumn
					title={`旧版本 v${previousVersion?.version ?? "—"}`}
					version={previousVersion}
				/>
				<VersionColumn
					title={`新版本 v${latestVersion?.version ?? "—"}`}
					version={latestVersion}
				/>
			</div>

			<div className="border-t-2 border-base-content/10 pt-3">
				<div className="mb-2 font-heading text-xs font-bold text-base-content/60">差异</div>
				{compareQuery.isLoading && (
					<div className="text-xs text-base-content/60">计算差异中...</div>
				)}
				{compareQuery.isError && (
					<div className="text-xs text-error">
						对比失败: {compareQuery.error instanceof Error ? compareQuery.error.message : "未知错误"}
					</div>
				)}
				{!compareQuery.isLoading && !compareQuery.isError && (
					<div className="max-h-48 overflow-y-auto">
						{(compareQuery.data?.diffs.length ?? 0) === 0 ? (
							<div className="text-xs text-base-content/60">两个版本内容相同。</div>
						) : (
							<ul className="space-y-2">
								{compareQuery.data?.diffs.map((diff) => (
									<DiffRow key={diff.field_name} diff={diff} />
								))}
							</ul>
						)}
					</div>
				)}
			</div>
		</div>
	);
}
