import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { styleTemplatesApi } from "~/services/api";
import { StyleTemplateCard } from "./StyleTemplateCard";
import type { StyleTemplate } from "~/types";

type CategoryFilter = "all" | "builtin" | "custom";

interface StyleTemplateGridProps {
  selectedSlug: string;
  onSelect: (slug: string) => void;
  onCreateNew?: () => void;
}

export function StyleTemplateGrid({
  selectedSlug,
  onSelect,
  onCreateNew,
}: StyleTemplateGridProps) {
  const [filter, setFilter] = useState<CategoryFilter>("all");

  const { data: templates = [], isLoading, error } = useQuery<StyleTemplate[]>({
    queryKey: ["style-templates", filter === "all" ? undefined : filter],
    queryFn: () =>
      styleTemplatesApi.list(
        filter === "all" ? undefined : { category: filter },
      ),
  });

  const tabs: { key: CategoryFilter; label: string }[] = [
    { key: "all", label: "全部" },
    { key: "builtin", label: "内置" },
    { key: "custom", label: "自定义" },
  ];

  if (error) {
    return (
      <div className="alert alert-error">
        <span>加载风格模板失败</span>
      </div>
    );
  }

  return (
    <div>
      {/* Category tabs */}
      <div className="tabs tabs-boxed mb-4 bg-base-300">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={`tab tab-sm ${filter === tab.key ? "tab-active" : ""}`}
            onClick={() => setFilter(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card bg-base-300 animate-pulse">
              <div className="h-24 bg-base-200" />
              <div className="card-body p-4">
                <div className="h-4 bg-base-200 rounded w-2/3" />
                <div className="h-3 bg-base-200 rounded w-full mt-2" />
              </div>
            </div>
          ))}
        </div>
      ) : templates.length === 0 ? (
        <div className="text-center py-8 text-base-content/60">
          {filter === "custom"
            ? "暂无自定义风格，点击下方按钮创建"
            : "暂无可用风格模板"}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {templates.map((t) => (
            <StyleTemplateCard
              key={t.slug}
              template={t}
              selected={t.slug === selectedSlug}
              onClick={onSelect}
            />
          ))}
        </div>
      )}

      {/* Create new button (visible in custom or all tab) */}
      {onCreateNew && (filter === "custom" || filter === "all") && (
        <div className="mt-4 text-center">
          <button
            type="button"
            className="btn btn-outline btn-sm"
            onClick={onCreateNew}
          >
            + 创建新风格
          </button>
        </div>
      )}
    </div>
  );
}
