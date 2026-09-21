import type { Decision, LiveTarget, SessionRunState } from "./types";

export type GazePhase =
  | "idle"
  | "searching"
  | "seeing"
  | "looking"
  | "locked"
  | "unsure"
  | "confirmed";

export interface GazeStatus {
  phase: GazePhase;
  kicker: string;
  title: string;
  detail: string;
  shortLabel: string;
  targetLabel: string | null;
  dwellPct: number;
  canConfirm: boolean;
  objectsInView: number;
  focus: LiveTarget | null;
}

const APPLIANCE: Record<string, string> = {
  lamp: "Lamp",
  fan: "Fan",
  plug: "Plug",
  "cell phone": "Phone",
};

export function targetDisplayName(t: LiveTarget): string {
  // Show the object the camera actually saw. Relay mapping (phone → plug)
  // is only for the ESP32 hub — using it here made a phone look "locked on Plug".
  const label = (t.label || "").trim();
  if (label) {
    const mapped = APPLIANCE[label.toLowerCase()];
    return mapped ?? label;
  }
  const id = t.id.toLowerCase();
  if (APPLIANCE[id]) return APPLIANCE[id];
  return t.id;
}

export function collapseTargets(targets: LiveTarget[]): LiveTarget[] {
  const rank = (t: LiveTarget) => (t.ambiguous ? 3 : t.selected ? 2 : t.candidate ? 1 : 0);
  const best = new Map<string, LiveTarget>();
  for (const t of targets) {
    const key = targetDisplayName(t);
    const prev = best.get(key);
    if (!prev || rank(t) > rank(prev)) best.set(key, t);
  }
  return [...best.values()];
}

export function deriveGazeStatus(input: {
  running: boolean | SessionRunState;
  decision: Decision;
  liveTargets: LiveTarget[];
  dwellProgress: number;
  dwellRequired: boolean;
  dwellActuates?: boolean;
}): GazeStatus {
  const running = input.running === true || input.running === "running";
  const dwellPct = Math.round(Math.max(0, Math.min(1, input.dwellProgress)) * 100);
  const targets = input.liveTargets;
  const ambiguous = targets.find((t) => t.ambiguous) ?? null;
  const selected = targets.find((t) => t.selected) ?? null;
  const candidate = targets.find((t) => t.candidate) ?? null;
  const objectsInView = targets.length;
  const dwellActuates = input.dwellActuates !== false;

  const base = {
    dwellPct,
    objectsInView,
    canConfirm: false,
    focus: null as LiveTarget | null,
    targetLabel: null as string | null,
  };

  if (!running) {
    return {
      ...base,
      phase: "idle",
      kicker: "Idle",
      title: "Camera is off",
      detail: "Start the camera to see what you are looking at.",
      shortLabel: "Idle",
    };
  }

  if (input.decision.action === "ACT" && input.decision.selected_label) {
    const label = input.decision.selected_label;
    return {
      ...base,
      phase: "confirmed",
      kicker: "Toggled",
      title: `${label} toggled`,
      detail: "Command sent. Look again when you want the next toggle.",
      shortLabel: "Toggled",
      targetLabel: label,
      canConfirm: false,
      focus: selected,
    };
  }

  if (ambiguous) {
    const name = targetDisplayName(ambiguous);
    return {
      ...base,
      phase: "unsure",
      kicker: "Unsure",
      title: "Can't tell which device",
      detail: `Gaze is split between ${name} and something nearby. Look at one thing only.`,
      shortLabel: "Unsure",
      targetLabel: name,
      focus: ambiguous,
    };
  }

  if (selected) {
    const name = targetDisplayName(selected);
    return {
      ...base,
      phase: "locked",
      kicker: "Locked",
      title: `Locked on ${name}`,
      detail: dwellActuates
        ? "Hold complete — toggling now."
        : "This is the target. Tap Confirm to turn it on or off.",
      shortLabel: "Locked",
      targetLabel: name,
      dwellPct: 100,
      canConfirm: !dwellActuates,
      focus: selected,
    };
  }

  if (candidate) {
    const name = targetDisplayName(candidate);
    if (!input.dwellRequired) {
      return {
        ...base,
        phase: "locked",
        kicker: "Ready",
        title: `Looking at ${name}`,
        detail: dwellActuates
          ? "Look-and-hold will toggle this device."
          : "Tap Confirm to turn it on or off.",
        shortLabel: "Ready",
        targetLabel: name,
        dwellPct: 100,
        canConfirm: !dwellActuates,
        focus: candidate,
      };
    }
    return {
      ...base,
      phase: "looking",
      kicker: "Locking",
      title: `Locking onto ${name}`,
      detail:
        dwellPct >= 100
          ? dwellActuates
            ? "Hold complete — toggling now."
            : "Hold is complete — keep looking."
          : dwellActuates
            ? `Keep looking. ${dwellPct}% — it toggles at 100%.`
            : `Keep looking. ${dwellPct}% of the hold is done.`,
      shortLabel: "Locking",
      targetLabel: name,
      canConfirm: false,
      focus: candidate,
    };
  }

  if (objectsInView === 0) {
    return {
      ...base,
      phase: "searching",
      kicker: "Searching",
      title: "Nothing in view yet",
      detail: "Point the laptop camera at the lamp.",
      shortLabel: "Searching",
    };
  }

  return {
    ...base,
    phase: "seeing",
    kicker: "In view",
    title: `${objectsInView} object${objectsInView === 1 ? "" : "s"} in view`,
    detail: "Look at the lamp and hold for two seconds to toggle it.",
    shortLabel: "In view",
  };
}
