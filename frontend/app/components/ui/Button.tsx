import { clsx } from "clsx";
import { type ButtonHTMLAttributes, type ReactNode } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "accent" | "ghost" | "error";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  children: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  className,
  children,
  disabled,
  onClick,
  type = "button",
  ...props
}: ButtonProps) {
  const baseStyles = "btn-projection font-heading cursor-pointer inline-flex items-center justify-center gap-2 no-underline";

  const variantStyles = {
    primary: "bg-primary text-primary-content hover:shadow-projection",
    secondary: "bg-secondary text-secondary-content hover:shadow-signal",
    accent: "bg-accent text-accent-content hover:shadow-beam",
    ghost: "!bg-transparent border-transparent shadow-none hover:!bg-base-200 hover:shadow-aperture",
    error: "bg-error text-error-content hover:shadow-signal",
  };

  const sizeStyles = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-5 py-2.5 text-base",
    lg: "px-7 py-3 text-lg",
  };

  const handleClick = async (e: React.MouseEvent<HTMLButtonElement>) => {
    if (loading || disabled) return;
    await onClick?.(e);
  };

  const isDisabled = disabled || loading;

  return (
    <button
      className={clsx(
        baseStyles,
        variantStyles[variant],
        sizeStyles[size],
        "touch-target", // 确保触摸目标尺寸
        isDisabled && "opacity-50 cursor-not-allowed",
        className
      )}
      disabled={isDisabled}
      onClick={handleClick}
      type={type}
      {...props}
    >
      {loading ? (
        <span className="w-5 h-5 rounded-full border-2 border-base-content/15 border-t-primary animate-spin" />
      ) : (
        children
      )}
    </button>
  );
}
