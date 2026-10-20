import type { ReactElement } from "react";
import type { ActivityItem } from "../activityLog";

export function IconGear() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.65 1.65 0 004.6 15a1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.6a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09A1.65 1.65 0 0015 4.6a1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z" />
    </svg>
  );
}

export function IconBack() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

export function IconChevron() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 18l6-6-6-6" />
    </svg>
  );
}

export function IconWarn() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 8v5M12 16h.01" />
      <path d="M10.3 3.9L2.5 17a2 2 0 001.7 3h15.6a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z" />
    </svg>
  );
}

function IconLamp() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2a5 5 0 015 5c0 3-2 3.5-2 6h-6c0-2.5-2-3-2-6a5 5 0 015-5z" />
    </svg>
  );
}

function IconPhone() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="5" y="2" width="14" height="20" rx="2" />
      <path d="M12 18h.01" />
    </svg>
  );
}

function IconCircle() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="9" />
    </svg>
  );
}

function IconAlert() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 8v5M12 16h.01" />
      <circle cx="12" cy="12" r="9" />
    </svg>
  );
}

function IconBattery() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2" y="7" width="18" height="10" rx="2" />
      <path d="M22 10v4" />
    </svg>
  );
}

function glyphFor(item: ActivityItem): ReactElement {
  if (item.kind === "review") return <IconAlert />;
  if (item.kind === "action") return <IconLamp />;
  if (item.kind === "look" && /phone|bottle/.test(item.title.toLowerCase())) return <IconPhone />;
  if (item.kind === "look") return <IconCircle />;
  if (/battery/.test(item.title.toLowerCase())) return <IconBattery />;
  return <IconCircle />;
}

function toneFor(item: ActivityItem): string {
  if (item.kind === "review") return "amber";
  if (item.kind === "action") return "harbor";
  return "";
}

export function ActivityRow({
  item,
  time,
  bleed = false,
}: {
  item: ActivityItem;
  time?: string;
  bleed?: boolean;
}) {
  const needs = bleed && item.alert;
  return (
    <div className={needs ? "row needs" : "row"}>
      <div className={`row-icon ${toneFor(item)}`}>{glyphFor(item)}</div>
      <div className="row-body">
        <div className="row-title">{item.title}</div>
        {item.subtitle ? <div className="row-sub">{item.subtitle}</div> : null}
      </div>
      {time ? <div className="row-time">{time}</div> : null}
    </div>
  );
}
