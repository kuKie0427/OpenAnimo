interface LoadingOverlayProps {
  text?: string;
  className?: string;
}

export function LoadingOverlay({ text, className }: LoadingOverlayProps) {
  return (
    <div
      className={`absolute inset-0 z-20 flex flex-col items-center justify-center bg-base-100/80 ${
        className || ""
      }`}
    >
      <span className="loading loading-spinner loading-lg text-primary"></span>
      {text && <p className="mt-4 text-lg font-bold">{text}</p>}
    </div>
  );
}
