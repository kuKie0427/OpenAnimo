import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assetsApi, getStaticUrl } from "~/services/api";
import { Button } from "~/components/ui/Button";
import { SvgIcon } from "~/components/ui/SvgIcon";
import type { Asset } from "~/types";
import type { IconName } from "~/components/ui/SvgIcon";

type AssetType = "character" | "scene";

const ASSET_TABS: { key: AssetType | "all"; label: string; icon: IconName }[] =
	[
		{ key: "all", label: "全部", icon: "layers" },
		{ key: "character", label: "角色", icon: "star" },
		{ key: "scene", label: "场景", icon: "image" },
	];

interface AssetDrawerProps {
	open: boolean;
	onClose: () => void;
	/** 当前项目 ID — 传入时显示"使用"按钮 */
	projectId?: number;
}

function AssetCard({
	asset,
	projectId,
	onDelete,
	onUse,
	isUsing,
}: {
	asset: Asset;
	projectId?: number;
	onDelete: (id: number) => void;
	onUse: (asset: Asset) => void;
	isUsing: boolean;
}) {
	return (
		<div className="card card-compact bg-base-200 border border-base-content/10 hover:border-primary/40 transition-colors">
			<figure className="h-32 bg-base-300 overflow-hidden">
				{asset.image_url ? (
					<img
						src={getStaticUrl(asset.image_url) ?? undefined}
						alt={asset.name}
						className="w-full h-full object-cover"
						loading="lazy"
					/>
				) : (
					<div className="flex items-center justify-center w-full h-full text-base-content/20">
						<SvgIcon name="image" size={32} />
					</div>
				)}
			</figure>
			<div className="card-body p-2 gap-1">
				<div className="flex items-center gap-1">
					<span className="badge badge-xs badge-outline shrink-0">
						{asset.asset_type === "character"
							? "角色"
							: asset.asset_type === "scene"
								? "场景"
								: "风格"}
					</span>
					<h4 className="text-xs font-bold flex-1 truncate">{asset.name}</h4>
				</div>
				{asset.description && (
					<p className="text-xs text-base-content/50 line-clamp-2">
						{asset.description}
					</p>
				)}
				<div className="flex items-center justify-end gap-1 mt-0.5">
					{projectId &&
						(asset.asset_type === "character" ||
							asset.asset_type === "scene") && (
							<Button
								variant="ghost"
								size="sm"
								className="!px-1.5 !py-0 !min-h-0 !h-5 text-xs text-primary hover:text-primary-focus"
								onClick={() => onUse(asset)}
								disabled={isUsing}
								title="添加到当前项目"
							>
								<SvgIcon name="plus" size={10} className="mr-0.5" />
								使用
							</Button>
						)}
					<Button
						variant="ghost"
						size="sm"
						className="!px-1 !py-0 !min-h-0 !h-5 text-xs text-error/60 hover:text-error"
						onClick={() => onDelete(asset.id)}
						title="删除资产"
					>
						<SvgIcon name="x" size={12} />
					</Button>
				</div>
			</div>
		</div>
	);
}

export function AssetDrawer({ open, onClose, projectId }: AssetDrawerProps) {
	const queryClient = useQueryClient();
	const [activeTab, setActiveTab] = useState<AssetType | "all">("all");
	const [search, setSearch] = useState("");

	const assetType = activeTab === "all" ? undefined : activeTab;

	const { data, isLoading } = useQuery({
		queryKey: ["assets", assetType, search],
		queryFn: () => assetsApi.list({ assetType, search: search || undefined }),
		enabled: open,
	});

	const deleteMutation = useMutation({
		mutationFn: (id: number) => assetsApi.delete(id),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assets"] }),
	});

	const useMutation_ = useMutation({
		mutationFn: (asset: Asset) => assetsApi.useInProject(asset.id, projectId!),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["assets"] });
			if (projectId) {
				queryClient.invalidateQueries({
					queryKey: ["project", projectId, "characters"],
				});
				queryClient.invalidateQueries({
					queryKey: ["project", projectId, "shots"],
				});
			}
		},
	});

	const items = data?.items ?? [];

	return (
		<>
			{open && (
				<div className="fixed inset-0 bg-black/30 z-drawer-backdrop" onClick={onClose} />
			)}
			<div
				className={`fixed right-0 top-0 h-full w-80 lg:w-96 bg-base-100 border-l border-base-content/15 z-drawer transform transition-transform duration-200 ${open ? "translate-x-0" : "translate-x-full"}`}
			>
				{/* Header */}
				<div className="flex items-center justify-between p-3 border-b border-base-content/10">
					<div className="flex items-center gap-1.5">
						<SvgIcon name="archive" size={16} className="text-primary" />
						<h3 className="text-sm font-bold">资产库</h3>
						<span className="badge badge-xs badge-ghost">
							{data?.total ?? 0}
						</span>
					</div>
					<Button
						variant="ghost"
						size="sm"
						className="!px-1 !min-h-0 !h-6"
						onClick={onClose}
					>
						<SvgIcon name="x" size={14} />
					</Button>
				</div>

				{/* Tabs */}
				<div className="flex border-b-2 border-base-content/10">
					{ASSET_TABS.map((tab) => (
						<button
							key={tab.key}
							className={`flex-1 flex items-center justify-center gap-1 py-2 text-xs font-medium transition-colors border-b-2 -mb-[2px] ${
								activeTab === tab.key
									? "border-primary text-primary"
									: "border-transparent text-base-content/50 hover:text-base-content/80"
							}`}
							onClick={() => setActiveTab(tab.key)}
						>
							<SvgIcon name={tab.icon} size={12} />
							{tab.label}
						</button>
					))}
				</div>

				{/* Search */}
				<div className="px-3 pt-2">
					<input
						type="text"
						placeholder="搜索资产名称…"
						className="input input-xs input-bordered w-full text-xs"
						value={search}
						onChange={(e) => setSearch(e.target.value)}
					/>
				</div>

				{/* Content */}
				<div
					className="p-3 overflow-y-auto"
					style={{ height: "calc(100vh - 160px)" }}
				>
					{isLoading ? (
						<div className="flex items-center justify-center py-8">
							<span className="loading loading-spinner loading-sm text-primary" />
						</div>
					) : items.length === 0 ? (
						<div className="text-center text-xs text-base-content/40 py-8">
							<SvgIcon
								name="layers"
								size={24}
								className="mx-auto mb-2 text-base-content/15"
							/>
							{search ? (
								<p>没有匹配的资产</p>
							) : (
								<>
									<p>还没有保存的资产</p>
									<p className="text-base-content/25 mt-1">
										在画布角色卡片点击{" "}
										<SvgIcon name="star" size={10} className="inline" /> 可添加
									</p>
								</>
							)}
						</div>
					) : (
						<div className="grid grid-cols-2 gap-2">
							{items.map((a) => (
								<AssetCard
									key={a.id}
									asset={a}
									projectId={projectId}
									onDelete={(id) => deleteMutation.mutate(id)}
									onUse={(asset) => useMutation_.mutate(asset)}
									isUsing={useMutation_.isPending}
								/>
							))}
						</div>
					)}
				</div>
			</div>
		</>
	);
}
