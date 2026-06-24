import {
	HTMLContainer,
	Rectangle2d,
	ShapeUtil,
	T,
	type Geometry2d,
	type RecordProps,
} from "tldraw";
import type { CharacterSectionShape, ReviewedCharacter } from "./types";
import { SectionShell } from "./SectionShell";
import { getStaticUrl } from "~/services/api";
import { charactersApi } from "~/services/api";
import {
	getWorkspaceSectionPlaceholderText,
	getWorkspaceSectionStatusLabel,
} from "~/utils/workspaceStatus";
import { canvasEvents } from "../canvasEvents";
import type { ShapeActionName } from "../canvasEvents";
import { SvgIcon } from "~/components/ui/SvgIcon";
import { useDomSize, getShapeSize } from "~/hooks/useDomSize";
import { useState, useCallback } from "react";

function CharacterCard({ char }: { char: ReviewedCharacter }) {
	const isApproved = char.approval_state === "approved";
	const currentImage = getStaticUrl(char.image_url);
	const approvedImage = getStaticUrl(char.approved_image_url);
	const displayImage =
		isApproved && approvedImage ? approvedImage : currentImage;

	const [showBible, setShowBible] = useState(false);

	const handleAction = (action: ShapeActionName) => {
		if (
			action === "regenerate" &&
			!window.confirm(`重新生成角色 ${char.name}？`)
		)
			return;
		if (action === "approve" && !window.confirm(`批准角色 ${char.name}？`))
			return;
		canvasEvents.emit("shape-action", {
			shapeId: "",
			action,
			entityType: "character",
			entityId: char.id,
			feedbackType: "render",
		});
	};

	return (
		<div
			className={`card card-compact bg-base-200 border border-base-content/15 group relative ${
				isApproved ? "ring-1 ring-success/20" : ""
			}`}
		>
			{displayImage && (
				<figure className="relative aspect-[4/3]">
					<img
						src={displayImage}
						alt={char.name}
						className="w-full h-full object-cover"
					/>
					<div className="absolute inset-0 bg-base-content/0 group-hover:bg-base-content/20 transition-colors flex items-center justify-center gap-1.5 opacity-0 group-hover:opacity-100">
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
						<button
							type="button"
							className="btn btn-xs btn-circle btn-ghost text-primary hover:bg-primary/30"
							title="添加到资产库"
							onClick={() => handleAction("add-to-assets")}
						>
							<SvgIcon name="star" size={12} />
						</button>
					</div>
				</figure>
			)}
			<div className="card-body p-2">
				<div className="flex items-center gap-1.5">
					<span
						className={`w-2 h-2 rounded-full ${isApproved ? "bg-success" : "bg-warning"}`}
					/>
					<span className="font-semibold text-xs">{char.name}</span>
					<span className="badge badge-ghost badge-xs ml-auto">
						v{char.approval_version}
					</span>
				</div>
				{char.description && (
					<p className="text-xs text-base-content/50">{char.description}</p>
				)}
				<div className="flex items-center gap-1 mt-1">
					{/* Bible button */}
					<button
						type="button"
						className={`btn btn-xs btn-ghost gap-0.5 ${
							showBible ? "btn-active" : ""
						}`}
						onClick={() => setShowBible(!showBible)}
						title="角色圣经"
					>
						<SvgIcon name="book-open" size={12} />
						<span className="text-[10px]">圣经</span>
					</button>
					{/* Embedding indicator */}
					{char.has_embedding && (
						<span
							className="badge badge-primary badge-xs inline-flex items-center gap-0.5"
							title="人脸嵌入已计算"
						>
							人脸
							<SvgIcon name="check" size={10} />
						</span>
					)}
				</div>
				{/* Bible Panel */}
				{showBible && (
					<BiblePanel
						characterId={char.id}
						initialVisualNotes={char.visual_notes ?? null}
						initialReferenceImages={char.reference_images || []}
						initialHasEmbedding={char.has_embedding ?? false}
						onClose={() => setShowBible(false)}
					/>
				)}
			</div>
		</div>
	);
}

function BiblePanel({
	characterId,
	initialVisualNotes,
	initialReferenceImages,
	initialHasEmbedding,
	onClose,
}: {
	characterId: number;
	initialVisualNotes: string | null;
	initialReferenceImages: string[];
	initialHasEmbedding: boolean;
	onClose: () => void;
}) {
	const [visualNotes, setVisualNotes] = useState(initialVisualNotes || "");
	const [referenceImages, setReferenceImages] = useState<string[]>(initialReferenceImages);
	const [hasEmbedding, setHasEmbedding] = useState(initialHasEmbedding);
	const [saving, setSaving] = useState(false);
	const [computing, setComputing] = useState(false);
	const [newImageUrl, setNewImageUrl] = useState("");

	const saveVisualNotes = useCallback(async () => {
		setSaving(true);
		try {
			await charactersApi.updateBible(characterId, { visual_notes: visualNotes || null });
		} catch (e) {
			console.error("Failed to save visual notes", e);
		} finally {
			setSaving(false);
		}
	}, [characterId, visualNotes]);

	const addImage = useCallback(async () => {
		if (!newImageUrl.trim()) return;
		setSaving(true);
		try {
			const result = await charactersApi.addReferenceImage(
				characterId,
				newImageUrl.trim(),
			);
			setReferenceImages(result.reference_images);
			setNewImageUrl("");
		} catch (e) {
			console.error("Failed to add reference image", e);
		} finally {
			setSaving(false);
		}
	}, [characterId, newImageUrl]);

	const removeImage = useCallback(
		async (index: number) => {
			setSaving(true);
			try {
				await charactersApi.deleteReferenceImage(characterId, index);
				setReferenceImages((prev) => prev.filter((_, i) => i !== index));
			} catch (e) {
				console.error("Failed to delete reference image", e);
			} finally {
				setSaving(false);
			}
		},
		[characterId],
	);

	const computeEmbedding = useCallback(async () => {
		setComputing(true);
		try {
			await charactersApi.computeEmbedding(characterId);
			setHasEmbedding(true);
		} catch (e) {
			console.error("Failed to compute embedding", e);
		} finally {
			setComputing(false);
		}
	}, [characterId]);

	return (
		<div className="mt-2 p-2 bg-base-300 rounded-lg text-xs space-y-2">
			<div className="flex items-center justify-between">
				<span className="font-semibold text-[11px]">角色圣经</span>
				<button
					type="button"
					className="btn btn-xs btn-ghost btn-circle"
					onClick={onClose}
				>
					<SvgIcon name="x" size={12} />
				</button>
			</div>

			{/* Visual Notes */}
			<div>
				<label className="label text-[10px]">
					视觉特征 (发色、瞳色、体型、标志配饰等)
				</label>
				<textarea
					className="textarea textarea-bordered textarea-xs w-full h-16"
					value={visualNotes}
					onChange={(e) => setVisualNotes(e.target.value)}
					onBlur={saveVisualNotes}
					placeholder="描述角色的关键视觉特征..."
				/>
			</div>

			{/* Reference Images */}
			<div>
				<label className="label text-[10px]">参考图</label>
				{referenceImages.length > 0 && (
					<div className="grid grid-cols-3 gap-1 mb-1">
						{referenceImages.map((url, idx) => (
							<div key={idx} className="relative group">
								<img
									src={getStaticUrl(url) ?? undefined}
									alt={`参考图 ${idx + 1}`}
									className="w-full h-16 object-cover rounded"
								/>
								<button
									type="button"
									className="btn btn-xs btn-circle btn-ghost absolute top-0 right-0 opacity-0 group-hover:opacity-100 text-error"
									onClick={() => removeImage(idx)}
								>
									<SvgIcon name="x" size={12} />
								</button>
							</div>
						))}
					</div>
				)}
				<div className="flex gap-1">
					<input
						type="text"
						className="input input-bordered input-xs flex-1"
						placeholder="图片 URL"
						value={newImageUrl}
						onChange={(e) => setNewImageUrl(e.target.value)}
						onKeyDown={(e) => e.key === "Enter" && addImage()}
					/>
					<button
						type="button"
						className="btn btn-xs btn-primary"
						onClick={addImage}
						disabled={saving || !newImageUrl.trim()}
					>
						添加
					</button>
				</div>
			</div>

			{/* Embedding Status */}
			<div className="flex items-center gap-2">
				<span className="text-[10px]">人脸特征:</span>
				{hasEmbedding ? (
					<span className="badge badge-success badge-xs">已计算</span>
				) : (
					<button
						type="button"
						className="btn btn-xs btn-outline btn-info"
						onClick={computeEmbedding}
						disabled={computing}
					>
						{computing ? "计算中..." : "计算人脸特征"}
					</button>
				)}
			</div>

			{saving && <span className="text-[10px] text-base-content/50">保存中...</span>}
		</div>
	);
}

export class CharacterSectionShapeUtil extends ShapeUtil<CharacterSectionShape> {
	static override type = "character-section" as const;

	static override props: RecordProps<CharacterSectionShape> = {
		w: T.number,
		h: T.number,
		characters: T.any,
		sectionState: T.string,
		placeholder: T.boolean,
		statusLabel: T.string,
		placeholderText: T.string,
		sectionTitle: T.string,
	};

	getDefaultProps(): CharacterSectionShape["props"] {
		return {
			w: 800,
			h: 200,
			characters: [],
			sectionState: "blocked",
			placeholder: true,
			statusLabel: getWorkspaceSectionStatusLabel("blocked"),
			placeholderText: getWorkspaceSectionPlaceholderText("render"),
			sectionTitle: "角色",
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

	getGeometry(shape: CharacterSectionShape): Geometry2d {
		const size = this.editor ? getShapeSize(this.editor, shape.id) : undefined;
		return new Rectangle2d({
			width: shape.props.w,
			height: size?.height ?? shape.props.h,
			isFilled: true,
		});
	}

	component(shape: CharacterSectionShape) {
		const { characters, placeholder, placeholderText, statusLabel, w } =
			shape.props;
		const ref = useDomSize(shape, this.editor ?? null);

		return (
			<HTMLContainer
				style={{ width: w, pointerEvents: "all", overflow: "visible" }}
			>
				<div ref={ref} style={{ width: w }}>
					<SectionShell
						sectionKey="render"
						sectionTitle="角色"
						statusLabel={statusLabel}
						placeholder={placeholder}
						placeholderText={placeholderText}
					>
						<div className="grid grid-cols-2 gap-2">
							{(characters as ReviewedCharacter[]).map((char) => (
								<CharacterCard key={char.id} char={char} />
							))}
						</div>
					</SectionShell>
				</div>
			</HTMLContainer>
		);
	}

	indicator() {
		return null;
	}
}
