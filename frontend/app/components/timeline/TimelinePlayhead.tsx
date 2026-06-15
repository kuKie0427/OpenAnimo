interface TimelinePlayheadProps {
  currentTime: number;
  totalDuration: number;
}

export function TimelinePlayhead({ currentTime, totalDuration }: TimelinePlayheadProps) {
  const left = (currentTime / totalDuration) * 100;

  return (
    <div
      className="absolute top-0 bottom-0 w-0.5 bg-primary pointer-events-none z-10"
      style={{ left: `${left}%` }}
    >
      <div className="absolute -top-1 -left-1.5 w-3 h-3 bg-primary rounded-full" />
    </div>
  );
}
