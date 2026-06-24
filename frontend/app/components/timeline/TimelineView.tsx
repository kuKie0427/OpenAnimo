import { useState, useMemo } from "react";
import { TimelineTrack } from "./TimelineTrack";
import { TimelineControls } from "./TimelineControls";

interface TimelineViewProps {
  projectId: number;
  shapes: Array<{
    id: string;
    type: string;
    x: number;
    y: number;
    content: any;
  }>;
  onShapeSelect: (id: string) => void;
  onTimeChange: (time: number) => void;
}

export function TimelineView({ projectId: _projectId, shapes, onShapeSelect, onTimeChange }: TimelineViewProps) {
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const tracks = useMemo(() => {
    const storyboardShapes = shapes.filter(s => s.type === 'storyboard-section');
    const characterShapes = shapes.filter(s => s.type === 'character-section');
    const tracks = [];

    if (storyboardShapes.length > 0) {
      tracks.push({
        id: 'storyboards',
        label: '分镜',
        items: storyboardShapes.map((s, i) => ({
          id: s.id,
          label: `分镜 ${i + 1}`,
          startTime: i * 5,
          duration: 5,
          thumbnail: s.content?.imageUrl,
        })),
      });
    }

    if (characterShapes.length > 0) {
      tracks.push({
        id: 'characters',
        label: '角色',
        items: characterShapes.map((s, i) => ({
          id: s.id,
          label: s.content?.name || `角色 ${i + 1}`,
          startTime: i * 3,
          duration: 8,
          thumbnail: s.content?.avatarUrl,
        })),
      });
    }

    return tracks;
  }, [shapes]);

  return (
    <div className="flex-1 flex flex-col bg-base-100">
      <div className="flex-1 overflow-auto p-4">
        {tracks.map((track) => (
          <TimelineTrack
            key={track.id}
            track={track}
            currentTime={currentTime}
            onItemSelect={onShapeSelect}
          />
        ))}
      </div>

      <TimelineControls
        currentTime={currentTime}
        isPlaying={isPlaying}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onTimeChange={(time) => {
          setCurrentTime(time);
          onTimeChange(time);
        }}
      />
    </div>
  );
}
