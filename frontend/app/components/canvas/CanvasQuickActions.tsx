import {
  ArrowsRightLeftIcon,
  ArrowsUpDownIcon,
  QueueListIcon,
  ArrowUturnLeftIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";

interface CanvasQuickActionsProps {
  selectedCount: number;
  onAlignH: () => void;
  onAlignV: () => void;
  onDistributeH: () => void;
  onDistributeV: () => void;
  onGroup: () => void;
  onUngroup: () => void;
  onDelete: () => void;
}

export function CanvasQuickActions({
  selectedCount,
  onAlignH,
  onAlignV,
  onDistributeH: _onDistributeH,
  onDistributeV: _onDistributeV,
  onGroup,
  onUngroup,
  onDelete,
}: CanvasQuickActionsProps) {
  if (selectedCount < 2) return null;

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1 px-3 py-2 bg-base-100/90 backdrop-blur-sm rounded-lg shadow-aperture border border-base-content/10">
      <span className="text-xs text-base-content/60 mr-2">
        {selectedCount} 个选中
      </span>
      <button onClick={onAlignH} className="btn btn-ghost btn-xs" title="水平对齐">
        <ArrowsRightLeftIcon className="w-3.5 h-3.5" />
      </button>
      <button onClick={onAlignV} className="btn btn-ghost btn-xs" title="垂直对齐">
        <ArrowsUpDownIcon className="w-3.5 h-3.5" />
      </button>
      <div className="divider divider-horizontal mx-1" />
      <button onClick={onGroup} className="btn btn-ghost btn-xs" title="分组">
        <QueueListIcon className="w-3.5 h-3.5" />
      </button>
      <button onClick={onUngroup} className="btn btn-ghost btn-xs" title="取消分组">
        <ArrowUturnLeftIcon className="w-3.5 h-3.5" />
      </button>
      <div className="divider divider-horizontal mx-1" />
      <button onClick={onDelete} className="btn btn-ghost btn-xs text-error" title="删除">
        <TrashIcon className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
