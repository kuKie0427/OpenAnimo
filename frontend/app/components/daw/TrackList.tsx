import { useState, useCallback, useRef } from "react";
import { clsx } from "clsx";
import { PlusIcon } from "@heroicons/react/24/outline";
import { TrackItem } from "./TrackItem";

interface TrackListProps {
	items: Array<{
		id: number;
		title: string;
		thumbnail?: string;
		status: "draft" | "processing" | "completed" | "error";
	}>;
	selectedId: number | null;
	onSelect: (id: number) => void;
	onReorder?: (fromIndex: number, toIndex: number) => void;
}

export function TrackList({
	items,
	selectedId,
	onSelect,
	onReorder,
}: TrackListProps) {
	const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
	const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
	const containerRef = useRef<HTMLDivElement>(null);

	const selectedIndex = items.findIndex((item) => item.id === selectedId);

	const handleKeyDown = useCallback(
		(event: React.KeyboardEvent) => {
			if (items.length === 0) return;

			switch (event.key) {
				case "ArrowUp":
					event.preventDefault();
					onSelect(
						selectedIndex <= 0
							? items[items.length - 1].id
							: items[selectedIndex - 1].id
					);
					break;
				case "ArrowDown":
					event.preventDefault();
					onSelect(
						selectedIndex >= items.length - 1
							? items[0].id
							: items[selectedIndex + 1].id
					);
					break;
				case "Enter":
					if (selectedId !== null) {
						onSelect(selectedId);
					}
					break;
				default:
					break;
			}
		},
		[items, selectedIndex, selectedId, onSelect]
	);

	const handleDragStart = useCallback(
		(event: React.DragEvent, index: number) => {
			if (!onReorder) return;
			event.dataTransfer.effectAllowed = "move";
			event.dataTransfer.setData("text/plain", String(index));
			setDraggedIndex(index);
		},
		[onReorder]
	);

	const handleDragOver = useCallback(
		(event: React.DragEvent, index: number) => {
			event.preventDefault();
			if (!onReorder || draggedIndex === null) return;
			event.dataTransfer.dropEffect = "move";
			if (draggedIndex !== index) {
				setDragOverIndex(index);
			}
		},
		[onReorder, draggedIndex]
	);

	const handleDrop = useCallback(
		(event: React.DragEvent, dropIndex: number) => {
			event.preventDefault();
			if (!onReorder || draggedIndex === null) return;

			const fromIndex = draggedIndex;
			if (fromIndex !== dropIndex) {
				onReorder(fromIndex, dropIndex);
			}
			setDraggedIndex(null);
			setDragOverIndex(null);
		},
		[onReorder, draggedIndex]
	);

	const handleDragEnd = useCallback(() => {
		setDraggedIndex(null);
		setDragOverIndex(null);
	}, []);

	return (
		<div
			ref={containerRef}
			className="w-60 lg:w-72 flex-shrink-0 bg-base-200 border-r border-base-content/10 overflow-y-auto"
			tabIndex={0}
			onKeyDown={handleKeyDown}
			role="listbox"
			aria-label="Track list"
		>
			{/* Header */}
			<div className="flex items-center justify-between mb-2 px-2">
				<span className="text-xs font-mono text-base-content/50 uppercase tracking-wider">
					{items.length} items
				</span>
				<button
					type="button"
					className="btn btn-ghost btn-xs"
					aria-label="Add track"
				>
					<PlusIcon className="w-4 h-4" />
				</button>
			</div>

			{/* List */}
			<div className="space-y-1 px-2">
				{items.length === 0 ? (
					<div className="py-8 text-center text-sm text-base-content/50">
						No tracks yet
					</div>
				) : (
					items.map((item, index) => (
						<div
							key={item.id}
							draggable={!!onReorder}
							onDragStart={(e) => handleDragStart(e, index)}
							onDragOver={(e) => handleDragOver(e, index)}
							onDrop={(e) => handleDrop(e, index)}
							onDragEnd={handleDragEnd}
							className={clsx(
								"transition-colors",
								dragOverIndex === index &&
									draggedIndex !== index &&
									"before:absolute before:inset-x-0 before:top-0 before:h-0.5 before:bg-primary",
								onReorder &&
									(draggedIndex === index
										? "cursor-grabbing"
										: "cursor-grab")
							)}
							role="option"
							aria-selected={selectedId === item.id}
						>
							<TrackItem
								item={item}
								selected={selectedId === item.id}
								onClick={() => onSelect(item.id)}
							/>
						</div>
					))
				)}
			</div>
		</div>
	);
}
