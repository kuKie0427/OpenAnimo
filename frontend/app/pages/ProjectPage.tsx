import { ArrowPathIcon, StopIcon } from "@heroicons/react/24/outline";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
	Link,
	useNavigate,
	useParams,
	useSearchParams,
} from "react-router-dom";
import { ViewSwitcher } from "~/components/daw/ViewSwitcher";
import { StageTabs } from "~/components/daw/StageTabs";
import { ScriptEditor } from "~/components/script/ScriptEditor";
import { ShotlistPanel } from "~/components/script/ShotlistPanel";
import type { ShotSyncItem } from "~/components/script/ShotlistPanel";
import { TimelineView } from "~/components/timeline";
import { ListView } from "~/components/list";
import { AppShell } from "~/components/layout/AppShell";
import { StageView } from "~/components/layout/StageView";
import { Button } from "~/components/ui/Button";
import { Card } from "~/components/ui/Card";
import { useViewStore } from "~/stores/viewStore";
import { useProjectWebSocket } from "~/hooks/useWebSocket";
import { canvasEvents } from "~/components/canvas/canvasEvents";
import { projectsApi } from "~/services/api";
import { useEditorStore, useShallow } from "~/stores/editorStore";
import type { ProjectProviderSettings, RecoveryControlRead, VersionEntityType, WorkflowStage } from "~/types";
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
	const [scriptOpen, setScriptOpen] = useState(false);
	const [selectedParagraphIndex, setSelectedParagraphIndex] = useState<number | null>(null);
	const [selectedShotId, setSelectedShotId] = useState<number | null>(null);
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

	const { data: scriptData, isLoading: scriptLoading, error: scriptError } = useQuery({
		queryKey: ["script", projectId],
		queryFn: () => projectsApi.getScript(projectId),
		enabled: !!project && scriptOpen,
	});

	const [localScript, setLocalScript] = useState<string | null>(null);
	const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

	const updateScriptMutation = useMutation({
		mutationFn: (scriptMarkdown: string) =>
			projectsApi.updateScript(projectId, { script_markdown: scriptMarkdown }),
		onError: (error: Error) => {
			toast.error({
				title: "保存剧本失败",
				message: error.message || "请重试",
			});
		},
	});

	const scriptValue = localScript ?? scriptData?.script_markdown ?? "";

	const handleScriptChange = useCallback((value: string) => {
		setLocalScript(value);
		if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
		saveTimerRef.current = setTimeout(() => {
			updateScriptMutation.mutate(value);
		}, 500);
	}, []);

	useEffect(() => {
		return () => {
			if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
		};
	}, []);

	useEffect(() => {
		if (scriptData?.script_markdown !== undefined && localScript === null) {
			setLocalScript(scriptData.script_markdown);
		}
	}, [scriptData]);

	const {
		data: syncMapData,
		refetch: refetchSyncMap,
	} = useQuery({
		queryKey: ["script-sync", projectId],
		queryFn: () => projectsApi.getScriptSyncMap(projectId),
		enabled: !!project && scriptOpen,
	});

	const syncMap = syncMapData?.sync_map ?? [];

	const syncParagraphMutation = useMutation({
		mutationFn: (data: {
			paragraph_index: number;
			paragraph_text: string;
		}) => projectsApi.syncParagraph(projectId, data),
		onSuccess: () => {
			setTimeout(() => {
				refetchSyncMap();
				queryClient.invalidateQueries({ queryKey: ["script", projectId] });
			}, 2000);
		},
	});

	const currentParagraphShots: ShotSyncItem[] = useMemo(() => {
		if (selectedParagraphIndex === null || syncMap.length === 0) {
			return [];
		}
		return syncMap
			.filter((e) => e.paragraph_index === selectedParagraphIndex)
			.sort((a, b) => a.shot_order - b.shot_order)
			.map((e) => ({
				shot_id: e.shot_id,
				paragraph_index: e.paragraph_index,
				shot_order: e.shot_order,
				shot_description: e.shot_description,
				shot_image_url: e.shot_image_url,
				is_synced: e.is_synced,
			}));
	}, [selectedParagraphIndex, syncMap]);

	const currentParagraphText = useMemo(() => {
		if (selectedParagraphIndex === null || !scriptValue) return "";
		const paragraphs = scriptValue.split(/\n\s*\n/);
		return paragraphs[selectedParagraphIndex] ?? "";
	}, [selectedParagraphIndex, scriptValue]);

	const handleCursorActivity = useCallback(
		(lineNumber: number) => {
			const matching = syncMap.find((e) => e.line_number === lineNumber);
			if (matching) {
				setSelectedParagraphIndex(matching.paragraph_index);
				const shots = syncMap.filter(
					(e) => e.paragraph_index === matching.paragraph_index,
				);
				setSelectedShotId(shots.length > 0 ? shots[0].shot_id : null);
			}
		},
		[syncMap],
	);

	const handleShotSelect = useCallback(
		(shotId: number) => {
			setSelectedShotId(shotId);
			const entry = syncMap.find((e) => e.shot_id === shotId);
			if (entry) {
				setSelectedParagraphIndex(entry.paragraph_index);
			}
		},
		[syncMap],
	);

	const handleSyncParagraph = useCallback(() => {
		if (selectedParagraphIndex === null) return;
		syncParagraphMutation.mutate({
			paragraph_index: selectedParagraphIndex,
			paragraph_text: currentParagraphText,
		});
	}, [selectedParagraphIndex, currentParagraphText, syncParagraphMutation]);

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

	const shotSyncCompleted = useEditorStore((state) => state.shotSyncCompleted);
	useEffect(() => {
		if (shotSyncCompleted) {
			queryClient.invalidateQueries({ queryKey: ["script-sync", projectId] });
			queryClient.invalidateQueries({ queryKey: ["script", projectId] });
		}
	}, [shotSyncCompleted, projectId, queryClient]);

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

	const workflowStages = useMemo(() => {
		const stageDefs: Array<{
			key: WorkflowStage;
			label: string;
			icon: React.ComponentType<{ className?: string }>;
			status: "completed" | "active" | "pending" | "error";
		}> = [
			{ key: "plan", label: "规划", icon: ArrowPathIcon, status: "pending" },
			{ key: "render", label: "生成", icon: ArrowPathIcon, status: "pending" },
			{ key: "compose", label: "合成", icon: ArrowPathIcon, status: "pending" },
			{ key: "review", label: "审阅", icon: ArrowPathIcon, status: "pending" },
		];

		const stageOrder: WorkflowStage[] = ["plan", "render", "compose", "review"];
		const currentIdx = stageOrder.indexOf(storeCurrentStage);

		return stageDefs.map((s, i) => ({
			...s,
			status: i < currentIdx ? "completed" as const
				: i === currentIdx ? "active" as const
				: "pending" as const,
		}));
	}, [storeCurrentStage]);

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
			<div className="flex-1 flex flex-col overflow-hidden">
				<div className="flex items-center justify-between">
					<StageTabs
						currentStage={storeCurrentStage}
						stages={workflowStages}
						onStageChange={(stage) => {
							const stageDef = workflowStages.find((s) => s.key === stage);
							if (stageDef?.status === "pending") {
								toast.info({ title: "提示", message: "请从右侧对话面板发起生成" });
								return;
							}
							useEditorStore.getState().setCurrentStage(stage);
						}}
					/>
					<div className="flex items-center gap-2 pr-4">
						<button
							type="button"
							onClick={() => setScriptOpen((v) => !v)}
							className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-all duration-200 ${
								scriptOpen
									? "bg-primary text-primary-content shadow-aperture"
									: "text-base-content/60 hover:text-base-content hover:bg-base-200"
							}`}
							data-testid="script-toggle"
						>
							<span>📝</span>
							<span className="hidden sm:inline">剧本</span>
						</button>
						<ViewSwitcher currentView={viewMode} onViewChange={setViewMode} />
					</div>
				</div>

				<div className="flex-1 relative overflow-hidden">
					{scriptOpen ? (
						<div data-testid="script-editor" className="w-full h-full flex overflow-hidden">
							<div className="flex-1 p-4 overflow-auto">
								{scriptLoading ? (
									<div className="flex items-center justify-center h-full">
										<ArrowPathIcon className="w-6 h-6 animate-pulse text-base-content/60" />
									</div>
								) : scriptError ? (
									<div className="flex flex-col items-center justify-center h-full gap-4">
										<p className="text-base-content/60">加载剧本失败</p>
										<button
											type="button"
											onClick={() => queryClient.invalidateQueries({ queryKey: ["script", projectId] })}
											className="btn btn-sm btn-primary"
										>
											重试
										</button>
									</div>
								) : (
									<ScriptEditor
										value={scriptValue}
										onChange={handleScriptChange}
										selectedLine={
											selectedParagraphIndex !== null
												? syncMap.find((e) => e.paragraph_index === selectedParagraphIndex)
														?.line_number ?? null
												: null
										}
										onCursorActivity={handleCursorActivity}
									/>
								)}
							</div>
							<ShotlistPanel
								shots={currentParagraphShots}
								selectedShotId={selectedShotId}
								onSelectShot={handleShotSelect}
								onSyncParagraph={handleSyncParagraph}
								isSyncing={syncParagraphMutation.isPending}
							/>
						</div>
					) : (
						<>
							{viewMode === "canvas" && (
								<div data-testid="infinite-canvas" className="w-full h-full">
									<StageView projectId={projectId} />
								</div>
							)}
							{viewMode === "timeline" && (
								<div data-testid="timeline-view" className="w-full h-full">
									<TimelineView
										projectId={projectId}
										shapes={timelineShapes}
										onShapeSelect={(id) => setSelectedShapeId(id)}
										onTimeChange={(_time) => {}}
									/>
								</div>
							)}
							{viewMode === "list" && (
								<div data-testid="list-view" className="w-full h-full">
									<ListView
										projectId={projectId}
										shapes={timelineShapes}
										onShapeSelect={(id) => setSelectedShapeId(id)}
										onShapeEdit={(id) => setSelectedShapeId(id)}
										onShapeDelete={() => {}}
									/>
								</div>
							)}
						</>
					)}
				</div>
			</div>
		</AppShell>
	);
}
