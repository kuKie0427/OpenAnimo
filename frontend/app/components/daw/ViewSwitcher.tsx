import { clsx } from "clsx";
import {
  ArrowsPointingOutIcon,
  ClockIcon,
  ListBulletIcon,
} from "@heroicons/react/24/outline";

export type ViewMode = "canvas" | "timeline" | "list";

interface ViewSwitcherProps {
  currentView: ViewMode;
  onViewChange: (view: ViewMode) => void;
}

const views: Array<{
  key: ViewMode;
  icon: typeof ListBulletIcon;
  label: string;
}> = [
  { key: "canvas", icon: ArrowsPointingOutIcon, label: "画布" },
  { key: "timeline", icon: ClockIcon, label: "时间线" },
  { key: "list", icon: ListBulletIcon, label: "列表" },
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
            data-testid={`view-${view.key}`}
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
