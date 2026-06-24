import { PencilIcon } from "@heroicons/react/24/outline";
import { clsx } from "clsx";

interface ListItemProps {
  shape: {
    id: string;
    type: string;
    content: any;
    x: number;
    y: number;
  };
  isSelected: boolean;
  onSelect: (selected: boolean) => void;
  onClick: () => void;
  onEdit: () => void;
  index?: number;
}

const TYPE_LABELS: Record<string, string> = {
  "plan-section": "规划",
  "character-section": "角色",
  "storyboard-section": "分镜",
  "compose-section": "合成",
};

const TYPE_COLORS: Record<string, string> = {
  "plan-section": "badge-primary",
  "character-section": "badge-accent",
  "storyboard-section": "badge-secondary",
  "compose-section": "badge-ghost",
};

export function ListItem({
  shape,
  isSelected,
  onSelect,
  onClick,
  onEdit,
  index = 0,
}: ListItemProps) {
  return (
    <div
      data-testid={`list-item-${index}`}
      className={clsx(
        "flex items-center gap-3 p-3 rounded-lg transition-all duration-200",
        "list-item",
        isSelected
          ? "bg-primary/10 border border-primary/20"
          : "bg-base-200 border border-transparent hover:border-base-content/10"
      )}
    >
      <input
        type="checkbox"
        checked={isSelected}
        onChange={(e) => onSelect(e.target.checked)}
        className="checkbox checkbox-xs checkbox-primary"
      />

      <span className={`badge badge-xs ${TYPE_COLORS[shape.type]}`}>
        {TYPE_LABELS[shape.type]}
      </span>

      <div className="flex-1 min-w-0" onClick={onClick}>
        <h4 className="text-sm font-medium truncate">
          {shape.content?.title || "未命名"}
        </h4>
        {shape.content?.description && (
          <p className="text-xs text-base-content/60 truncate mt-1">
            {shape.content.description}
          </p>
        )}
      </div>

      {shape.content?.imageUrl && (
        <img
          src={shape.content.imageUrl}
          alt=""
          className="w-10 h-10 rounded object-cover"
        />
      )}

      <button
        onClick={onEdit}
        className="btn btn-ghost btn-xs"
        title="编辑"
      >
        <PencilIcon className="w-3 h-3" />
      </button>
    </div>
  );
}
