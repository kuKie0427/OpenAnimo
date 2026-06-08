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
    primary: "!bg-[#F5A623] !text-[#1A1A12] hover:brightness-110",
    secondary: "!bg-[#CC3333] !text-white hover:brightness-110",
    accent: "!bg-[#4A90D9] !text-white hover:brightness-110",
    ghost: "!bg-transparent border-transparent shadow-none hover:!bg-base-200 hover:shadow-aperture",
    error: "!bg-[#D94848] !text-white hover:brightness-110",
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
        loading && "loading",
        isDisabled && "opacity-50 cursor-not-allowed",
        className
      )}
      disabled={isDisabled}
      onClick={handleClick}
      type={type}
      {...props}
    >
      {loading ? <span className="loading loading-spinner loading-sm" /> : children}
    </button>
  );
}
