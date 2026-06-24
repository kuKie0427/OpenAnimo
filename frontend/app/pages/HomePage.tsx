import { useState, useCallback, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { projectsApi } from "~/services/api";
import { Button } from "~/components/ui/Button";
import { Card } from "~/components/ui/Card";
import {
	ChevronDownIcon,
	ChevronUpIcon,
	GlobeAltIcon,
	PaperAirplaneIcon,
} from "@heroicons/react/24/outline";
import { AppShell } from "~/components/layout/AppShell";
import { SvgIcon } from "~/components/ui/SvgIcon";

const STYLE_CATEGORIES = [
	{
		group: "2D 动画",
		styles: [
			{ value: "anime", label: "日漫" },
			{ value: "shonen", label: "少年热血" },
			{ value: "slice-of-life", label: "日常治愈" },
			{ value: "manga", label: "黑白漫画" },
			{ value: "donghua", label: "国风动画" },
		],
	},
	{
		group: "3D 风格",
		styles: [
			{ value: "cinematic", label: "电影质感" },
			{ value: "pixar", label: "3D 卡通" },
			{ value: "lowpoly", label: "低多边形" },
		],
	},
	{
		group: "艺术风格",
		styles: [
			{ value: "watercolor", label: "水彩" },
			{ value: "sketch", label: "素描" },
			{ value: "realistic", label: "写实" },
		],
	},
];

const DEFAULT_STYLE = "anime";

export function HomePage() {
	const navigate = useNavigate();
	const queryClient = useQueryClient();
	const [story, setStory] = useState("");
	const [style, setStyle] = useState(DEFAULT_STYLE);
	const [shotCount, setShotCount] = useState<number | undefined>(undefined);
	const [characterHints, setCharacterHints] = useState<string[]>([""]);
	const [showAdvanced, setShowAdvanced] = useState(false);
	const [isComposing, setIsComposing] = useState(false);
	const [referenceImages, setReferenceImages] = useState<string[]>([]);
	const [pendingFiles, setPendingFiles] = useState<File[]>([]);
	const [assetsOpen, setAssetsOpen] = useState(false);
	const [historyOpen, setHistoryOpen] = useState(false);
	const fileInputRef = useRef<HTMLInputElement>(null);

	const createMutation = useMutation({
		mutationFn: projectsApi.create,
		onSuccess: async (project) => {
			queryClient.invalidateQueries({ queryKey: ["projects"] });
			if (pendingFiles.length > 0 && project.id) {
				for (const file of pendingFiles) {
					try {
						await projectsApi.uploadReference(project.id, file);
					} catch (e) {
						if (import.meta.env.DEV) console.error("[ref upload]", e);
					}
				}
				setPendingFiles([]);
			}
			navigate(`/project/${project.id}?autoStart=true`);
		},
	});

	const handleSubmit = () => {
		const trimmed = story.trim();
		if (!trimmed || createMutation.isPending) return;

		const MAX_STORY_LENGTH = 5000;
		if (trimmed.length > MAX_STORY_LENGTH) {
			alert(
				`故事太长了！请控制在 ${MAX_STORY_LENGTH} 字以内（当前 ${trimmed.length} 字）`,
			);
			return;
		}

		const firstLine = trimmed.split("\n")[0] || "";
		const MAX_TITLE_LENGTH = 50;
		const title =
			firstLine.length > MAX_TITLE_LENGTH
				? `${firstLine.slice(0, MAX_TITLE_LENGTH)}...`
				: firstLine;

		const hints = characterHints.filter((h) => h.trim());

		createMutation.mutate({
			title: title || "未命名项目",
			story: trimmed,
			style,
			target_shot_count: shotCount,
			character_hints: hints.length > 0 ? hints : undefined,
			text_provider_override: null,
			image_provider_override: null,
			video_provider_override: null,
		});
	};

	const handleKeyDown = (e: React.KeyboardEvent) => {
		if (e.key === "Enter" && !e.shiftKey && !isComposing) {
			e.preventDefault();
			handleSubmit();
		}
	};

	const addCharacterHint = () => {
		setCharacterHints([...characterHints, ""]);
	};

	const updateCharacterHint = (index: number, value: string) => {
		const updated = [...characterHints];
		updated[index] = value;
		setCharacterHints(updated);
	};

	const removeCharacterHint = (index: number) => {
		setCharacterHints(characterHints.filter((_, i) => i !== index));
	};

	const handleImageUpload = useCallback(
		(files: FileList | null) => {
			if (!files) return;
			const newFiles = Array.from(files);
			const total = pendingFiles.length + newFiles.length;
			if (total > 7) {
				newFiles.splice(7 - pendingFiles.length);
			}
			setPendingFiles((prev) => [...prev, ...newFiles]);
			newFiles.forEach((file) => {
				const reader = new FileReader();
				reader.onload = (e) => {
					const dataUrl = e.target?.result as string;
					setReferenceImages((prev) => [...prev, dataUrl]);
				};
				reader.readAsDataURL(file);
			});
		},
		[pendingFiles.length],
	);

	const handleDrop = useCallback(
		(e: React.DragEvent) => {
			e.preventDefault();
			handleImageUpload(e.dataTransfer.files);
		},
		[handleImageUpload],
	);

	const handlePaste = useCallback(
		(e: React.ClipboardEvent) => {
			const items = e.clipboardData.items;
			const imageItems = Array.from(items).filter((item) =>
				item.type.startsWith("image/"),
			);
			if (imageItems.length === 0) return;
			e.preventDefault();
			imageItems.forEach((item) => {
				const file = item.getAsFile();
				if (file) {
					const dt = new DataTransfer();
					dt.items.add(file);
					handleImageUpload(dt.files);
				}
			});
		},
		[handleImageUpload],
	);

	const removeReferenceImage = (index: number) => {
		setReferenceImages(referenceImages.filter((_, i) => i !== index));
		setPendingFiles(pendingFiles.filter((_, i) => i !== index));
	};

	return (
		<AppShell
			variant="default"
			onToggleAssets={() => setAssetsOpen((v) => !v)}
			onToggleHistory={() => setHistoryOpen((v) => !v)}
			assetsOpen={assetsOpen}
			historyOpen={historyOpen}
			onAssetsClose={() => setAssetsOpen(false)}
			onHistoryClose={() => setHistoryOpen(false)}
			onHistoryNavigate={(id) => navigate(`/project/${id}`)}
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
			<div
				className="flex flex-col items-center justify-center p-4 sm:p-6 grain-hero min-h-[calc(100vh-40px)]"
				onDrop={handleDrop}
				onDragOver={(e) => e.preventDefault()}
			>
				<main className="w-full max-w-2xl mx-auto">
					<div className="text-center mb-8 animate-fade-in">
						<h1 className="text-6xl sm:text-8xl font-heading tracking-wider text-base-content leading-none">
							OpenAnimo
						</h1>
						<p className="font-heading text-sm text-base-content/50 mt-2 tracking-wide">
							用 AI 将故事转化为漫剧视频
						</p>
						<Link
							to="/universes"
							className="inline-flex items-center gap-1 mt-2 text-xs text-base-content/50 hover:text-primary transition-colors font-heading font-bold"
						>
							<GlobeAltIcon className="w-3.5 h-3.5" aria-hidden="true" />
							IP 宇宙
						</Link>
					</div>

					<Card className="w-full">
						<div className="space-y-4">
							{/* Story Input + Reference Images */}
							<div className="relative" onPaste={handlePaste}>
								<label htmlFor="story-input" className="sr-only">
									输入你的故事创意
								</label>
								<textarea
									id="story-input"
									className="input-field w-full min-h-28 text-sm resize-none p-3 pr-12 bg-base-100/80"
									placeholder="写下你的故事创意…"
									value={story}
									onChange={(e) => setStory(e.target.value)}
									onKeyDown={handleKeyDown}
									onCompositionStart={() => setIsComposing(true)}
									onCompositionEnd={() => setIsComposing(false)}
									disabled={createMutation.isPending}
									aria-label="输入你的故事创意"
									maxLength={5000}
									rows={4}
								/>
								{story.length > 4500 && (
									<div className="absolute top-2 right-2 text-xs text-warning font-bold">
										{5000 - story.length}
									</div>
								)}
								<Button
									variant="primary"
									size="sm"
									className="absolute right-2 bottom-2 rounded-full !p-2 min-w-[40px] min-h-[40px] transition-all duration-150 hover:scale-105 active:scale-95"
									onClick={handleSubmit}
									disabled={!story.trim() || createMutation.isPending}
									loading={createMutation.isPending}
									aria-label="开始生成故事"
									aria-disabled={!story.trim() || createMutation.isPending}
								>
									{!createMutation.isPending && (
										<PaperAirplaneIcon className="w-4 h-4" aria-hidden="true" />
									)}
								</Button>
							</div>

							{/* Reference Images */}
							{referenceImages.length > 0 && (
								<div className="flex gap-1.5 flex-wrap">
									{referenceImages.map((img, i) => (
										<div
											key={i}
											className="relative group w-12 h-12 rounded-lg overflow-hidden border border-base-content/10"
										>
											<img
												src={img}
												alt={`参考图 ${i + 1}`}
												className="w-full h-full object-cover"
											/>
											<button
												type="button"
												className="absolute inset-0 bg-error/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
												onClick={() => removeReferenceImage(i)}
												aria-label={`删除参考图 ${i + 1}`}
											>
												<SvgIcon name="x" size={12} className="text-base-100" />
											</button>
										</div>
									))}
									{referenceImages.length < 7 && (
										<button
											type="button"
											className="w-12 h-12 rounded-lg border border-dashed border-base-content/15 flex items-center justify-center text-base-content/25 hover:border-primary/40 hover:text-primary/50 transition-colors"
											onClick={() => fileInputRef.current?.click()}
											aria-label="添加参考图"
										>
											<SvgIcon name="plus" size={14} />
										</button>
									)}
								</div>
							)}
							{referenceImages.length === 0 && (
								<div
									className="flex items-center gap-1.5 text-xs text-base-content/30 hover:text-primary/50 cursor-pointer transition-colors"
									onClick={() => fileInputRef.current?.click()}
									role="button"
									tabIndex={0}
									onKeyDown={(e) =>
										e.key === "Enter" && fileInputRef.current?.click()
									}
								>
									<SvgIcon name="image" size={14} />
									<span>添加参考图（可选，最多7张）</span>
								</div>
							)}
							<input
								ref={fileInputRef}
								type="file"
								accept="image/*"
								multiple
								className="hidden"
								onChange={(e) => {
									handleImageUpload(e.target.files);
									e.target.value = "";
								}}
							/>

							{/* Style Selector */}
							<div className="space-y-1.5">
								{STYLE_CATEGORIES.map((category, ci) => (
									<div
										key={category.group}
										className="flex items-center gap-1.5 flex-wrap"
									>
										<span className="text-[10px] text-base-content/30 font-bold tracking-wider w-14 flex-shrink-0">
											{category.group}
										</span>
										<div className="flex gap-1 flex-wrap items-center">
											{category.styles.map((opt) => (
												<button
													key={opt.value}
													type="button"
													className={`px-2 py-0.5 rounded-full border text-[11px] font-bold transition-all duration-150 ${
														style === opt.value
															? "border-primary bg-primary/10 text-primary shadow-gate-glow"
															: "border-base-content/10 bg-base-200/50 text-base-content/50 hover:border-primary/30 hover:-translate-y-0.5"
													}`}
													onClick={() => setStyle(opt.value)}
												>
													{opt.label}
												</button>
											))}
										</div>
										{ci < STYLE_CATEGORIES.length - 1 && (
											<div className="hidden sm:block flex-1 border-b border-base-content/5" />
										)}
									</div>
								))}
								<div className="flex items-center justify-end">
									<button
										type="button"
										className="flex items-center gap-0.5 text-xs text-base-content/30 hover:text-primary transition-colors px-1.5"
										onClick={() => setShowAdvanced(!showAdvanced)}
										aria-expanded={showAdvanced}
									>
										{showAdvanced ? (
											<ChevronUpIcon className="w-3 h-3" />
										) : (
											<ChevronDownIcon className="w-3 h-3" />
										)}
										更多
									</button>
								</div>
							</div>

							{showAdvanced && (
								<div className="space-y-2 border-t border-base-content/10 pt-2">
									<div>
										<label
											htmlFor="shot-count"
className="text-xs text-base-content/40 mb-0.5 block font-heading tracking-wide"
										>
											镜头数 {shotCount ?? "自动"}
										</label>
										<input
											id="shot-count"
											type="range"
											min={1}
											max={20}
											value={shotCount ?? 6}
											onChange={(e) => setShotCount(Number(e.target.value))}
											className="range range-xs range-primary"
										/>
									</div>

									<div>
										<label className="text-xs text-base-content/40 mb-0.5 block font-heading tracking-wide">
											角色提示
										</label>
										{characterHints.map((hint, i) => (
											<div key={i} className="flex gap-1 mb-1">
												<input
													type="text"
													className="input input-bordered input-sm bg-base-200/60 flex-1 text-xs border"
													placeholder={`角色 ${i + 1}`}
													value={hint}
													onChange={(e) =>
														updateCharacterHint(i, e.target.value)
													}
												/>
												{characterHints.length > 1 && (
													<button
														type="button"
														className="btn btn-ghost btn-xs"
														onClick={() => removeCharacterHint(i)}
														aria-label={`删除角色 ${i + 1}`}
													>
														×
													</button>
												)}
											</div>
										))}
										{characterHints.length < 6 && (
											<button
												type="button"
												className="btn btn-ghost btn-xs text-primary"
												onClick={addCharacterHint}
											>
												+ 添加
											</button>
										)}
									</div>
								</div>
							)}
						</div>
					</Card>
				</main>
			</div>
		</AppShell>
	);
}
