import { MagnifyingGlassIcon } from "@heroicons/react/24/outline";

interface ListHeaderProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  typeFilter: string;
  onTypeFilterChange: (type: string) => void;
  sortBy: "name" | "type" | "position";
  onSortChange: (sort: "name" | "type" | "position") => void;
  selectedCount: number;
  totalCount: number;
  onSelectAll: () => void;
  onDelete: () => void;
}

export function ListHeader({
  searchQuery,
  onSearchChange,
  typeFilter,
  onTypeFilterChange,
  sortBy,
  onSortChange,
  selectedCount,
  totalCount,
  onSelectAll,
  onDelete,
}: ListHeaderProps) {
  return (
    <div className="flex items-center gap-4 px-4 py-3 bg-base-200 border-b border-base-content/10">
      <div className="flex items-center gap-2 flex-1">
        <MagnifyingGlassIcon className="w-4 h-4 text-base-content/40" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="搜索..."
          className="input input-xs input-bordered w-full max-w-xs"
          data-testid="list-search"
        />
      </div>

      <select
        value={typeFilter}
        onChange={(e) => onTypeFilterChange(e.target.value)}
        className="select select-xs select-bordered"
        data-testid="list-filter"
      >
        <option value="all">全部类型</option>
        <option value="plan-section">规划</option>
        <option value="character-section">角色</option>
        <option value="storyboard-section">分镜</option>
        <option value="compose-section">合成</option>
      </select>

      <select
        value={sortBy}
        onChange={(e) =>
          onSortChange(e.target.value as "name" | "type" | "position")
        }
        className="select select-xs select-bordered"
      >
        <option value="position">按位置</option>
        <option value="name">按名称</option>
        <option value="type">按类型</option>
      </select>

      {selectedCount > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-base-content/60">
            {selectedCount} / {totalCount} 选中
          </span>
          <button onClick={onDelete} className="btn btn-error btn-xs">
            删除
          </button>
        </div>
      )}

      <button onClick={onSelectAll} className="btn btn-ghost btn-xs">
        {selectedCount === totalCount ? "取消全选" : "全选"}
      </button>
    </div>
  );
}
