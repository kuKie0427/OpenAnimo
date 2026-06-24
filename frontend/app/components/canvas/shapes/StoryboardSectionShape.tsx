import {
	HTMLContainer,
	Rectangle2d,
	ShapeUtil,
	T,
	type Geometry2d,
	type RecordProps,
} from "tldraw";
import { useState } from "react";
import type { StoryboardSectionShape, ReviewedShot } from "./types";
import { SectionShell } from "./SectionShell";
import { getStaticUrl } from "~/services/api";
import {
	getWorkspaceSectionPlaceholderText,
	getWorkspaceSectionStatusLabel,
} from "~/utils/workspaceStatus";
import { canvasEvents } from "../canvasEvents";
import type { ShapeActionName } from "../canvasEvents";
import { SvgIcon } from "~/components/ui/SvgIcon";
import { useDomSize, getShapeSize } from "~/hooks/useDomSize";

function ShotCard({ shot }: { shot: ReviewedShot }) {
	const isApproved = shot.approval_state === "approved";
	const imageUrl = getStaticUrl(shot.image_url);
	const videoUrl = getStaticUrl(shot.video_url);
	const [isEditing, setIsEditing] = useState(false);
	const [editDialogue, setEditDialogue] = useState(shot.dialogue || "");
	const [editAction, setEditAction] = useState(shot.action || "");

	const handleAction = (action: ShapeActionName) => {
		if (
			action === "regenerate" &&
			!window.confirm(`重新生成镜头 ${shot.order}？`)
		)
			return;
		if (action === "approve" && !window.confirm(`批准镜头 ${shot.order}？`))
			return;
		if (action === "edit") {
			setIsEditing(true);
			return;
		}
		canvasEvents.emit("shape-action", {
			shapeId: "",
			action,
			entityType: "shot",
			entityId: shot.id,
			feedbackType: "render",
		});
	};

	const handleSaveEdit = () => {
		setIsEditing(false);
		const changes: string[] = [];
		if (editDialogue !== (shot.dialogue || ""))
			changes.push(`对话: "${editDialogue}"`);
		if (editAction !== (shot.action || "")) changes.push(`动作: ${editAction}`);
		if (changes.length > 0) {
			canvasEvents.emit("shape-action", {
				shapeId: "",
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
		<div
			className={`card card-compact bg-base-200 border border-base-content/15 min-w-0 group relative ${
				isApproved ? "ring-1 ring-success/20" : ""
			}`}
		>
			{imageUrl ? (
				<figure className="relative aspect-[4/3]">
					<img
						src={imageUrl}
						alt={`Shot ${shot.order}`}
						className="w-full h-full object-cover"
					/>
					<span className="badge badge-xs absolute top-1 right-1 bg-base-100/80">
						{shot.duration ? `${shot.duration}s` : "—"}
					</span>
					{shot.expression && (
						<span className="badge badge-xs badge-primary absolute bottom-1 left-1">
							{shot.expression}
						</span>
					)}
					<div className="absolute inset-0 bg-base-content/0 group-hover:bg-base-content/20 transition-colors flex items-center justify-center gap-1 opacity-0 group-hover:opacity-100">
						<button
							type="button"
							className="btn btn-xs btn-circle btn-ghost text-base-100 hover:bg-base-100/30"
							title="重新生成"
							onClick={() => handleAction("regenerate")}
						>
							<SvgIcon name="refresh-cw" size={12} />
						</button>
						<button
							type="button"
							className="btn btn-xs btn-circle btn-ghost text-base-100 hover:bg-base-100/30"
							title="编辑"
							onClick={() => handleAction("edit")}
						>
							<SvgIcon name="pencil" size={12} />
						</button>
						{videoUrl && (
							<button
								type="button"
								className="btn btn-xs btn-circle btn-ghost text-base-100 hover:bg-base-100/30"
								title="预览片段"
								onClick={() =>
									canvasEvents.emit("preview-video", {
										src: videoUrl,
										title: `镜头 ${shot.order}`,
									})
								}
							>
								<SvgIcon name="play" size={12} />
							</button>
						)}
						{!isApproved && (
							<button
								type="button"
								className="btn btn-xs btn-circle btn-ghost text-success hover:bg-success/30"
								title="批准"
								onClick={() => handleAction("approve")}
							>
								<SvgIcon name="check" size={12} />
							</button>
						)}
						<button
							type="button"
							className="btn btn-xs btn-circle btn-ghost text-info hover:bg-info/30"
							title="版本历史"
							onClick={() => handleAction("history")}
						>
							<SvgIcon name="clock-3" size={12} />
						</button>
					</div>
				</figure>
			) : (
				<div className="h-28 flex items-center justify-center bg-base-300">
					<span className="text-xs opacity-40">生成中...</span>
				</div>
			)}
			<div className="card-body p-2 gap-0.5">
				<div className="flex items-center gap-1.5">
					<span
						className={`w-2 h-2 rounded-full flex-shrink-0 ${
							isApproved ? "bg-success" : "bg-warning"
						}`}
					/>
					<span className="text-xs font-medium">镜头 {shot.order}</span>
					{shot.camera && (
						<span className="badge badge-ghost badge-xs ml-auto">
							{shot.camera}
						</span>
					)}
				</div>
				{shot.scene && (
					<p className="text-xs text-base-content/70 font-semibold">
						{shot.scene}
					</p>
				)}
				{shot.description && (
					<p className="text-xs text-base-content/50 line-clamp-2">
						{shot.description}
					</p>
				)}
				{isEditing ? (
					<div className="space-y-1 mt-1">
						<input
							type="text"
							className="input input-bordered input-xs bg-base-100/80 w-full text-xs"
							placeholder="动作"
							value={editAction}
							onChange={(e) => setEditAction(e.target.value)}
						/>
						<input
							type="text"
							className="input input-bordered input-xs bg-base-100/80 w-full text-xs"
							placeholder="对话"
							value={editDialogue}
							onChange={(e) => setEditDialogue(e.target.value)}
							onKeyDown={(e) => e.key === "Enter" && handleSaveEdit()}
						/>
						<div className="flex gap-1">
							<button
								type="button"
								className="btn btn-xs btn-primary btn-sm"
								onClick={handleSaveEdit}
							>
								保存
							</button>
							<button
								type="button"
								className="btn btn-xs btn-ghost btn-sm"
								onClick={() => setIsEditing(false)}
							>
								取消
							</button>
						</div>
					</div>
				) : (
					<>
						{shot.action && (
							<p className="text-xs text-accent/70 flex items-center gap-0.5">
								<SvgIcon name="chevron-right" size={10} />
								{shot.action}
							</p>
						)}
						{shot.dialogue && (
							<p className="text-xs text-primary/80 italic">
								{shot.tts_url && (
									<SvgIcon name="volume-2" size={10} className="mr-0.5 inline" />
								)}
								"{shot.dialogue}"
							</p>
						)}
					</>
				)}
				<div className="flex flex-wrap gap-0.5 mt-0.5">
					{shot.lighting && (
						<span className="badge badge-ghost badge-xs opacity-60 inline-flex items-center gap-0.5">
							<SvgIcon name="lightbulb" size={10} />
							{shot.lighting}
						</span>
					)}
					{shot.sfx && (
						<span className="badge badge-ghost badge-xs opacity-60 inline-flex items-center gap-0.5">
							<SvgIcon name="volume-2" size={10} />
							{shot.sfx}
						</span>
					)}
					{shot.bgm_type && (
						<span className="badge badge-info badge-xs opacity-70 inline-flex items-center gap-0.5">
							<SvgIcon name="music" size={10} />
							{shot.bgm_type}
						</span>
					)}
				</div>
			</div>
		</div>
	);
}

export class StoryboardSectionShapeUtil extends ShapeUtil<StoryboardSectionShape> {
	static override type = "storyboard-section" as const;

	static override props: RecordProps<StoryboardSectionShape> = {
		w: T.number,
		h: T.number,
		shots: T.any,
		sectionTitle: T.string,
		sectionState: T.string,
		placeholder: T.boolean,
		statusLabel: T.string,
		placeholderText: T.string,
	};

	getDefaultProps(): StoryboardSectionShape["props"] {
		return {
			w: 800,
			h: 200,
			shots: [],
			sectionTitle: "分镜画面",
			sectionState: "blocked",
			placeholder: true,
			statusLabel: getWorkspaceSectionStatusLabel("blocked"),
			placeholderText: getWorkspaceSectionPlaceholderText("render"),
		};
	}

	override canEdit() {
		return true;
	}
	override canResize() {
		return false;
	}
	override canCull() {
		return false;
	}

	getGeometry(shape: StoryboardSectionShape): Geometry2d {
		const size = this.editor ? getShapeSize(this.editor, shape.id) : undefined;
		return new Rectangle2d({
			width: shape.props.w,
			height: size?.height ?? shape.props.h,
			isFilled: true,
		});
	}

	component(shape: StoryboardSectionShape) {
		const {
			shots,
			sectionTitle,
			placeholder,
			placeholderText,
			statusLabel,
			w,
		} = shape.props;
		const typedShots = (shots ?? []) as ReviewedShot[];
		const ref = useDomSize(shape, this.editor ?? null);

		return (
			<HTMLContainer
				style={{ width: w, pointerEvents: "all", overflow: "visible" }}
			>
				<div ref={ref} style={{ width: w }}>
					<SectionShell
						sectionKey="render"
						sectionTitle={sectionTitle}
						statusLabel={statusLabel}
						placeholder={placeholder}
						placeholderText={placeholderText}
					>
						{!placeholder && (
							<div>
								{typedShots.length > 0 && (
									<div className="grid grid-cols-3 gap-2">
										{typedShots.map((shot) => (
											<ShotCard key={shot.id} shot={shot} />
										))}
									</div>
								)}
							</div>
						)}
					</SectionShell>
				</div>
			</HTMLContainer>
		);
	}

	indicator() {
		return null;
	}
}
