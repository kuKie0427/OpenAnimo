import { DocumentIcon } from "@heroicons/react/24/outline";
import { type PropsWithChildren, type ReactNode } from "react";

interface SectionShellProps {
  sectionTitle: string;
  sectionKey: "plan" | "render" | "compose";
  statusLabel: string;
  placeholder: boolean;
  placeholderText?: string;
  placeholderIcon?: ReactNode;
  children: ReactNode;
}

export function SectionShell({
  sectionTitle,
  sectionKey,
  statusLabel,
  placeholder,
  placeholderText,
  placeholderIcon,
  children,
}: PropsWithChildren<SectionShellProps>) {
  const cardClass = sectionKey === "render" ? "card-feature" : "card-screen";
  return (
    <div className={`flex flex-col w-full ${cardClass}`}>
      <div className="flex items-center justify-between px-3 py-2 border-b-2 border-base-content/10 shrink-0 bg-base-200/60">
        <h2 className="text-sm font-heading font-bold m-0">{sectionTitle}</h2>
        <span className="badge badge-ghost badge-xs">{statusLabel}</span>
      </div>
      <div className="flex-1 p-3">
        {placeholder ? (
          <div
            className="flex flex-col items-center justify-center h-full gap-2 opacity-40"
            data-testid="section-placeholder"
          >
            {placeholderIcon ?? <DocumentIcon className="w-8 h-8" />}
            <span className="text-xs">{placeholderText ?? "等待生成..."}</span>
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
