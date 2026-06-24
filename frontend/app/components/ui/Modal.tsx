import { useEffect, useRef, type ReactNode } from "react";
import { Button } from "./Button";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  actions?: ReactNode;
}

export function Modal({ isOpen, onClose, title, children, actions }: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  // 焦点管理：保存并恢复焦点
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement as HTMLElement;
      // 聚焦到 modal 容器
      modalRef.current?.focus();
    } else {
      // 恢复焦点到触发元素
      previousActiveElement.current?.focus();
    }
  }, [isOpen]);

  // 键盘陷阱：限制 Tab 在 modal 内循环
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }

      if (e.key !== "Tab") return;

      const focusableElements = modalRef.current?.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );

      if (!focusableElements || focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (e.shiftKey) {
        // Shift + Tab: 如果在第一个元素，跳到最后一个
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab: 如果在最后一个元素，跳到第一个
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <dialog className="modal modal-open" aria-modal="true" role="dialog" aria-labelledby={title ? "modal-title" : undefined}>
      <div
        ref={modalRef}
        className="modal-box bg-base-200"
        tabIndex={-1}
      >
        {title && (
          <h3 id="modal-title" className="font-heading font-bold text-lg mb-4">
            {title}
          </h3>
        )}
        <div className="py-4">{children}</div>
        <div className="modal-action gap-2">
          {actions}
          <Button variant="ghost" onClick={onClose}>
            关闭
          </Button>
        </div>
      </div>
      <form method="dialog" className="modal-backdrop">
        <button type="button" onClick={onClose} aria-label="关闭对话框">关闭</button>
      </form>
    </dialog>
  );
}
