import { clsx } from "clsx";
import type { CSSProperties, ReactNode } from "react";

interface CardProps {
  title?: ReactNode;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  variant?: "default" | "primary" | "secondary" | "accent";
}

export function Card({ title, children, className, style, variant = "default" }: CardProps) {
  const variantStyles = {
    default: "bg-base-100",
    primary: "bg-primary/10 border-primary",
    secondary: "bg-secondary/10 border-secondary",
    accent: "bg-accent/10 border-accent",
  };

  return (
    <div className={clsx("card-screen p-6", variantStyles[variant], className)} style={style}>
      {title && (
        <h3 className="text-xl font-heading font-bold mb-4 flex items-center gap-2">
          {title}
        </h3>
      )}
      {children}
    </div>
  );
}
