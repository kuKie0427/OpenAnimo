import { clsx } from "clsx";

interface TrackItemProps {
  item: {
    id: number;
    title: string;
    thumbnail?: string;
    status: "draft" | "processing" | "completed" | "error";
  };
  selected: boolean;
  onClick: () => void;
}

export function TrackItem({ item, selected, onClick }: TrackItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "w-full flex items-center gap-3 px-3 py-2 rounded-md transition-all duration-200",
        selected
          ? "bg-primary/10 border border-primary/20 shadow-aperture"
          : "hover:bg-base-300 border border-transparent"
      )}
    >
      {item.thumbnail ? (
        <img
          src={item.thumbnail}
          alt={item.title}
          className="w-10 h-10 rounded object-cover flex-shrink-0"
        />
      ) : (
        <div className="w-10 h-10 rounded bg-base-300 flex-shrink-0" />
      )}

      <div className="flex-1 text-left min-w-0">
        <div className="text-sm truncate">{item.title}</div>
        <div className="text-xs text-base-content/50 font-mono">
          {item.status}
        </div>
      </div>

      {item.status === "processing" && (
        <span className="w-2 h-2 rounded-full bg-warning animate-pulse flex-shrink-0" />
      )}

      {item.status === "error" && (
        <span className="w-2 h-2 rounded-full bg-error flex-shrink-0" />
      )}
    </button>
  );
}
