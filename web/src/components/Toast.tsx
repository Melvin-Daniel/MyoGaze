import type { ReactElement } from "react";
import type { ToastMessage } from "../types";
import { CheckIcon, AlertIcon, InfoIcon, CloseIcon } from "../icons";

interface ToastStackProps {
  toasts: ToastMessage[];
  onDismiss?: (id: string) => void;
}

const ICONS: Record<ToastMessage["tone"], (p: { size?: number }) => ReactElement> = {
  neutral: InfoIcon,
  act: CheckIcon,
  abstain: AlertIcon,
};

const TONE_STYLE: Record<ToastMessage["tone"], string> = {
  neutral: "info",
  act: "success",
  abstain: "warning",
};

export function ToastStack({ toasts, onDismiss }: ToastStackProps) {
  if (toasts.length === 0) return null;

  return (
    <div className="toast-stack" role="status" aria-live="polite">
      {toasts.map((toast) => {
        const Icon = ICONS[toast.tone] ?? InfoIcon;
        return (
          <div className="toast" data-tone={TONE_STYLE[toast.tone]} key={toast.id}>
            <span className="toast__icon">
              <Icon size={16} />
            </span>
            <span>{toast.text}</span>
            {onDismiss && (
              <button
                type="button"
                className="toast__close"
                aria-label="Dismiss notification"
                onClick={() => onDismiss(toast.id)}
              >
                <CloseIcon size={13} />
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
