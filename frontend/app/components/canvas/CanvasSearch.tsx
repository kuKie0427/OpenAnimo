import { useState } from "react";
import {
  MagnifyingGlassIcon,
  ChevronUpIcon,
  ChevronDownIcon,
} from "@heroicons/react/24/outline";
type CanvasShapeType = "plan-section" | "character-section" | "storyboard-section" | "compose-section";

interface CanvasSearchProps {
  onSearch: (query: string) => void;
  onFilterType: (type: CanvasShapeType | "all") => void;
  resultCount: number;
  onNavigateResult: (direction: "next" | "prev") => void;
  currentIndex: number;
}

export function CanvasSearch({
  onSearch,
  onFilterType,
  resultCount,
  onNavigateResult,
  currentIndex,
}: CanvasSearchProps) {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<CanvasShapeType | "all">("all");

  const handleSearch = (value: string) => {
    setQuery(value);
    onSearch(value);
  };

  return (
    <div className="absolute top-4 right-4 z-10 flex items-center gap-2 px-3 py-2 bg-base-100/90 backdrop-blur-sm rounded-lg shadow-aperture border border-base-content/10">
      <MagnifyingGlassIcon className="w-4 h-4 text-base-content/40" />
      <input
        type="text"
        value={query}
        onChange={(e) => handleSearch(e.target.value)}
        placeholder="搜索..."
        className="w-32 text-xs bg-transparent outline-none placeholder:text-base-content/30"
      />
      <select
        value={typeFilter}
        onChange={(e) => {
          setTypeFilter(e.target.value as CanvasShapeType | "all");
          onFilterType(e.target.value as CanvasShapeType | "all");
        }}
        className="text-xs bg-transparent border-none outline-none cursor-pointer"
      >
        <option value="all">全部</option>
        <option value="plan-section">规划</option>
        <option value="character-section">角色</option>
        <option value="storyboard-section">分镜</option>
        <option value="compose-section">合成</option>
      </select>
      {resultCount > 0 && (
        <div className="flex items-center gap-1 text-xs text-base-content/60">
          <span>{currentIndex + 1}/{resultCount}</span>
          <button onClick={() => onNavigateResult("prev")} className="hover:text-primary">
            <ChevronUpIcon className="w-3 h-3" />
          </button>
          <button onClick={() => onNavigateResult("next")} className="hover:text-primary">
            <ChevronDownIcon className="w-3 h-3" />
          </button>
        </div>
      )}
    </div>
  );
}
