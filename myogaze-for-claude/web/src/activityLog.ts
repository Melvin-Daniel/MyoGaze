import type { ActivityEntry } from "./types";

export type ActivityKind = "review" | "action" | "look" | "device";
export type ActivityChip = "all" | "review" | "actions" | "device";

export interface ActivityItem {
  id: string;
  timestamp: number;
  kind: ActivityKind;
  title: string;
  subtitle: string;
  alert: boolean;
}

function objectName(label: string): string {
  const raw = label.trim();
  if (!raw) return "device";
  return raw.charAt(0).toLowerCase() + raw.slice(1);
}

export function describeActivity(entry: ActivityEntry, who = "they"): ActivityItem {
  const d = entry.decision;
  const label = d.selected_label?.trim() || null;
  const reason = (d.reason || "").toLowerCase();
  const unsure =
    reason.includes("ambiguous") ||
    reason.includes("unsure") ||
    reason.includes("can't tell") ||
    reason.includes("did not") ||
    reason.includes("didn't");
  const resting = reason.includes("resting") || reason.includes("no target");

  if (d.action === "ACT") {
    return {
      id: entry.id,
      timestamp: entry.timestamp,
      kind: "action",
      title: label ? `Toggled the ${objectName(label)}` : "Toggled the lamp",
      subtitle: "",
      alert: false,
    };
  }

  if (unsure) {
    return {
      id: entry.id,
      timestamp: entry.timestamp,
      kind: "review",
      title: `Wasn't sure what ${who} meant`,
      subtitle: label ? `Near the ${objectName(label)}` : "Flagged for your review",
      alert: true,
    };
  }

  if (resting || (!label && d.action === "ABSTAIN")) {
    return {
      id: entry.id,
      timestamp: entry.timestamp,
      kind: "device",
      title: "Resting — no target in view",
      subtitle: "",
      alert: false,
    };
  }

  if (label) {
    return {
      id: entry.id,
      timestamp: entry.timestamp,
      kind: "look",
      title: `Looked at the ${objectName(label)}`,
      subtitle: "",
      alert: false,
    };
  }

  return {
    id: entry.id,
    timestamp: entry.timestamp,
    kind: "device",
    title: d.reason || "Device update",
    subtitle: "",
    alert: false,
  };
}

export function matchesChip(item: ActivityItem, chip: ActivityChip): boolean {
  if (chip === "all") return true;
  if (chip === "review") return item.kind === "review";
  if (chip === "actions") return item.kind === "action";
  return item.kind === "device";
}

export function formatMinutesAgo(ts: number, now = Date.now()): string {
  const minutes = Math.max(0, Math.floor((now - ts) / 60000));
  if (minutes < 1) return "just now";
  if (minutes === 1) return "1 min ago";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours === 1) return "1 hour ago";
  if (hours < 24) return `${hours} hours ago`;
  return formatClock(ts);
}

export function formatClock(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}

export function formatStamp(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

export function formatAgo(ts: number, now = Date.now()): string {
  const seconds = Math.max(0, Math.floor((now - ts) / 1000));
  if (seconds < 45) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const rem = minutes % 60;
  if (hours < 24) return rem ? `${hours}h ${rem}m` : `${hours}h`;
  return formatClock(ts);
}

export function dateLabel(ts: number): string {
  const day = new Date(ts);
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const then = new Date(day);
  then.setHours(0, 0, 0, 0);
  const diff = Math.round((start.getTime() - then.getTime()) / 86_400_000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return day.toLocaleDateString([], { month: "short", day: "numeric" });
}

export function groupByDate(items: ActivityItem[]): { label: string; items: ActivityItem[] }[] {
  const groups: { label: string; items: ActivityItem[] }[] = [];
  for (const item of items) {
    const label = dateLabel(item.timestamp);
    const last = groups[groups.length - 1];
    if (last && last.label === label) last.items.push(item);
    else groups.push({ label, items: [item] });
  }
  return groups;
}
