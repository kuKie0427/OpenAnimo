import { clsx } from "clsx";
import {
  ListBulletIcon,
  Squares2X2Icon,
  ArrowsPointingOutIcon,
} from "@heroicons/react/24/outline";

export type ViewMode = "list" | "detail" | "canvas";

interface ViewSwitcherProps {
  currentView: ViewMode;
  onViewChange: (view: ViewMode) => void;
}

const views: Array<{
  key: ViewMode;
  icon: typeof ListBulletIcon;
  label: string;
}> = [
  { key: "list", icon: ListBulletIcon, label: "列表" },
  { key: "detail", icon: Squares2X2Icon, label: "详情" },
  { key: "canvas", icon: ArrowsPointingOutIcon, label: "画布" },
];

export function ViewSwitcher({ currentView, onViewChange }: ViewSwitcherProps) {
  return (
    <div className="flex items-center gap-1 p-1 bg-base-200 rounded-lg">
      {views.map((view) => {
        const Icon = view.icon;
        const isSelected = currentView === view.key;

        return (
          <button
            key={view.key}
            type="button"
            onClick={() => onViewChange(view.key)}
            title={view.label}
            className={clsx(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-all duration-200",
              isSelected
                ? "bg-primary text-primary-content shadow-aperture"
                : "text-base-content/60 hover:text-base-content hover:bg-base-300"
            )}
          >
            <Icon className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{view.label}</span>
          </button>
        );
      })}
    </div>
  );
}

export type { ViewSwitcherProps };
