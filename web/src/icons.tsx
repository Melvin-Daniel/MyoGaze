// NeuroShift — icon set
// Hand-drawn-minimal line icons. Stroke-based, currentColor, 1.6px weight.
// No emoji anywhere in the product per design brief.

import type { SVGProps } from "react";

const base = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function IconGaze(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <path d="M2 12c2.6-4.2 6-6.3 10-6.3S19.4 7.8 22 12c-2.6 4.2-6 6.3-10 6.3S4.6 16.2 2 12Z" />
      <circle cx="12" cy="12" r="2.6" />
    </svg>
  );
}

export function IconMuscle(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <path d="M4 20c0-4 1-7 1-10 0-3 2-5 4.5-5 1.7 0 2.9 1 3.5 2.2" />
      <path d="M9.5 5c1.6-1.3 4-1.6 6 .2 2.3 2 2.3 5 1 7.3-1 1.8-1 3.3-1 5.5" />
      <path d="M4 20h11.5" />
      <path d="M12 11.5c1.6.3 3 .1 4-1" />
    </svg>
  );
}

export function IconShieldCheck(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <path d="M12 3l7 3v5.5c0 4.6-3 8.3-7 9.5-4-1.2-7-4.9-7-9.5V6l7-3Z" />
      <path d="M9 12.2l2.1 2.1L15.5 10" />
    </svg>
  );
}

export function IconShieldPause(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <path d="M12 3l7 3v5.5c0 4.6-3 8.3-7 9.5-4-1.2-7-4.9-7-9.5V6l7-3Z" />
      <path d="M10 9.5v5M14 9.5v5" />
    </svg>
  );
}

export function IconHome(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <path d="M4 11.5 12 4l8 7.5" />
      <path d="M6 10v9.5h12V10" />
      <path d="M10 19.5v-6h4v6" />
    </svg>
  );
}

export function IconMonitor(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <rect x="3" y="5.5" width="18" height="12" rx="2" />
      <path d="M8 21h8M12 17.5V21" />
      <circle cx="12" cy="11.5" r="2.4" />
    </svg>
  );
}

export function IconActivity(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <path d="M3 12h4l2.2-6.5L13 18l2-8.5 1.6 2.5H21" />
    </svg>
  );
}

export function IconInsights(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <path d="M4 20V10M11 20V4M18 20v-7" />
      <path d="M2 20h20" />
    </svg>
  );
}

export function IconSystem(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2.2M12 18.8V21M4.9 4.9l1.5 1.5M17.6 17.6l1.5 1.5M3 12h2.2M18.8 12H21M4.9 19.1l1.5-1.5M17.6 6.4l1.5-1.5" />
    </svg>
  );
}

export function IconLamp(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <path d="M7 4h10l-2.5 6.5H9.5L7 4Z" />
      <path d="M12 10.5V17" />
      <path d="M8 21h8" />
      <path d="M9.5 17h5l1.2 3.2c.2.5-.2.8-.6.8H8.9c-.4 0-.8-.3-.6-.8L9.5 17Z" />
    </svg>
  );
}

export function IconFan(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <circle cx="12" cy="12" r="1.6" />
      <path d="M12 10.4c-.6-2.6-.4-6 1.8-7.4 1.8-1.1 3.6.2 3.2 2.2-.4 2.1-2.6 4.1-5 5.2Z" />
      <path d="M13.6 12c2.6-.6 6-.4 7.4 1.8 1.1 1.8-.2 3.6-2.2 3.2-2.1-.4-4.1-2.6-5.2-5Z" />
      <path d="M12 13.6c.6 2.6.4 6-1.8 7.4-1.8 1.1-3.6-.2-3.2-2.2.4-2.1 2.6-4.1 5-5.2Z" />
    </svg>
  );
}

export function IconPlug(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <path d="M9 3v5M15 3v5" />
      <path d="M7 8h10v3.5a5 5 0 0 1-10 0V8Z" />
      <path d="M12 15.5V19" />
      <path d="M9 19h6" />
    </svg>
  );
}

export function IconWifi(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <path d="M3.5 8.5a13 13 0 0 1 17 0" />
      <path d="M6.5 12.2a9 9 0 0 1 11 0" />
      <path d="M9.5 15.8a5 5 0 0 1 5 0" />
      <circle cx="12" cy="19" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconWifiOff(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <path d="M3.5 8.5a13 13 0 0 1 9-3.5M13.9 5.4A13 13 0 0 1 20.5 8.5" />
      <path d="M6.5 12.2a9 9 0 0 1 6.5-2.6M15.1 10a9 9 0 0 1 2.4 2.2" />
      <path d="M9.5 15.8a5 5 0 0 1 5 0" />
      <circle cx="12" cy="19" r="1" fill="currentColor" stroke="none" />
      <path d="M2 2l20 20" />
    </svg>
  );
}

export function IconPlay(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <path d="M6.5 4.5v15l14-7.5-14-7.5Z" strokeLinejoin="round" />
    </svg>
  );
}

export function IconRefresh(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <path d="M3.5 12a8.5 8.5 0 0 1 14.7-5.8M20.5 12a8.5 8.5 0 0 1-14.7 5.8" />
      <path d="M18 3.8V7h-3.2M6 20.2V17h3.2" />
    </svg>
  );
}

export function IconChevronRight(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...base} {...props}>
      <path d="M9 5.5 15.5 12 9 18.5" />
    </svg>
  );
}
