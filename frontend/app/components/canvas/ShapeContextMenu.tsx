import { useCallback, useEffect, useRef, useState } from "react";
import { useEditor, type TLShapeId } from "tldraw";
import { projectsApi } from "~/services/api";
import { useEditorStore } from "~/stores/editorStore";
import { toast } from "~/utils/toast";
import { ConfirmModal } from "~/components/ui/ConfirmModal";
import { Button } from "~/components/ui/Button";
import { SHAPE_TYPES } from "./shapes/types";

interface MenuPosition {
	x: number;
	y: number;
}

interface ShapeContext {
	shapeType: string;
	shapeId: string;
	feedbackType: "plan" | "render" | "compose";
}

const ACTIONS: Record<string, { label: string; action: string }[]> = {
	[SHAPE_TYPES.STORYBOARD_BOARD]: [
		{ label: "重新规划", action: "regenerate" },
		{ label: "修改故事", action: "edit" },
	],
	[SHAPE_TYPES.SCRIPT_SECTION]: [
		{ label: "重新规划", action: "regenerate" },
		{ label: "修改故事", action: "edit" },
	],
	[SHAPE_TYPES.PLAN_SECTION]: [
		{ label: "重新规划", action: "regenerate" },
		{ label: "修改故事", action: "edit" },
	],
	[SHAPE_TYPES.VIDEO_SECTION]: [
		{ label: "重新合成视频", action: "regenerate" },
	],
	[SHAPE_TYPES.COMPOSE_SECTION]: [
		{ label: "重新合成视频", action: "regenerate" },
	],
};

const SHAPE_TO_ENTITY: Record<
	string,
	{ feedbackType: "plan" | "render" | "compose" }
> = {
	[SHAPE_TYPES.STORYBOARD_BOARD]: { feedbackType: "plan" },
	[SHAPE_TYPES.SCRIPT_SECTION]: { feedbackType: "plan" },
	[SHAPE_TYPES.PLAN_SECTION]: { feedbackType: "plan" },
	[SHAPE_TYPES.VIDEO_SECTION]: { feedbackType: "compose" },
	[SHAPE_TYPES.COMPOSE_SECTION]: { feedbackType: "compose" },
};

export function ShapeContextMenu() {
	const editor = useEditor();
	const currentRunId = useEditorStore((state) => state.currentRunId);
	const [position, setPosition] = useState<MenuPosition | null>(null);
	const [context, setContext] = useState<ShapeContext | null>(null);
	const [confirmAction, setConfirmAction] = useState<string | null>(null);
	const [editContent, setEditContent] = useState("");
	const [isEditing, setIsEditing] = useState(false);
	const menuRef = useRef<HTMLDivElement>(null);
	const firstBtnRef = useRef<HTMLButtonElement>(null);

	const close = useCallback(() => {
		setPosition(null);
		setContext(null);
		setConfirmAction(null);
		setIsEditing(false);
		setEditContent("");
	}, []);

	const handleContextMenu = useCallback(
		(e: MouseEvent) => {
			const selectedShapes = editor.getSelectedShapes();
			if (selectedShapes.length !== 1) return;

			const shape = selectedShapes[0];
			const mapping = SHAPE_TO_ENTITY[shape.type];
			if (!mapping) return;

			e.preventDefault();
			e.stopPropagation();

			setContext({
				shapeType: shape.type,
				shapeId: shape.id,
				feedbackType: mapping.feedbackType,
			});
			setPosition({ x: e.clientX, y: e.clientY });
		},
		[editor],
	);

	const submitFeedback = useCallback(
		(content: string) => {
			if (!context) return;

			const shape = editor.getShape(context.shapeId as TLShapeId);
			let shapeProjectId: number | null = null;
			if (shape) {
				const props = shape.props as Record<string, unknown>;
				if (typeof props.projectId === "number") {
					shapeProjectId = props.projectId;
				}
			}
			if (!shapeProjectId) {
				toast.error({ title: "画布操作", message: "无法确定项目" });
				return;
			}

			projectsApi
				.feedback(
					shapeProjectId,
					content,
					currentRunId ?? undefined,
					context.feedbackType,
				)
				.then(() => toast.success({ title: "画布操作", message: "已提交" }))
				.catch(() => toast.error({ title: "画布操作", message: "提交失败" }));

			close();
		},
		[context, currentRunId, editor, close],
	);

	const handleAction = useCallback((action: string) => {
		if (action === "regenerate") {
			setConfirmAction(action);
			return;
		}
		if (action === "edit") {
			setIsEditing(true);
			setEditContent("");
			return;
		}
	}, []);

	const handleConfirmRegenerate = useCallback(() => {
		submitFeedback("请重新生成当前阶段");
		setConfirmAction(null);
	}, [submitFeedback]);

	const handleSaveEdit = useCallback(() => {
		const content = editContent.trim();
		if (content) submitFeedback(content);
		else close();
	}, [editContent, submitFeedback, close]);

	const handleClickOutside = useCallback(
		(e: MouseEvent) => {
			if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
				close();
			}
		},
		[close],
	);

	const handleKeyDown = useCallback(
		(e: KeyboardEvent) => {
			if (e.key === "Escape") close();
		},
		[close],
	);

	useEffect(() => {
		const canvasEl = editor.getContainer();
		canvasEl.addEventListener("contextmenu", handleContextMenu);
		document.addEventListener("mousedown", handleClickOutside);
		document.addEventListener("keydown", handleKeyDown);

		if (position && !isEditing) {
			firstBtnRef.current?.focus();
		}

		return () => {
			canvasEl.removeEventListener("contextmenu", handleContextMenu);
			document.removeEventListener("mousedown", handleClickOutside);
			document.removeEventListener("keydown", handleKeyDown);
		};
	}, [
		editor,
		handleContextMenu,
		handleClickOutside,
		handleKeyDown,
		position,
		isEditing,
	]);

	if (!position || !context) return null;

	const actions = ACTIONS[context.shapeType] || [];

	return (
		<>
			<div
				ref={menuRef}
				className="fixed z-[var(--z-popover,60)] min-w-[180px] py-1 rounded-lg card-screen"
				style={{ left: position.x, top: position.y }}
				role="menu"
			>
				{actions.map(({ label, action }, i) => (
					<button
						ref={i === 0 ? firstBtnRef : undefined}
						key={action}
						className="w-full px-3 py-2 text-left text-sm hover:bg-base-200/60 transition-shadow duration-200 hover:shadow-aperture font-heading"
						role="menuitem"
						onClick={() => handleAction(action)}
					>
						{label}
					</button>
				))}
			</div>
			{isEditing && (
				<div
					className="fixed inset-0 z-[var(--z-modal-backdrop,40)] flex items-center justify-center bg-base-content/20"
					onClick={(e) => {
						if (e.target === e.currentTarget) close();
					}}
				>
					<div
						className="card-screen p-4 w-80 space-y-3"
						onClick={(e) => e.stopPropagation()}
					>
						<h3 className="font-heading font-bold text-sm m-0">修改意见</h3>
						<textarea
							className="input-field w-full text-sm p-2 resize-none"
							rows={3}
							placeholder="请描述修改方向"
							value={editContent}
							autoFocus
							onChange={(e) => setEditContent(e.currentTarget.value)}
							onKeyDown={(e) => {
								if (e.key === "Enter" && !e.shiftKey) {
									e.preventDefault();
									handleSaveEdit();
								}
								if (e.key === "Escape") close();
							}}
						/>
						<div className="flex justify-end gap-2">
							<button
								type="button"
								className="btn btn-sm btn-ghost"
								onClick={close}
							>
								取消
							</button>
<Button variant="primary" size="sm" onClick={handleSaveEdit}>
							提交
						</Button>
						</div>
					</div>
				</div>
			)}
			<ConfirmModal
				isOpen={Boolean(confirmAction)}
				onClose={() => setConfirmAction(null)}
				onConfirm={handleConfirmRegenerate}
				title="确认操作"
				message="重新生成会覆盖当前内容，确定？"
				variant="warning"
			/>
		</>
	);
}
