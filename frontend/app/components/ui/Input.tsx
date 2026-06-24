import { clsx } from "clsx";
import type { InputHTMLAttributes } from "react";
import { useId } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, className, ...props }: InputProps) {
  const id = useId();

  return (
    <div className="form-control w-full">
      {label && (
        <label htmlFor={id} className="label">
          <span className="label-text font-heading font-medium">{label}</span>
        </label>
      )}
      <input
        id={id}
        className={clsx(
          "input-field w-full px-4 py-3 text-base",
          error && "border-error",
          className
        )}
        {...props}
      />
      {error && (
        <label className="label">
          <span className="label-text-alt text-error">{error}</span>
        </label>
      )}
    </div>
  );
}
