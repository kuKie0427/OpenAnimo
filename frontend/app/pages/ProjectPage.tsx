import { ArrowPathIcon, StopIcon } from "@heroicons/react/24/outline";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import {
	Link,
	useNavigate,
	useParams,
	useSearchParams,
} from "react-router-dom";
import { ViewSwitcher } from "~/components/daw/ViewSwitcher";
import { TimelineView } from "~/components/timeline";
import { AppShell } from "~/components/layout/AppShell";
import { StageView } from "~/components/layout/StageView";
import { Button } from "~/components/ui/Button";
import { Card } from "~/components/ui/Card";
import { useViewStore } from "~/stores/viewStore";
import { useProjectWebSocket } from "~/hooks/useWebSocket";
import { canvasEvents } from "~/components/canvas/canvasEvents";
import { projectsApi } from "~/services/api";
import { useEditorStore, useShallow } from "~/stores/editorStore";
import type { ProjectProviderSettings, RecoveryControlRead, VersionEntityType } from "~/types";
import { ApiError } from "~/types/errors";
import { toast } from "~/utils/toast";
import { isWorkflowStage } from "~/utils/workflowStage";

export function ProjectPage() {
	const { id } = useParams<{ id: string }>();
	const navigate = useNavigate();
	const [searchParams, setSearchParams] = useSearchParams();
	const projectId = parseInt(id || "0", 10);
	const queryClient = useQueryClient();
	const {
		isGenerating: storeIsGenerating,
		currentRunId: storeCurrentRunId,
		currentStage: storeCurrentStage,
		awaitingConfirm: storeAwaitingConfirm,
		recoveryControl: storeRecoveryControl,
	} = useEditorStore(
		useShallow((s) => ({
			isGenerating: s.isGenerating,
			currentRunId: s.currentRunId,
			currentStage: s.currentStage,
			awaitingConfirm: s.awaitingConfirm,
			recoveryControl: s.recoveryControl,
		})),
	);
	const hasActiveRun = storeIsGenerating || Boolean(storeCurrentRunId);
	const hasRecovery = Boolean(storeRecoveryControl);
	const [assetsOpen, setAssetsOpen] = useState(false);
	const [historyOpen, setHistoryOpen] = useState(false);
	const [versionOpen, setVersionOpen] = useState(false);
	const [versionTarget, setVersionTarget] = useState<{
		entityType: VersionEntityType;
		entityId: number;
	} | null>(null);
	const autoStartTriggered = useRef(false);
	const generateRequestTokenRef = useRef(0);
	const retryCount = useRef(0);
	const [_selectedShapeId, setSelectedShapeId] = useState<string | null>(null);
	const { viewMode, setViewMode } = useViewStore();

	const { send } = useProjectWebSocket(projectId);

	useEffect(() => {
		return canvasEvents.on("version-history", (target) => {
			setVersionTarget({ entityType: target.entityType, entityId: target.entityId });
			setVersionOpen(true);
		});
	}, []);

	const syncStoreWithActiveRun = (run: {
		id: number;
		current_agent?: string | null;
		progress?: number | null;
		provider_snapshot?: ProjectProviderSettings | null;
	}) => {
		const s = useEditorStore.getState();
		s.setGenerating(true);
		s.setCurrentRunId(run.id);
		s.setCurrentAgent(run.current_agent ?? "orchestrator");
		s.setProgress(typeof run.progress === "number" ? run.progress : 0);
		s.setCurrentRunProviderSnapshot(run.provider_snapshot ?? null);
		s.setAwaitingConfirm(false, null, run.id);
		s.setRecoveryControl(null);
		s.setRecoverySummary(null);
		s.setRecoveryGate(null);
	};

	const {
		data: project,
		isLoading: projectLoading,
		error: projectError,
	} = useQuery({
		queryKey: ["project", projectId],
		queryFn: () => projectsApi.get(projectId),
		enabled: projectId > 0,
		retry: 1,
	});

	useEffect(() => {
		if (projectError) {
			const apiError = projectError instanceof ApiError ? projectError : null;
			toast.error({
				title: "无法加载项目",
				message: apiError?.message || "项目数据获取失败，请重试",
				actions: [
					{
						label: "重试",
						onClick: () =>
							queryClient.invalidateQueries({
								queryKey: ["project", projectId],
							}),
					},
				],
			});
		}
	}, [projectError, projectId, queryClient]);

	const { data: characters } = useQuery({
		queryKey: ["characters", projectId],
		queryFn: () => projectsApi.getCharacters(projectId),
		enabled: !!project,
	});

	const { data: shots } = useQuery({
		queryKey: ["shots", projectId],
		queryFn: () => projectsApi.getShots(projectId),
		enabled: !!project,
	});

	const { data: messages } = useQuery({
		queryKey: ["messages", projectId],
		queryFn: () => projectsApi.getMessages(projectId),
		enabled: !!project,
	});

	useEffect(() => {
		if (characters) {
			useEditorStore.getState().setCharacters(characters);
		}
	}, [characters]);

	useEffect(() => {
		if (shots) {
			useEditorStore.getState().setShots(shots);
		}
	}, [shots]);

	useEffect(() => {
		if (project) {
			const editorStore = useEditorStore.getState();
			editorStore.setProjectVideoUrl(project.video_url ?? null);
			editorStore.setProjectStatus(project.status ?? null);
			editorStore.setProjectTitle(project.title ?? null);
			editorStore.setProjectSummary(project.summary ?? null);
			editorStore.setProjectStory(project.story ?? null);
			editorStore.setProjectStyle(project.style ?? null);
			editorStore.setProjectTargetShotCount(project.target_shot_count ?? null);
			editorStore.setProjectCharacterHints(project.character_hints ?? null);
			editorStore.setProjectCreationMode(project.creation_mode ?? null);
			editorStore.setProjectReferenceImages(project.reference_images ?? null);
			editorStore.setProjectExports(project.exports ?? null);
			editorStore.setProjectProviderSettings(project.provider_settings ?? null);
			editorStore.setProjectUniverseId(project.universe_id ?? null);
			editorStore.setProjectChapterNumber(project.chapter_number ?? null);
			editorStore.setProjectChapterTitle(project.chapter_title ?? null);
			editorStore.setProjectStoryOutline(project.story_outline ?? null);
			editorStore.setProjectVisualBible(project.visual_bible ?? null);
			editorStore.setProjectOutlineApproved(project.outline_approved ?? false);
		}
	}, [project]);

	useEffect(() => {
		if (projectId <= 0) return;

		generateRequestTokenRef.current += 1;
		const editorStore = useEditorStore.getState();

		editorStore.clearMessages();
		editorStore.resetRunState();
		editorStore.setCurrentStage("plan");
		editorStore.setSelectedShot(null);
		editorStore.setSelectedCharacter(null);
		editorStore.setHighlightedMessage(null);
		editorStore.setProjectVideoUrl(null);
	}, [projectId]);

	const messagesLoadedRef = useRef(false);
	useEffect(() => {
		if (messages && !messagesLoadedRef.current) {
			messagesLoadedRef.current = true;
			const editorStore = useEditorStore.getState();
			messages.forEach((msg) => {
				editorStore.addMessage({
					id: `db_${msg.id}`,
					agent: msg.agent,
					role: msg.role,
					content: msg.content,
					timestamp: msg.created_at,
					progress: msg.progress ?? undefined,
					// 从数据库加载的消息不再显示为加载中
					isLoading: false,
				});
			});
		}
	}, [messages]);

	const generateMutation = useMutation({
		mutationFn: ({ requestToken }: { requestToken: number }) => {
			const editorState = useEditorStore.getState();
			const gateModes = editorState.gateModes;
			const body = gateModes.size > 0
				? { gate_modes: [...gateModes] }
				: { auto_mode: editorState.runMode === "yolo" };
			return projectsApi
				.generate(projectId, body)
				.then((run) => ({ run, requestToken }));
		},
		onSuccess: ({ run, requestToken }) => {
			if (requestToken !== generateRequestTokenRef.current) return;
			syncStoreWithActiveRun(run);
			retryCount.current = 0;
		},
		onError: async (error: Error | ApiError, variables) => {
			if (variables?.requestToken !== generateRequestTokenRef.current) return;
			const apiError = error instanceof ApiError ? error : null;
			const isConflict =
				apiError?.status === 409 || error.message.includes("409");

			if (isConflict) {
				retryCount.current = 0;
				const control = apiError?.response as RecoveryControlRead | undefined;
				if (control) {
					useEditorStore.getState().setRecoveryControl(control);
					useEditorStore
						.getState()
						.setRecoverySummary(control.recovery_summary);
					useEditorStore.getState().setCurrentRunId(control.active_run.id);
					useEditorStore.getState().setGenerating(control.state === "active");
					if (control.state === "active") {
						useEditorStore
							.getState()
							.setCurrentAgent(control.active_run.current_agent);
						useEditorStore.getState().setProgress(control.active_run.progress);
					}
				} else {
					toast.warning({
						title: "请稍等片刻",
						message: "另一个任务正在进行，完成后再试",
					});
				}
			} else {
				toast.error({
					title: "生成失败",
					message:
						apiError?.message ||
						error.message ||
						"生成过程出错，请重试或联系支持",
					details: import.meta.env.DEV
						? JSON.stringify(apiError?.details)
						: undefined,
				});
			}
		},
	});

	const storeCurrentAgent = useEditorStore((s) => s.currentAgent);

	const feedbackMutation = useMutation({
		mutationFn: (content: string) =>
			projectsApi.feedback(
				projectId,
				content,
				undefined,
				storeCurrentAgent ?? "plan",
			),
		onError: (error: Error | ApiError) => {
			const apiError = error instanceof ApiError ? error : null;
			const isConflict =
				apiError?.status === 409 || error.message.includes("409");

			if (isConflict) {
				toast.info({
					title: "AI 正在思考",
					message: "请等待当前任务完成",
				});
			} else {
				toast.error({
					title: "提交失败",
					message: apiError?.message || error.message || "无法发送反馈，请重试",
				});
			}
		},
	});

	const cancelMutation = useMutation({
		mutationFn: () => projectsApi.cancel(projectId),
		onSettled: () => {
			useEditorStore.getState().resetRunState();
			useEditorStore.getState().addMessage({
				agent: "system",
				role: "system",
				content: "生成已停止",
				icon: StopIcon,
				timestamp: new Date().toISOString(),
			});
		},
	});

	const resumeMutation = useMutation({
		mutationFn: () => {
			const control = storeRecoveryControl;
			if (!control) {
				throw new Error("没有可恢复的运行");
			}
			return projectsApi.resume(projectId, control.active_run.id);
		},
		onSuccess: (run) => {
			const control = storeRecoveryControl;
			const s = useEditorStore.getState();
			s.setGenerating(true);
			s.setCurrentRunId(run.id);
			s.setCurrentAgent(run.current_agent);
			s.setProgress(run.progress);
			s.setCurrentRunProviderSnapshot(run.provider_snapshot ?? null);
			if (control) {
				const nextStage =
					control.recovery_summary.next_stage ??
					control.recovery_summary.current_stage;
				if (isWorkflowStage(nextStage)) {
					s.setCurrentStage(nextStage);
				}
			}
			s.setRecoveryControl(null);
			s.setRecoverySummary(null);
			s.setRecoveryGate(null);
		},
		onError: (error: Error | ApiError) => {
			const apiError = error instanceof ApiError ? error : null;
			toast.error({
				title: "恢复失败",
				message:
					apiError?.message || error.message || "无法恢复当前运行，请重试",
			});
		},
	});

	const handleGenerate = async () => {
		if (generateMutation.isPending || hasActiveRun) return;
		const requestToken = generateRequestTokenRef.current + 1;
		generateRequestTokenRef.current = requestToken;
		useEditorStore.getState().clearMessages();
		useEditorStore.getState().setCurrentStage("plan");
		generateMutation.mutate({ requestToken });
	};

	const handleFeedback = (content: string) => {
		feedbackMutation.mutate(content);
		useEditorStore.getState().addMessage({
			agent: "user",
			role: "user",
			content,
			timestamp: new Date().toISOString(),
		});
	};

	const handleConfirm = (feedback?: string) => {
		const runId = storeCurrentRunId;
		if (runId) {
			send({ type: "confirm", data: { run_id: runId, feedback } });
			if (feedback) {
				useEditorStore.getState().addMessage({
					agent: "user",
					role: "user",
					content: feedback,
					timestamp: new Date().toISOString(),
				});
			}
		}
	};

	const handleEntityConfirm = (decisions: Array<{ entity_id: number; approved: boolean; feedback?: string }>) => {
		const runId = storeCurrentRunId;
		if (runId) {
			send({ type: "confirm", data: { run_id: runId, entity_decisions: decisions } });
		}
	};

	const handleCancel = () => {
		const activeRunId =
			storeCurrentRunId ?? storeRecoveryControl?.active_run.id ?? null;
		if (
			!activeRunId &&
			!storeIsGenerating &&
			storeRecoveryControl?.state !== "active"
		) {
			return;
		}
		generateRequestTokenRef.current += 1;
		cancelMutation.mutate();
	};

	const handleResume = () => {
		if (!storeRecoveryControl) return;
		resumeMutation.mutate();
	};

	useEffect(() => {
		if (!storeIsGenerating) {
			const progress = useEditorStore.getState().progress;
			if (progress === 1) {
				queryClient.invalidateQueries({ queryKey: ["characters", projectId] });
				queryClient.invalidateQueries({ queryKey: ["shots", projectId] });
			}
		}
	}, [storeIsGenerating, projectId, queryClient]);

	const projectUpdatedAt = useEditorStore((state) => state.projectUpdatedAt);
	useEffect(() => {
		if (projectUpdatedAt) {
			queryClient.invalidateQueries({ queryKey: ["project", projectId] });
			queryClient.invalidateQueries({ queryKey: ["projects"] });
		}
	}, [projectUpdatedAt, projectId, queryClient]);

	useEffect(() => {
		const autoStart = searchParams.get("autoStart");
		if (
			autoStart === "true" &&
			project &&
			!autoStartTriggered.current &&
			!hasActiveRun
		) {
			const editorStore = useEditorStore.getState();
			autoStartTriggered.current = true;
			setSearchParams({}, { replace: true });
			const requestToken = generateRequestTokenRef.current + 1;
			generateRequestTokenRef.current = requestToken;
			editorStore.clearMessages();
			editorStore.setCurrentStage("plan");
			generateMutation.mutate({ requestToken });
		}
	}, [project, searchParams, setSearchParams, generateMutation]);

	const timelineShapes = useMemo(() => {
		const shapes: Array<{
			id: string;
			type: string;
			x: number;
			y: number;
			content: any;
		}> = [];

		if (characters) {
			characters.forEach((c: any, i: number) => {
				shapes.push({
					id: `char_${c.id}`,
					type: "character-section",
					x: i * 200,
					y: 0,
					content: { name: c.name, avatarUrl: c.image_url, ...c },
				});
			});
		}

		if (shots) {
			(shots as any[]).forEach((s: any, i: number) => {
				shapes.push({
					id: `shot_${s.id}`,
					type: "storyboard-section",
					x: i * 200,
					y: 100,
					content: { imageUrl: s.image_url, ...s },
				});
			});
		}

		return shapes;
	}, [characters, shots]);

	if (projectLoading) {
		return (
			<div className="min-h-screen flex items-center justify-center flex-col gap-4 bg-base-100">
				<ArrowPathIcon className="w-6 h-6 animate-pulse text-base-content/60" />
				<p className="font-heading text-2xl text-base-content/80">
					正在加载项目...
				</p>
			</div>
		);
	}

	if (!project) {
		return (
			<div className="min-h-screen flex items-center justify-center bg-base-100">
				<Card className="text-center">
					<h1 className="text-2xl font-heading font-bold mb-4">项目未找到</h1>
					<Link to="/">
						<Button variant="primary">返回首页</Button>
					</Link>
				</Card>
			</div>
		);
	}

	return (
		<AppShell
			variant="workbench"
			showStagePipeline={true}
			onToggleAssets={() => setAssetsOpen((v) => !v)}
			onToggleHistory={() => setHistoryOpen((v) => !v)}
			assetsOpen={assetsOpen}
			historyOpen={historyOpen}
			projectId={project.id}
			currentStage={storeCurrentStage}
			isGenerating={storeIsGenerating}
			awaitingConfirm={storeAwaitingConfirm}
			hasRecovery={hasRecovery}
			onResume={handleResume}
			onCancelPipeline={handleCancel}
			onAssetsClose={() => setAssetsOpen(false)}
			onHistoryClose={() => setHistoryOpen(false)}
			onHistoryNavigate={(id) => navigate(`/project/${id}`)}
			chatIsGenerating={hasActiveRun}
			onChatSendFeedback={handleFeedback}
			onChatConfirm={handleConfirm}
			onChatEntityConfirm={handleEntityConfirm}
			onChatGenerate={handleGenerate}
			onChatCancel={handleCancel}
			chatGenerateDisabled={false}
			versionCompareOpen={versionOpen}
			versionCompareProjectId={project.id}
			versionCompareEntityType={versionTarget?.entityType}
			versionCompareEntityId={versionTarget?.entityId ?? null}
			onVersionCompareClose={() => setVersionOpen(false)}
		>
			<div className="flex-1 relative overflow-hidden">
				<div className="absolute top-3 right-4 z-20">
					<ViewSwitcher
						currentView={viewMode === "timeline" ? "detail" : viewMode}
						onViewChange={(v) => setViewMode(v === "detail" ? "timeline" : v)}
					/>
				</div>
				{viewMode === "canvas" && <StageView projectId={projectId} />}
				{viewMode === "timeline" && (
					<TimelineView
						projectId={projectId}
						shapes={timelineShapes}
						onShapeSelect={(id) => setSelectedShapeId(id)}
						onTimeChange={(_time) => {}}
					/>
				)}
				{viewMode === "list" && <ListView projectId={projectId} />}
			</div>
		</AppShell>
	);
}

function ListView({ projectId: _projectId }: { projectId: number }) {
	return (
		<div className="flex h-full w-full items-center justify-center bg-base-100 flex-col gap-4">
			<p className="text-base-content/40 text-sm">列表视图</p>
			<p className="text-base-content/30 text-xs">功能开发中...</p>
		</div>
	);
}
