import { useState, useCallback } from "react";
import { ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/24/outline";
import { clsx } from "clsx";

interface CollapsibleMessageProps {
  summary: string;
  children: React.ReactNode;
  defaultExpanded?: boolean;
  className?: string;
}

export function CollapsibleMessage({
  summary,
  children,
  defaultExpanded = false,
  className,
}: CollapsibleMessageProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const toggle = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  return (
    <div className={clsx("collapsible-message", className)}>
      {isExpanded ? (
        <div>
          {children}
          <button
            onClick={toggle}
            className="mt-2 flex items-center gap-1 text-xs text-base-content/60 hover:text-base-content/80 transition-colors"
            aria-label="收起详情"
          >
            <ChevronUpIcon className="w-3 h-3" aria-hidden="true" />
            <span>收起</span>
          </button>
        </div>
      ) : (
        <div
          onClick={toggle}
          className="cursor-pointer hover:bg-base-200/50 rounded-lg p-2 -m-2 transition-colors"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              toggle();
            }
          }}
          aria-label="展开查看详情"
        >
          <p className="text-sm text-base-content/80">{summary}</p>
          <div className="flex items-center gap-1 mt-1 text-xs text-base-content/50">
            <ChevronDownIcon className="w-3 h-3" aria-hidden="true" />
            <span>点击展开</span>
          </div>
        </div>
      )}
    </div>
  );
}
