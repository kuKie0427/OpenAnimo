import { TimelineItem } from "./TimelineItem";
import { TimelinePlayhead } from "./TimelinePlayhead";

interface TimelineTrackProps {
  track: {
    id: string;
    label: string;
    items: Array<{
      id: string;
      label: string;
      startTime: number;
      duration: number;
      thumbnail?: string;
    }>;
  };
  currentTime: number;
  onItemSelect: (id: string) => void;
}

export function TimelineTrack({ track, currentTime, onItemSelect }: TimelineTrackProps) {
  const totalDuration = Math.max(...track.items.map(i => i.startTime + i.duration), 1);

  return (
    <div className="flex items-start gap-4 mb-4">
      <div className="w-24 flex-shrink-0 text-xs font-mono text-base-content/60 pt-2">
        {track.label}
      </div>

      <div className="flex-1 relative h-16 bg-base-200 rounded-lg overflow-hidden">
        {track.items.map((item) => (
          <TimelineItem
            key={item.id}
            item={item}
            totalDuration={totalDuration}
            isActive={currentTime >= item.startTime && currentTime < item.startTime + item.duration}
            onClick={() => onItemSelect(item.id)}
          />
        ))}

        <TimelinePlayhead
          currentTime={currentTime}
          totalDuration={totalDuration}
        />
      </div>
    </div>
  );
}
