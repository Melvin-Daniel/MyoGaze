import type { ReactNode } from "react";
import { IconBack } from "../RdIcons";

export function SettingsHeader({ title, onBack }: { title: string; onBack?: () => void }) {
  return (
    <div className="topbar">
      {onBack ? (
        <button type="button" className="iconbtn" aria-label="Back" onClick={onBack}>
          <IconBack />
        </button>
      ) : (
        <span className="iconbtn" aria-hidden />
      )}
      <h1 className="title">{title}</h1>
      <span className="iconbtn" aria-hidden />
    </div>
  );
}

export function SettingsSection({ label, children }: { label?: string; children: ReactNode }) {
  return (
    <div className="st-section">
      {label ? <p className="grouplabel">{label}</p> : null}
      <div className="st-card">{children}</div>
    </div>
  );
}

export function SettingsRow({
  label,
  hint,
  onClick,
  trailing,
}: {
  label: string;
  hint?: string;
  onClick?: () => void;
  trailing?: ReactNode;
}) {
  if (onClick) {
    return (
      <button type="button" className="st-row" onClick={onClick}>
        <span className="st-row-copy">
          <strong>{label}</strong>
          {hint ? <span>{hint}</span> : null}
        </span>
        {trailing ?? <span className="chev">›</span>}
      </button>
    );
  }
  return (
    <div className="st-row static">
      <span className="st-row-copy">
        <strong>{label}</strong>
        {hint ? <span>{hint}</span> : null}
      </span>
      {trailing}
    </div>
  );
}

export function SoonRow({ label, hint }: { label: string; hint?: string }) {
  return (
    <div className="st-row static">
      <span className="st-row-copy">
        <strong>{label}</strong>
        {hint ? <span>{hint}</span> : null}
      </span>
      <span className="soon-badge">Coming soon</span>
    </div>
  );
}

export function SettingsToggle({
  label,
  hint,
  checked,
  onChange,
  disabled,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <div className="st-row static">
      <span className="st-row-copy">
        <strong>{label}</strong>
        {hint ? <span>{hint}</span> : null}
      </span>
      <button
        type="button"
        className="switch"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
      />
    </div>
  );
}

export function SettingsSelect<T extends string | number>({
  label,
  hint,
  value,
  options,
  onChange,
}: {
  label: string;
  hint?: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <label className="st-select">
      <span className="st-row-copy">
        <strong>{label}</strong>
        {hint ? <span>{hint}</span> : null}
      </span>
      <select value={String(value)} onChange={(e) => onChange((Number.isNaN(Number(e.target.value)) ? e.target.value : Number(e.target.value)) as T)}>
        {options.map((option) => (
          <option key={String(option.value)} value={String(option.value)}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function StatusBadge({
  tone,
  children,
}: {
  tone: "ok" | "warn" | "off" | "busy";
  children: ReactNode;
}) {
  return <span className={`st-badge ${tone}`}>{children}</span>;
}

export function ConfirmModal({
  title,
  body,
  confirmLabel,
  danger,
  onConfirm,
  onCancel,
}: {
  title: string;
  body: string;
  confirmLabel: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="st-modal" role="dialog" aria-modal="true" aria-labelledby="st-modal-title">
      <div className="st-modal-card">
        <h2 id="st-modal-title">{title}</h2>
        <p>{body}</p>
        <div className="btnrow">
          <button type="button" className="btn" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className={danger ? "btn warn" : "btn primary"} onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

export function ProfileCard({
  name,
  identifier,
  laptop,
  camera,
  lamp,
}: {
  name: string;
  identifier: string;
  laptop: string;
  camera: string;
  lamp: string;
}) {
  const initial = (name.trim()[0] || "I").toUpperCase();
  return (
    <div className="st-profile">
      <div className="avatar">{initial}</div>
      <div className="st-profile-copy">
        <strong>{name}</strong>
        <span>{identifier}</span>
        <div className="st-profile-meta">
          <span>{laptop}</span>
          <span>{camera}</span>
          <span>{lamp}</span>
        </div>
      </div>
    </div>
  );
}
