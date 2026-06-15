import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { universesApi, projectsApi } from "~/services/api";
import { SharedCharacterCard } from "~/components/universe/SharedCharacterCard";
import { AppShell } from "~/components/layout/AppShell";
import { Button } from "~/components/ui/Button";
import { Card } from "~/components/ui/Card";
import { Modal } from "~/components/ui/Modal";
import {
	ArrowLeftIcon,
	PlusIcon,
	BookOpenIcon,
	TrashIcon,
	GlobeAltIcon,
	PaintBrushIcon,
	UserGroupIcon,
} from "@heroicons/react/24/outline";
import { toast } from "~/utils/toast";
import type { UniverseDetail, Project } from "~/types";

export function UniverseDetailPage() {
	const { universeId } = useParams<{ universeId: string }>();
	const queryClient = useQueryClient();
	const id = Number(universeId);

	const [showAddProject, setShowAddProject] = useState(false);
	const [importTarget, setImportTarget] = useState<{
		sharedCharacterId: number;
		characterName: string;
	} | null>(null);
	const [selectedImportProjectId, setSelectedImportProjectId] = useState<
		number | null
	>(null);

	const { data: universe, isLoading } = useQuery({
		queryKey: ["universe", id],
		queryFn: () => universesApi.get(id),
		enabled: !isNaN(id),
	});

	const { data: projectsData } = useQuery({
		queryKey: ["projects"],
		queryFn: () => projectsApi.list(),
	});

	const addProjectMutation = useMutation({
		mutationFn: ({
			projectId,
			chapterNumber,
			chapterTitle,
		}: {
			projectId: number;
			chapterNumber?: number;
			chapterTitle?: string;
		}) =>
			universesApi.addProject(id, projectId, chapterNumber, chapterTitle),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["universe", id] });
			queryClient.invalidateQueries({ queryKey: ["universes"] });
			setShowAddProject(false);
			toast.success({ title: "已添加", message: "项目已加入宇宙" });
		},
		onError: (error: Error) => {
			toast.error({ title: "添加失败", message: error.message });
		},
	});

	const removeProjectMutation = useMutation({
		mutationFn: (projectId: number) =>
			universesApi.removeProject(id, projectId),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["universe", id] });
			queryClient.invalidateQueries({ queryKey: ["universes"] });
			toast.success({ title: "已移除", message: "项目已从宇宙移除" });
		},
	});

	const importCharacterMutation = useMutation({
		mutationFn: ({
			projectId,
			sharedCharacterId,
		}: {
			projectId: number;
			sharedCharacterId: number;
		}) => universesApi.importCharacter(projectId, sharedCharacterId),
		onSuccess: (_data, variables) => {
			queryClient.invalidateQueries({
				queryKey: ["project", variables.projectId],
			});
			setImportTarget(null);
			setSelectedImportProjectId(null);
			toast.success({ title: "已导入", message: "共享角色已导入到项目" });
		},
		onError: (error: Error) => {
			toast.error({ title: "导入失败", message: error.message });
		},
	});

	if (isLoading) {
		return (
			<div className="min-h-screen bg-base-100 flex items-center justify-center">
				<span className="loading loading-spinner loading-lg text-primary" />
			</div>
		);
	}

	if (!universe) {
		return (
			<div className="min-h-screen bg-base-100 flex items-center justify-center">
				<p className="text-base-content/50">宇宙不存在</p>
			</div>
		);
	}

	const u = universe as UniverseDetail;
	const allProjects = projectsData ?? [];
	const existingProjectIds = new Set(u.chapters.map((c) => c.project_id));
	const availableProjects = allProjects.filter(
		(p: Project) => !existingProjectIds.has(p.id),
	);

	return (
		<AppShell
			variant="default"
			onToggleAssets={() => {}}
			onToggleHistory={() => {}}
			onAssetsClose={() => {}}
			onHistoryClose={() => {}}
			chatIsGenerating={false}
			onChatSendFeedback={() => {}}
			onChatConfirm={() => {}}
			onChatEntityConfirm={() => {}}
			onChatGenerate={() => {}}
			onChatCancel={() => {}}
			versionCompareOpen={false}
			versionCompareProjectId={0}
			onVersionCompareClose={() => {}}
		>
			<main className="container mx-auto px-4 py-8 max-w-6xl">
				{/* Back */}
				<Link
					to="/universes"
					className="btn btn-ghost btn-sm mb-4 inline-flex items-center gap-1"
				>
					<ArrowLeftIcon className="w-4 h-4" />
					返回宇宙列表
				</Link>

				{/* Header */}
				<div className="mb-8">
					<h1 className="text-3xl font-heading font-bold">
						{u.name}
					</h1>
					{u.description && (
						<p className="text-base-content/60 mt-2">{u.description}</p>
					)}
				</div>

				{/* World setting */}
				{u.world_setting && (
					<Card className="mb-6" variant="primary">
						<h2 className="text-lg font-heading font-bold mb-2 flex items-center gap-2">
							<GlobeAltIcon className="w-5 h-5" aria-hidden="true" />
							世界观设定
						</h2>
						<p className="text-sm text-base-content/70 whitespace-pre-wrap">
							{u.world_setting}
						</p>
					</Card>
				)}

				{/* Style rules */}
				{u.style_rules && (
					<Card className="mb-6" variant="accent">
						<h2 className="text-lg font-heading font-bold mb-2 flex items-center gap-2">
							<PaintBrushIcon className="w-5 h-5" aria-hidden="true" />
							统一风格规则
						</h2>
						<p className="text-sm text-base-content/70 whitespace-pre-wrap">
							{u.style_rules}
						</p>
					</Card>
				)}

				{/* Chapters */}
				<Card className="mb-6">
					<div className="flex items-center justify-between mb-4">
						<h2 className="text-lg font-heading font-bold flex items-center gap-2">
							<BookOpenIcon className="w-5 h-5" />
							章节列表
						</h2>
						<Button size="sm" onClick={() => setShowAddProject(true)}>
							<PlusIcon className="w-3.5 h-3.5 mr-1" />
							添加项目
						</Button>
					</div>

					{u.chapters.length === 0 ? (
						<p className="text-sm text-base-content/40 text-center py-8">
							还没有章节，点击"添加项目"开始
						</p>
					) : (
						<div className="space-y-2">
							{u.chapters
								.sort((a, b) =>
									(a.chapter_number ?? 999) - (b.chapter_number ?? 999),
								)
								.map((ch) => (
									<div
										key={ch.id}
										className="flex items-center justify-between p-3 rounded-lg bg-base-200/50 hover:bg-base-200 transition-colors"
									>
										<div className="flex items-center gap-3">
											<span className="badge badge-primary badge-sm font-bold">
												第{ch.chapter_number ?? "?"}章
											</span>
											<Link
												to={`/project/${ch.project_id}`}
												className="font-heading font-bold text-sm hover:text-primary transition-colors"
											>
												{ch.chapter_title || ch.project_title || "未命名"}
											</Link>
											{!ch.is_main_story && (
												<span className="badge badge-ghost badge-xs">外传</span>
											)}
										</div>
										<button
											type="button"
											className="btn btn-ghost btn-xs text-error/50 hover:text-error"
											onClick={() => removeProjectMutation.mutate(ch.project_id)}
										>
											<TrashIcon className="w-3.5 h-3.5" />
										</button>
									</div>
								))}
						</div>
					)}
				</Card>

				{/* Shared Characters */}
				<Card>
					<h2 className="text-lg font-heading font-bold mb-4 flex items-center gap-2">
						<UserGroupIcon className="w-5 h-5" aria-hidden="true" />
						共享角色库
					</h2>

					{u.shared_characters.length === 0 ? (
						<p className="text-sm text-base-content/40 text-center py-8">
							还没有共享角色，从项目角色中提升
						</p>
					) : (
						<div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
							{u.shared_characters.map((sc) => (
								<SharedCharacterCard
									key={sc.id}
									character={sc}
									showImport
									onImport={(character) => {
										setImportTarget({
											sharedCharacterId: character.id,
											characterName: character.name,
										});
										setSelectedImportProjectId(null);
									}}
								/>
							))}
						</div>
					)}
				</Card>
			</main>

			{/* Add Project Modal */}
			{showAddProject && (
				<Modal
					isOpen={showAddProject}
					onClose={() => setShowAddProject(false)}
					title="添加项目到宇宙"
				>
					{availableProjects.length === 0 ? (
						<p className="text-sm text-base-content/50 text-center py-6">
							没有可添加的项目（所有项目已在本宇宙中）
						</p>
					) : (
						<div className="space-y-2 max-h-96 overflow-y-auto">
							{availableProjects.map((p: Project) => (
								<button
									key={p.id}
									type="button"
									className="w-full text-left p-3 rounded-lg bg-base-200/50 hover:bg-base-200 transition-colors flex items-center justify-between"
									onClick={() => {
										const nextChapter =
											u.chapters.length > 0
												? Math.max(...u.chapters.map((c) => c.chapter_number ?? 0)) + 1
												: 1;
										addProjectMutation.mutate({
											projectId: p.id,
											chapterNumber: nextChapter,
											chapterTitle: p.title,
										});
									}}
								>
									<div>
										<span className="font-heading font-bold text-sm">
											{p.title}
										</span>
										<span className="text-xs text-base-content/40 ml-2">
											{p.status}
										</span>
									</div>
									<PlusIcon className="w-4 h-4 text-primary" />
								</button>
							))}
						</div>
					)}

					<div className="flex justify-end pt-4">
						<Button variant="ghost" onClick={() => setShowAddProject(false)}>
							关闭
						</Button>
					</div>
				</Modal>
			)}

			{/* Import Character Modal */}
			{importTarget && (
				<Modal
					isOpen
					onClose={() => {
						setImportTarget(null);
						setSelectedImportProjectId(null);
					}}
					title={`导入 "${importTarget.characterName}" 到项目`}
				>
					<p className="text-sm text-base-content/60 mb-4">
						选择要导入共享角色的目标项目
					</p>
					{allProjects.length === 0 ? (
						<p className="text-sm text-base-content/50 text-center py-6">
							暂无可用项目
						</p>
					) : (
						<div className="space-y-2 max-h-80 overflow-y-auto">
							{allProjects.map((p: Project) => (
								<button
									key={p.id}
									type="button"
									className={`w-full text-left p-3 rounded-lg transition-colors flex items-center justify-between ${
										selectedImportProjectId === p.id
											? "bg-primary/10 border border-primary/30"
											: "bg-base-200/50 hover:bg-base-200"
									}`}
									onClick={() => setSelectedImportProjectId(p.id)}
								>
									<div>
										<span className="font-heading font-bold text-sm">
											{p.title}
										</span>
										<span className="text-xs text-base-content/40 ml-2">
											{p.status}
										</span>
									</div>
								</button>
							))}
						</div>
					)}

					<div className="flex justify-end gap-2 pt-4">
						<Button
							variant="ghost"
							onClick={() => {
								setImportTarget(null);
								setSelectedImportProjectId(null);
							}}
						>
							取消
						</Button>
						<Button
							disabled={
								!selectedImportProjectId ||
								importCharacterMutation.isPending
							}
							onClick={() => {
								if (selectedImportProjectId) {
									importCharacterMutation.mutate({
										projectId: selectedImportProjectId,
										sharedCharacterId:
											importTarget.sharedCharacterId,
									});
								}
							}}
						>
							{importCharacterMutation.isPending
								? "导入中..."
								: "确认导入"}
						</Button>
					</div>
				</Modal>
			)}
		</AppShell>
	);
}
