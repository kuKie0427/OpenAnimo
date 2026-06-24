import { Fragment, useState } from "react";
import {
	HTMLContainer,
	Rectangle2d,
	ShapeUtil,
	T,
	type Geometry2d,
	type RecordProps,
} from "tldraw";
import { SvgIcon } from "~/components/ui/SvgIcon";
import { getStaticUrl } from "~/services/api";
import { getShapeSize, useDomSize } from "~/hooks/useDomSize";
import { getWorkspaceSectionPlaceholderText } from "~/utils/workspaceStatus";
import { canvasEvents } from "../canvasEvents";
import type { ShapeActionName, ShapeActionPayload } from "../canvasEvents";
import { Button } from "~/components/ui/Button";
import { SectionShell } from "./SectionShell";
import type {
	ReviewedCharacter,
	ReviewedShot,
	StoryboardBoardShape,
	StoryboardBoardSectionKey,
} from "./types";

const SECTION_TITLES: Record<StoryboardBoardSectionKey, string> = {
	plan: "编剧规划",
	render: "视觉渲染",
	compose: "最终输出",
};

const SECTION_FLOW_COPY: Partial<Record<StoryboardBoardSectionKey, string>> = {
	render: "角色与分镜接力",
	compose: "镜头汇成成片",
};

const VIDEO_PLACEHOLDER_ICON = (
	<svg
		xmlns="http://www.w3.org/2000/svg"
		viewBox="0 0 24 24"
		fill="currentColor"
		className="w-8 h-8 opacity-40"
	>
		<path d="M4.5 4.5a3 3 0 0 0-3 3v9a3 3 0 0 0 3 3h8.25a3 3 0 0 0 3-3v-9a3 3 0 0 0-3-3H4.5ZM19.94 18.75l-2.69-2.69V7.94l2.69-2.69c.944-.945 2.56-.276 2.56 1.06v11.38c0 1.336-1.616 2.005-2.56 1.06Z" />
	</svg>
);

function stopCanvasDrag(e: React.PointerEvent<HTMLElement>) {
	e.stopPropagation();
}

function emitEntityAction({
	action,
	entityType,
	entityId,
	feedbackType,
	shotPatch,
	feedbackContent,
}: {
	action: ShapeActionName;
	entityType: "character" | "shot";
	entityId: number;
	feedbackType: "render";
	shotPatch?: ShapeActionPayload["shotPatch"];
	feedbackContent?: string;
}) {
	canvasEvents.emit("shape-action", {
		shapeId: "shape:storyboard-board",
		action,
		entityType,
		entityId,
		feedbackType,
		shotPatch,
		feedbackContent,
	});
}

function CharacterCard({ character }: { character: ReviewedCharacter }) {
	const isApproved = character.approval_state === "approved";
	const currentImage = getStaticUrl(character.image_url);
	const approvedImage = getStaticUrl(character.approved_image_url);
	const displayImage =
		isApproved && approvedImage ? approvedImage : currentImage;
	const [isEditing, setIsEditing] = useState(false);
	const [feedbackText, setFeedbackText] = useState(character.description || "");

	const handleAction = (action: ShapeActionName) => {
		if (action === "edit") {
			setIsEditing(true);
			return;
		}
		emitEntityAction({
			action,
			entityType: "character",
			entityId: character.id,
			feedbackType: "render",
		});
	};

	const handleSaveEdit = () => {
		setIsEditing(false);
		const content = feedbackText.trim();
		if (content) {
			emitEntityAction({
				action: "edit",
				entityType: "character",
				entityId: character.id,
				feedbackType: "render",
				feedbackContent: content,
			});
		}
	};

	return (
		<article className="group overflow-hidden card-screen">
			<div className="relative aspect-[4/3] bg-base-300">
				{displayImage ? (
					<img
						src={displayImage}
						alt={character.name}
						className="h-full w-full object-cover"
					/>
				) : (
					<div className="flex h-full items-center justify-center text-xs text-base-content/40">
						等待角色图
					</div>
				)}
				<div className="absolute inset-0 flex items-center justify-center gap-1.5 bg-base-content/0 opacity-0 transition group-hover:bg-base-content/25 group-hover:opacity-100">
					<button
						type="button"
						className="btn btn-sm btn-circle btn-ghost text-base-100 hover:bg-base-100/30 touch-target"
						title="重新生成"
						onPointerDown={stopCanvasDrag}
						onClick={() => handleAction("regenerate")}
					>
						<SvgIcon name="refresh-cw" size={14} />
					</button>
					<button
						type="button"
						className="btn btn-sm btn-circle btn-ghost text-base-100 hover:bg-base-100/30 touch-target"
						title="编辑"
						onPointerDown={stopCanvasDrag}
						onClick={() => handleAction("edit")}
					>
						<SvgIcon name="pencil" size={14} />
					</button>
					{!isApproved && (
						<button
							type="button"
							className="btn btn-sm btn-circle btn-ghost text-success hover:bg-success/30 touch-target"
							title="批准"
							onPointerDown={stopCanvasDrag}
							onClick={() => handleAction("approve")}
						>
							<SvgIcon name="check" size={14} />
						</button>
					)}
					<button
						type="button"
						className="btn btn-sm btn-circle btn-ghost text-info hover:bg-info/30 touch-target"
						title="版本历史"
						onPointerDown={stopCanvasDrag}
						onClick={() => handleAction("history")}
					>
						<SvgIcon name="clock-3" size={14} />
					</button>
					<button
						type="button"
						className="btn btn-sm btn-circle btn-ghost text-primary hover:bg-primary/30 touch-target"
						title="添加到资产库"
						onPointerDown={stopCanvasDrag}
						onClick={() => handleAction("add-to-assets")}
					>
						<SvgIcon name="star" size={14} />
					</button>
				</div>
				{isApproved && (
					<span className="absolute right-2 top-2 badge badge-xs badge-success gap-1">
						<SvgIcon name="check" size={10} />
						已批准
					</span>
				)}
			</div>
			<div className="space-y-1.5 p-3">
				<div className="flex items-center gap-2">
					<span
						className={`h-2 w-2 rounded-full ${isApproved ? "bg-success" : "bg-warning"}`}
					/>
					<h3 className="m-0 text-sm font-heading font-bold">
						{character.name}
					</h3>
					<span className="badge badge-ghost badge-xs ml-auto">
						v{character.approval_version}
					</span>
				</div>
				{isEditing ? (
					<div className="space-y-1.5 pt-1">
						<textarea
							className="input-field w-full text-xs p-2 resize-none"
							rows={2}
							placeholder="修改意见"
							value={feedbackText}
							onPointerDown={stopCanvasDrag}
							onChange={(e) => setFeedbackText(e.currentTarget.value)}
							onKeyDown={(e) => {
								if (e.key === "Enter" && !e.shiftKey) {
									e.preventDefault();
									handleSaveEdit();
								}
							}}
						/>
						<div className="flex gap-1">
						<Button
							variant="primary"
							size="sm"
							onPointerDown={stopCanvasDrag}
							onClick={handleSaveEdit}
						>
							提交
						</Button>
							<button
								type="button"
								className="btn btn-xs btn-ghost"
								onPointerDown={stopCanvasDrag}
								onClick={() => setIsEditing(false)}
							>
								取消
							</button>
						</div>
					</div>
				) : (
					character.description && (
						<p className="m-0 text-xs leading-relaxed text-base-content/60">
							{character.description}
						</p>
					)
				)}
			</div>
		</article>
	);
}

function ShotCard({ shot }: { shot: ReviewedShot }) {
	const isApproved = shot.approval_state === "approved";
	const imageUrl = getStaticUrl(shot.image_url);
	const videoUrl = getStaticUrl(shot.video_url);
	const [isEditing, setIsEditing] = useState(false);
	const [editDialogue, setEditDialogue] = useState(shot.dialogue || "");
	const [editAction, setEditAction] = useState(shot.action || "");

	const handleAction = (action: ShapeActionName) => {
		if (action === "edit") {
			setIsEditing(true);
			return;
		}
		emitEntityAction({
			action,
			entityType: "shot",
			entityId: shot.id,
			feedbackType: "render",
		});
	};

	const handleSaveEdit = () => {
		setIsEditing(false);
		if (
			editDialogue !== (shot.dialogue || "") ||
			editAction !== (shot.action || "")
		) {
			emitEntityAction({
				action: "edit",
				entityType: "shot",
				entityId: shot.id,
				feedbackType: "render",
				shotPatch: {
					action: editAction || null,
					dialogue: editDialogue || null,
				},
			});
		}
	};

	return (
		<article
			className={`group overflow-hidden card-feature ${isApproved ? "ring-2 ring-success/50" : ""}`}
		>
			<div className="relative aspect-video bg-base-300">
				{imageUrl ? (
					<img
						src={imageUrl}
						alt={`Shot ${shot.order}`}
						className="h-full w-full object-cover"
					/>
				) : (
					<div className="flex h-full items-center justify-center text-xs text-base-content/40">
						等待分镜图
					</div>
				)}
				<span className="badge badge-xs absolute right-2 top-2 bg-base-100/80">
					{shot.duration ? `${shot.duration}s` : "未定时长"}
				</span>
				{shot.expression && (
					<span className="badge badge-xs badge-primary absolute bottom-2 left-2">
						{shot.expression}
					</span>
				)}
				{isApproved && (
					<span className="absolute left-2 top-2 badge badge-xs badge-success gap-1">
						<SvgIcon name="check" size={10} />
						已批准
					</span>
				)}
				<div className="absolute inset-0 flex items-center justify-center gap-1 bg-base-content/0 opacity-0 transition group-hover:bg-base-content/25 group-hover:opacity-100">
					<button
						type="button"
						className="btn btn-sm btn-circle btn-ghost text-base-100 hover:bg-base-100/30 touch-target"
						title="重新生成"
						onPointerDown={stopCanvasDrag}
						onClick={() => handleAction("regenerate")}
					>
						<SvgIcon name="refresh-cw" size={14} />
					</button>
					<button
						type="button"
						className="btn btn-sm btn-circle btn-ghost text-base-100 hover:bg-base-100/30 touch-target"
						title="编辑"
						onPointerDown={stopCanvasDrag}
						onClick={() => handleAction("edit")}
					>
						<SvgIcon name="pencil" size={14} />
					</button>
					{videoUrl && (
						<button
							type="button"
							className="btn btn-sm btn-circle btn-ghost text-base-100 hover:bg-base-100/30 touch-target"
							title="预览片段"
							onPointerDown={stopCanvasDrag}
							onClick={() =>
								canvasEvents.emit("preview-video", {
									src: videoUrl,
									title: `镜头 ${shot.order}`,
								})
							}
						>
							<SvgIcon name="play" size={14} />
						</button>
					)}
					{!isApproved && (
						<button
							type="button"
							className="btn btn-sm btn-circle btn-ghost text-success hover:bg-success/30 touch-target"
							title="批准"
							onPointerDown={stopCanvasDrag}
							onClick={() => handleAction("approve")}
						>
							<SvgIcon name="check" size={14} />
						</button>
					)}
					<button
						type="button"
						className="btn btn-sm btn-circle btn-ghost text-info hover:bg-info/30 touch-target"
						title="版本历史"
						onPointerDown={stopCanvasDrag}
						onClick={() => handleAction("history")}
					>
						<SvgIcon name="clock-3" size={14} />
					</button>
					<button
						type="button"
						className="btn btn-sm btn-circle btn-ghost text-primary hover:bg-primary/30 touch-target"
						title="保存到资产库"
						onPointerDown={stopCanvasDrag}
						onClick={() => handleAction("add-to-assets")}
					>
						<SvgIcon name="star" size={14} />
					</button>
				</div>
			</div>
			<div className="space-y-1.5 p-3">
				<div className="flex items-center gap-2">
					<span
						className={`h-2 w-2 shrink-0 rounded-full ${isApproved ? "bg-success" : "bg-warning"}`}
					/>
					<h3 className="m-0 text-sm font-heading font-bold">
						镜头 {shot.order}
					</h3>
					{shot.camera && (
						<span className="badge badge-ghost badge-xs ml-auto">
							{shot.camera}
						</span>
					)}
				</div>
				{shot.scene && (
					<p className="m-0 text-xs font-semibold text-base-content/75">
						{shot.scene}
					</p>
				)}
				{shot.description && (
					<p className="m-0 text-xs leading-relaxed text-base-content/60">
						{shot.description}
					</p>
				)}
				{isEditing ? (
					<div className="space-y-1.5 pt-1">
						<input
							type="text"
							className="input-field w-full text-xs p-2"
							placeholder="动作"
							value={editAction}
							onPointerDown={stopCanvasDrag}
							onChange={(e) => setEditAction(e.currentTarget.value)}
						/>
						<input
							type="text"
							className="input-field w-full text-xs p-2"
							placeholder="对话"
							value={editDialogue}
							onPointerDown={stopCanvasDrag}
							onChange={(e) => setEditDialogue(e.currentTarget.value)}
							onKeyDown={(e) => e.key === "Enter" && handleSaveEdit()}
						/>
						<div className="flex gap-1">
						<Button
							variant="primary"
							size="sm"
							onPointerDown={stopCanvasDrag}
							onClick={handleSaveEdit}
						>
							保存
						</Button>
							<button
								type="button"
								className="btn btn-xs btn-ghost"
								onPointerDown={stopCanvasDrag}
								onClick={() => setIsEditing(false)}
							>
								取消
							</button>
						</div>
					</div>
				) : (
					<>
						{shot.action && (
							<p className="m-0 flex items-center gap-1 text-xs text-accent/75">
								<SvgIcon name="chevron-right" size={10} />
								{shot.action}
							</p>
						)}
						{shot.dialogue && (
							<p className="m-0 text-xs italic text-primary/80">
								"{shot.dialogue}"
							</p>
						)}
					</>
				)}
				<div className="flex flex-wrap gap-1 pt-0.5">
					{shot.lighting && (
						<span className="badge badge-ghost badge-xs inline-flex items-center gap-1 opacity-70">
							<SvgIcon name="lightbulb" size={10} />
							{shot.lighting}
						</span>
					)}
					{shot.sfx && (
						<span className="badge badge-ghost badge-xs inline-flex items-center gap-1 opacity-70">
							<SvgIcon name="volume-2" size={10} />
							{shot.sfx}
						</span>
					)}
				</div>
			</div>
		</article>
	);
}

function PlanSection({
	story,
	summary,
	characters,
	shots,
}: {
	story: string;
	summary: string;
	characters: ReviewedCharacter[];
	shots: ReviewedShot[];
}) {
	return (
		<div className="space-y-4">
			{(story || summary) && (
				<div className="rounded-xl bg-secondary/10 p-4">
					{story && (
						<p className="m-0 whitespace-pre-wrap text-sm leading-relaxed text-base-content/80">
							{story}
						</p>
					)}
					{summary && (
						<p className="mt-3 border-t border-base-content/10 pt-3 text-xs leading-relaxed text-base-content/55">
							{summary}
						</p>
					)}
				</div>
			)}
			{shots.length > 0 && (
				<div className="overflow-hidden rounded-xl border border-base-content/10">
					<table className="w-full text-xs">
						<thead className="bg-base-200/80">
							<tr>
								<th className="w-10 px-3 py-2 text-left font-semibold">#</th>
								<th className="px-3 py-2 text-left font-semibold">描述</th>
								<th className="w-20 px-3 py-2 text-left font-semibold">运镜</th>
								<th className="w-16 px-3 py-2 text-left font-semibold">时长</th>
								<th className="w-28 px-3 py-2 text-left font-semibold">角色</th>
							</tr>
						</thead>
						<tbody>
							{shots.map((shot, i) => {
								const characterNames = shot.character_ids
									?.map(
										(id) =>
											characters.find((character) => character.id === id)?.name,
									)
									.filter(Boolean);
								return (
									<tr
										key={shot.id}
										className={i % 2 === 0 ? "bg-base-100" : "bg-base-200/30"}
									>
<td className="px-3 py-2 font-mono text-base-content/60 truncate max-w-0">
  {shot.order}
</td>
<td className="px-3 py-2 text-base-content/80 truncate max-w-0">
  {shot.description}
</td>
<td className="px-3 py-2 text-base-content/60 truncate max-w-0">
  {shot.camera || "-"}
</td>
<td className="px-3 py-2 text-base-content/60 truncate max-w-0">
  {shot.duration ? `${shot.duration}s` : "-"}
</td>
<td className="px-3 py-2 text-base-content/60 truncate max-w-0">
  {characterNames?.length ? characterNames.join("、") : "-"}
</td>
									</tr>
								);
							})}
						</tbody>
					</table>
				</div>
			)}
		</div>
	);
}

export class StoryboardBoardShapeUtil extends ShapeUtil<StoryboardBoardShape> {
	static override type = "storyboard-board" as const;

	static override props: RecordProps<StoryboardBoardShape> = {
		w: T.number,
		h: T.number,
		projectId: T.number,
		story: T.string,
		summary: T.string,
		characters: T.any,
		shots: T.any,
		videoUrl: T.string,
		videoTitle: T.string,
		visibleSections: T.any,
		sectionStates: T.any,
		placeholders: T.any,
		statusLabels: T.any,
		placeholderTexts: T.any,
		downloadUrl: T.string,
	};

	getDefaultProps(): StoryboardBoardShape["props"] {
		return {
			w: 920,
			h: 600,
			projectId: 0,
			story: "",
			summary: "",
			characters: [],
			shots: [],
			videoUrl: "",
			videoTitle: "最终视频",
			visibleSections: ["plan"],
			sectionStates: {},
			placeholders: {},
			statusLabels: {},
			placeholderTexts: {},
			downloadUrl: "",
		};
	}

	override canEdit() {
		return false;
	}
	override canResize() {
		return false;
	}
	override canCull() {
		return false;
	}
	override hideRotateHandle() {
		return true;
	}

	getGeometry(shape: StoryboardBoardShape): Geometry2d {
		const size = this.editor ? getShapeSize(this.editor, shape.id) : undefined;
		return new Rectangle2d({
			width: shape.props.w,
			height: size?.height ?? shape.props.h,
			isFilled: true,
		});
	}

	component(shape: StoryboardBoardShape) {
		const {
			w,
			story,
			summary,
			characters,
			shots,
			videoUrl,
			videoTitle,
			visibleSections,
			sectionStates,
			placeholders,
			statusLabels,
			placeholderTexts,
		} = shape.props;
		const ref = useDomSize(shape, this.editor ?? null);
		const typedCharacters = characters as ReviewedCharacter[];
		const typedShots = shots as ReviewedShot[];
		const sections = visibleSections as StoryboardBoardSectionKey[];

		return (
			<HTMLContainer
				style={{ width: w, pointerEvents: "all", overflow: "visible" }}
			>
				<div ref={ref} style={{ width: w }}>
					<div className="rounded-[1.6rem] bg-base-200/30 p-5">
						{sections.map((section, index) => {
							const showFlowConnector = index > 0;
							return (
								<Fragment key={section}>
									{showFlowConnector && (
										<div
											className="pointer-events-none flex h-16 items-center justify-center text-primary/70"
											aria-hidden="true"
										>
											<svg
												viewBox="0 0 920 64"
												className="h-16 w-full overflow-visible"
												preserveAspectRatio="none"
											>
												<path
													d="M 458 4 C 356 18 564 44 462 60"
													fill="none"
													stroke="currentColor"
													strokeWidth="4"
													strokeLinecap="round"
													strokeDasharray="10 10"
												/>
												<path
													d="M 462 60 L 450 47 M 462 60 L 476 48"
													fill="none"
													stroke="currentColor"
													strokeWidth="4"
													strokeLinecap="round"
												/>
											</svg>
											<span className="absolute rounded-full border border-base-content/20 bg-base-100 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-base-content/60 shadow-aperture">
												{SECTION_FLOW_COPY[section] ?? "流程推进"}
											</span>
										</div>
									)}

									{section === "plan" && (
										<SectionShell
											sectionKey="plan"
											sectionTitle={SECTION_TITLES.plan}
											statusLabel={statusLabels.plan ?? "待生成"}
											placeholder={Boolean(placeholders.plan)}
											placeholderText={
												placeholderTexts.plan ??
												getWorkspaceSectionPlaceholderText("plan")
											}
										>
											<PlanSection
												story={story}
												summary={summary}
												characters={typedCharacters}
												shots={typedShots}
											/>
										</SectionShell>
									)}

									{section === "render" && (
										<SectionShell
											sectionKey="render"
											sectionTitle={SECTION_TITLES.render}
											statusLabel={statusLabels.render ?? "待生成"}
											placeholder={Boolean(placeholders.render)}
											placeholderText={
												placeholderTexts.render ??
												getWorkspaceSectionPlaceholderText("render")
											}
										>
											<div className="space-y-6">
												<div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
													{typedCharacters.map((character) => (
														<CharacterCard key={character.id} character={character} />
													))}
												</div>
												<div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
													{typedShots.map((shot) => (
														<ShotCard key={shot.id} shot={shot} />
													))}
												</div>
											</div>
										</SectionShell>
									)}

									{section === "compose" && (
										<SectionShell
											sectionKey="compose"
											sectionTitle={SECTION_TITLES.compose}
											statusLabel={statusLabels.compose ?? "待生成"}
											placeholder={!videoUrl && Boolean(placeholders.compose)}
											placeholderText={
												placeholderTexts.compose ??
												getWorkspaceSectionPlaceholderText("compose")
											}
											placeholderIcon={VIDEO_PLACEHOLDER_ICON}
										>
											{videoUrl ? (
												<div className="space-y-3">
													<video
														className="w-full aspect-video rounded-xl bg-base-300"
														src={videoUrl}
														controls
														onPointerDown={stopCanvasDrag}
														aria-label={videoTitle}
													>
														<track
															kind="captions"
															label="中文"
															srcLang="zh"
															default
															src={`data:text/vtt;charset=utf-8,${encodeURIComponent(`WEBVTT\n\n00:00:00.000 --> 00:00:05.000\n${videoTitle || "最终视频"}`)}`}
														/>
													</video>
													<div className="flex justify-end">
												<Button
													variant="primary"
													size="sm"
													className="gap-1 text-xs"
													onPointerDown={stopCanvasDrag}
													onClick={() => {
														const url = getStaticUrl(shape.props.downloadUrl || videoUrl);
														if (url) {
															const a = document.createElement("a");
															a.href = url;
															a.download = "";
															document.body.appendChild(a);
															a.click();
															document.body.removeChild(a);
														}
													}}
												>
													<SvgIcon name="download" size={12} />
													下载
												</Button>
													</div>
												</div>
											) : null}
										</SectionShell>
									)}
								</Fragment>
							);
						})}

						<div className="sr-only" aria-live="polite">
							{sections
								.map(
									(section) =>
										`${SECTION_TITLES[section]} ${sectionStates[section] ?? "draft"}`,
								)
								.join("，")}
						</div>
					</div>
				</div>
			</HTMLContainer>
		);
	}

	indicator(shape: StoryboardBoardShape) {
		const size = this.editor ? getShapeSize(this.editor, shape.id) : undefined;
		return (
			<rect
				width={shape.props.w}
				height={size?.height ?? shape.props.h}
				rx={24}
			/>
		);
	}
}
