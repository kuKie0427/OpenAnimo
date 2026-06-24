import { clsx } from "clsx";
import type { StyleTemplate } from "~/types";

interface StyleTemplateCardProps {
  template: StyleTemplate;
  selected: boolean;
  onClick: (slug: string) => void;
}

/** CSS gradient backgrounds per builtin slug — no external images needed. */
const SLUG_GRADIENTS: Record<string, string> = {
  anime: "from-pink-500 to-purple-600",
  shonen: "from-red-600 to-orange-500",
  "slice-of-life": "from-amber-300 to-pink-300",
  manga: "from-gray-700 to-gray-900",
  donghua: "from-teal-500 to-indigo-600",
  "guofeng-manga": "from-rose-700 to-amber-600",
  cinematic: "from-slate-700 to-slate-500",
  pixar: "from-blue-400 to-cyan-300",
  cyberpunk: "from-violet-700 to-cyan-500",
  lowpoly: "from-emerald-500 to-lime-400",
  watercolor: "from-rose-300 to-sky-200",
  "fairy-tale": "from-yellow-300 to-pink-300",
  sketch: "from-stone-400 to-stone-600",
  realistic: "from-zinc-500 to-zinc-700",
};

const DEFAULT_GRADIENT = "from-primary to-secondary";

export function StyleTemplateCard({ template, selected, onClick }: StyleTemplateCardProps) {
  const gradient = SLUG_GRADIENTS[template.slug] ?? DEFAULT_GRADIENT;

  return (
    <button
      type="button"
      className={clsx(
        "card bg-base-300 overflow-hidden transition-all hover:scale-105 text-left",
        selected && "ring-2 ring-primary",
      )}
      onClick={() => onClick(template.slug)}
    >
      {/* Preview gradient header */}
      <div
        className={clsx("h-24 bg-gradient-to-br", gradient)}
        aria-hidden="true"
      />
      <div className="card-body p-4">
        <div className="flex items-center gap-2">
          <h4 className="font-heading font-bold text-sm">{template.name}</h4>
          {template.category === "custom" && (
            <span className="badge badge-xs badge-accent">自定义</span>
          )}
        </div>
        {template.description && (
          <p className="text-xs text-base-content/60 mt-1 line-clamp-2">
            {template.description}
          </p>
        )}
        {template.color_palette.length > 0 && (
          <div className="flex gap-1 mt-2 flex-wrap">
            {template.color_palette.slice(0, 4).map((tag) => (
              <span key={tag} className="badge badge-xs badge-outline">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </button>
  );
}
