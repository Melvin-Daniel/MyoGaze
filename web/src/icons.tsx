import type { SVGProps } from "react";

interface IconProps extends SVGProps<SVGSVGElement> {
  size?: number;
}

function base(size = 18) {
  return {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.75,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
}

/** Open C = gaze. QRS spike = muscle confirm. Empty core = abstain until both agree. */
export function MyoGazeMark({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={2.2} {...p}>
      <path d="M16.53 17.40 A7.05 7.05 0 1 1 16.53 6.60" />
      <path
        d="M18.90 8.10 L18.90 9.65 L17.05 10.75 L22.45 12.00 L17.05 13.25 L18.90 14.35 L18.90 15.90"
        strokeLinejoin="miter"
      />
    </svg>
  );
}

export function HomeIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M3 11.5 12 4l9 7.5" />
      <path d="M5.5 10v9a1 1 0 0 0 1 1H10v-5.5h4V20h3.5a1 1 0 0 0 1-1v-9" />
    </svg>
  );
}

export function MonitorIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <rect x="3" y="4.5" width="18" height="12" rx="1.5" />
      <path d="M8.5 20.5h7M12 16.5v4" />
      <circle cx="12" cy="10.5" r="2.5" />
    </svg>
  );
}

export function ActivityIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M3 12h4l2.2-6.5L13 18l2-9 1.4 3H21" />
    </svg>
  );
}

export function InsightsIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M4 20V10M11 20V4M18 20v-7" />
      <path d="M3 20.5h18" />
    </svg>
  );
}

export function SystemIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 13a7.7 7.7 0 0 0 0-2l2-1.4-2-3.4-2.3.6a7.6 7.6 0 0 0-1.7-1L15 3h-6l-.4 2.3a7.6 7.6 0 0 0-1.7 1l-2.3-.6-2 3.4L4.6 11a7.7 7.7 0 0 0 0 2l-2 1.4 2 3.4 2.3-.6a7.6 7.6 0 0 0 1.7 1L9 21h6l.4-2.3a7.6 7.6 0 0 0 1.7-1l2.3.6 2-3.4z" />
    </svg>
  );
}

export function LampIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={2} {...p}>
      <path d="M9 18h6" />
      <path d="M10 21h4" />
      <path d="M8.2 10.2a3.8 3.8 0 1 1 7.6 0c0 2.1-1.2 3.2-2.2 4.2H10.4c-1-1-2.2-2.1-2.2-4.2z" />
    </svg>
  );
}

export function FanIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <circle cx="12" cy="12" r="1.6" />
      <path d="M12 10.4C11 7 11.6 3.5 14 3c2 0 3 1.7 2.2 3.4-.7 1.5-2.5 2.4-4.2 3z" />
      <path d="M13.6 12c3.4-1 6.9-.4 7.4 2 0 2-1.7 3-3.4 2.2-1.5-.7-2.4-2.5-3-4.2z" />
      <path d="M12 13.6c1 3.4.4 6.9-2 7.4-2 0-3-1.7-2.2-3.4.7-1.5 2.5-2.4 4.2-3z" />
      <path d="M10.4 12c-3.4 1-6.9.4-7.4-2 0-2 1.7-3 3.4-2.2 1.5.7 2.4 2.5 3 4.2z" />
    </svg>
  );
}

export function PlugIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M9 3v5M15 3v5" />
      <path d="M6.5 8h11v3.5a5.5 5.5 0 0 1-11 0z" />
      <path d="M12 15v6" />
    </svg>
  );
}

export function CheckIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M4.5 12.5 9 17l10.5-11" />
    </svg>
  );
}

export function AlertIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M12 3.5 21.5 20h-19z" />
      <path d="M12 10v4.2" />
      <circle cx="12" cy="17.3" r="0.15" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function InfoIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5.5" />
      <circle cx="12" cy="8" r="0.15" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function CloseIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M5 5l14 14M19 5 5 19" />
    </svg>
  );
}

export function EyeIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
      <circle cx="12" cy="12" r="2.6" />
    </svg>
  );
}

export function MuscleIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M4 14c0-4 2-9 5.5-9 1.7 0 2 1.3 3.5 1.3S15 4.2 16.8 4.9C19.3 5.9 20 9 20 12c0 4.5-3 8-8 8s-8-3.5-8-6Z" />
      <path d="M9 11.5c1 .8 2 .8 3 0" />
    </svg>
  );
}

export function DownloadIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M12 4v11.5M8 12l4 4 4-4" />
      <path d="M4.5 18.5v1a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-1" />
    </svg>
  );
}

export function RefreshIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M20 11a8 8 0 1 0-2.3 5.7" />
      <path d="M20 5.5V11h-5.5" />
    </svg>
  );
}

export function CameraIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M3 8.5A1.5 1.5 0 0 1 4.5 7h2l1-2h9l1 2h2A1.5 1.5 0 0 1 21 8.5v9A1.5 1.5 0 0 1 19.5 19h-15A1.5 1.5 0 0 1 3 17.5z" />
      <circle cx="12" cy="12.5" r="3.5" />
    </svg>
  );
}

export function UserIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <circle cx="12" cy="8" r="3.2" />
      <path d="M5 19.2c1.2-3 3.6-4.5 7-4.5s5.8 1.5 7 4.5" />
    </svg>
  );
}

export function ChevronIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M9 5l7 7-7 7" />
    </svg>
  );
}

export function MicIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M6 11a6 6 0 0 0 12 0M12 17v3.5" />
    </svg>
  );
}

export function ResetIcon({ size, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M4 4v6h6" />
      <path d="M4.5 13.5A8 8 0 1 0 6.3 6.3L4 10" />
    </svg>
  );
}
