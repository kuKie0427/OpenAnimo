import { PlayIcon, PauseIcon } from "@heroicons/react/24/outline";

interface TimelineControlsProps {
  currentTime: number;
  isPlaying: boolean;
  onPlay: () => void;
  onPause: () => void;
  onTimeChange: (time: number) => void;
}

export function TimelineControls({ currentTime, isPlaying, onPlay, onPause, onTimeChange }: TimelineControlsProps) {
  return (
    <div className="flex items-center gap-4 px-4 py-3 bg-base-200 border-t border-base-content/10">
      <button
        onClick={isPlaying ? onPause : onPlay}
        className="btn btn-ghost btn-sm btn-circle"
        aria-label={isPlaying ? "暂停" : "播放"}
        data-testid={isPlaying ? "timeline-pause" : "timeline-play"}
      >
        {isPlaying ? (
          <PauseIcon className="w-4 h-4" />
        ) : (
          <PlayIcon className="w-4 h-4" />
        )}
      </button>

      <span className="text-xs font-mono text-base-content/60 w-16 tabular-nums">
        {formatTime(currentTime)}
      </span>

      <input
        type="range"
        min={0}
        max={100}
        value={currentTime}
        onChange={(e) => onTimeChange(Number(e.target.value))}
        className="range range-primary range-xs flex-1"
      />
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
