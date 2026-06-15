import { useState } from "react";
import type { ComponentType, SVGProps } from "react";

type ActionVariant = "primary" | "secondary" | "accent" | "ghost" | "error";

// 支持 heroicons 风格的图标组件
type IconComponent = ComponentType<SVGProps<SVGSVGElement> & { className?: string }>;

export interface ActionItem {
  icon: IconComponent;
  label: string;
  onClick: () => void;
  variant?: ActionVariant;
  loading?: boolean;
}

interface HoverActionBarProps {
  actions: ActionItem[];
  children: React.ReactNode;
  className?: string;
}

export function HoverActionBar({
  actions,
  children,
  className,
}: HoverActionBarProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      className={`relative ${className || ""}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {children}
      <div
        className={`absolute top-2 right-2 z-10 flex items-center gap-1 rounded-lg bg-base-100/90 p-1 transition-all duration-200 ${
          isHovered
            ? "opacity-100"
            : "opacity-0 pointer-events-none"
        }`}
      >
        {actions.map((action, index) => {
          const btnColor =
            action.variant === "error"
              ? "btn-error"
              : `btn-${action.variant || "ghost"}`;

          const Icon = action.icon;

          return (
            <div key={index} className="tooltip" data-tip={action.label}>
              <button
                className={`btn btn-xs btn-circle ${btnColor} ${
                  action.loading ? "loading" : ""
                }`}
                onClick={(e) => {
                  e.stopPropagation();
                  e.preventDefault();
                  action.onClick();
                }}
                disabled={action.loading}
                aria-label={action.label}
              >
                {!action.loading && <Icon className="w-4 h-4" />}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
