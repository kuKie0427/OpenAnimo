interface MinimapShape {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  type: string;
}

interface CanvasMinimapProps {
  shapes: MinimapShape[];
  viewport: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  canvasBounds: {
    width: number;
    height: number;
  };
  onNavigate: (x: number, y: number) => void;
}

export function CanvasMinimap({
  shapes,
  viewport,
  canvasBounds,
  onNavigate,
}: CanvasMinimapProps) {
  const scale = 150 / Math.max(canvasBounds.width, canvasBounds.height, 1);

  return (
    <div className="absolute bottom-4 right-4 z-10 w-[150px] h-[100px] bg-base-100/90 backdrop-blur-sm rounded-lg shadow-aperture border border-base-content/10 overflow-hidden">
      {shapes.map((shape) => (
        <div
          key={shape.id}
          className={`absolute rounded-sm ${
            shape.type === "plan-section" ? "bg-primary/30" :
            shape.type === "character-section" ? "bg-accent/30" :
            shape.type === "storyboard-section" ? "bg-secondary/30" :
            "bg-base-content/20"
          }`}
          style={{
            left: shape.x * scale,
            top: shape.y * scale,
            width: Math.max(shape.width * scale, 4),
            height: Math.max(shape.height * scale, 4),
          }}
        />
      ))}
      <div
        className="absolute border-2 border-primary/50 bg-primary/10"
        style={{
          left: viewport.x * scale,
          top: viewport.y * scale,
          width: viewport.width * scale,
          height: viewport.height * scale,
        }}
      />
      <div
        className="absolute inset-0 cursor-pointer"
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const x = (e.clientX - rect.left) / scale;
          const y = (e.clientY - rect.top) / scale;
          onNavigate(x, y);
        }}
      />
    </div>
  );
}
