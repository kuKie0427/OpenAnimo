import { ExclamationTriangleIcon } from "@heroicons/react/24/outline";

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "warning" | "info";
  isLoading?: boolean;
}

export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title = "确认操作",
  message,
  confirmText = "确认",
  cancelText = "取消",
  variant = "danger",
  isLoading = false,
}: ConfirmModalProps) {
  if (!isOpen) return null;

  const variantStyles = {
    danger: {
      icon: "text-error",
      iconBg: "bg-error/10",
      button: "btn-error",
    },
    warning: {
      icon: "text-warning",
      iconBg: "bg-warning/10",
      button: "btn-warning",
    },
    info: {
      icon: "text-info",
      iconBg: "bg-info/10",
      button: "btn-info",
    },
  };

  const styles = variantStyles[variant];

  return (
    <dialog className="modal" open aria-modal="true" aria-labelledby="confirm-modal-title">
      <div className="modal-box bg-base-100 border border-base-content/30 shadow-aperture">
        <div className="flex items-start gap-4">
          {/* 图标 */}
          <div className={`p-3 rounded-full ${styles.iconBg}`}>
            <ExclamationTriangleIcon className={`w-6 h-6 ${styles.icon}`} />
          </div>

          {/* 内容 */}
          <div className="flex-1">
            <h3 id="confirm-modal-title" className="font-heading font-bold text-lg">{title}</h3>
            <p className="text-base-content/70 mt-2">{message}</p>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="modal-action">
          <button
            className="btn btn-ghost border border-base-content/30 cursor-pointer"
            onClick={onClose}
            disabled={isLoading}
          >
            {cancelText}
          </button>
          <button
            className={`btn ${styles.button} border border-base-content/30 cursor-pointer`}
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading && <span className="loading loading-spinner loading-sm"></span>}
            {confirmText}
          </button>
        </div>
      </div>

      {/* 背景遮罩 */}
      <form method="dialog" className="modal-backdrop bg-neutral/50">
        <button type="button" onClick={onClose} disabled={isLoading}>
          close
        </button>
      </form>
    </dialog>
  );
}
