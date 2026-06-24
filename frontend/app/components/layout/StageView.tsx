import { lazy, Suspense } from "react";

interface StageViewProps {
  projectId: number;
}

const InfiniteCanvas = lazy(() =>
  import("~/components/canvas/InfiniteCanvas").then((m) => ({
    default: m.InfiniteCanvas,
  })),
);

export function StageView({ projectId }: StageViewProps) {
  return (
    <Suspense
      fallback={
        <div className="flex h-full w-full items-center justify-center bg-base-100 text-sm text-base-content/60">
          正在加载画布...
        </div>
      }
    >
      <InfiniteCanvas projectId={projectId} />
    </Suspense>
  );
}
