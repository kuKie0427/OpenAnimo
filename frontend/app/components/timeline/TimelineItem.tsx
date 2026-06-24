interface TimelineItemProps {
  item: {
    id: string;
    label: string;
    startTime: number;
    duration: number;
    thumbnail?: string;
  };
  totalDuration: number;
  isActive: boolean;
  onClick: () => void;
}

export function TimelineItem({ item, totalDuration, isActive, onClick }: TimelineItemProps) {
  const left = (item.startTime / totalDuration) * 100;
  const width = (item.duration / totalDuration) * 100;

  return (
    <button
      onClick={onClick}
      className={`absolute top-1 bottom-1 rounded transition-all duration-200 ${
        isActive
          ? 'bg-primary/20 border border-primary/40 shadow-aperture'
          : 'bg-base-300 border border-base-content/10 hover:border-primary/30'
      }`}
      style={{ left: `${left}%`, width: `${width}%` }}
    >
      {item.thumbnail && (
        <img
          src={item.thumbnail}
          alt={item.label}
          className="w-full h-full object-cover rounded"
        />
      )}
      <span className="absolute bottom-1 left-1 text-[10px] text-base-content/60 truncate max-w-[90%]">
        {item.label}
      </span>
    </button>
  );
}
