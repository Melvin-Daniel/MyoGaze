import { createContext, createElement, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

const STORAGE_KEY = "myogaze.settings.v1";

export type TextSize = "normal" | "large" | "xl";
export type BreakInterval = 20 | 30 | 45 | 60;

export interface AppPrefs {
  notifications: {
    breakReminders: boolean;
    calibration: boolean;
    laptopDisconnected: boolean;
    dailySummary: boolean;
  };
  quietHours: {
    enabled: boolean;
    start: string;
    end: string;
  };
  breaks: {
    enabled: boolean;
    intervalMin: BreakInterval;
  };
  accessibility: {
    textSize: TextSize;
    highContrast: boolean;
    reduceMotion: boolean;
    visualFeedback: boolean;
    audioFeedback: boolean;
  };
  lastCalibratedAt: number | null;
}

export const DEFAULT_PREFS: AppPrefs = {
  notifications: {
    breakReminders: true,
    calibration: true,
    laptopDisconnected: true,
    dailySummary: false,
  },
  quietHours: {
    enabled: false,
    start: "22:00",
    end: "07:00",
  },
  breaks: {
    enabled: false,
    intervalMin: 30,
  },
  accessibility: {
    textSize: "normal",
    highContrast: false,
    reduceMotion: false,
    visualFeedback: true,
    audioFeedback: false,
  },
  lastCalibratedAt: null,
};

function mergePrefs(raw: unknown): AppPrefs {
  if (!raw || typeof raw !== "object") return DEFAULT_PREFS;
  const value = raw as Partial<AppPrefs>;
  return {
    notifications: { ...DEFAULT_PREFS.notifications, ...value.notifications },
    quietHours: { ...DEFAULT_PREFS.quietHours, ...value.quietHours },
    breaks: { ...DEFAULT_PREFS.breaks, ...value.breaks },
    accessibility: { ...DEFAULT_PREFS.accessibility, ...value.accessibility },
    lastCalibratedAt:
      typeof value.lastCalibratedAt === "number" || value.lastCalibratedAt === null
        ? value.lastCalibratedAt
        : DEFAULT_PREFS.lastCalibratedAt,
  };
}

export function loadPrefs(): AppPrefs {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PREFS;
    return mergePrefs(JSON.parse(raw));
  } catch {
    return DEFAULT_PREFS;
  }
}

export function savePrefs(prefs: AppPrefs) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    /* private mode */
  }
}

export function isQuietHour(now: Date, prefs: AppPrefs): boolean {
  if (!prefs.quietHours.enabled) return false;
  const [sh, sm] = prefs.quietHours.start.split(":").map(Number);
  const [eh, em] = prefs.quietHours.end.split(":").map(Number);
  const start = sh * 60 + sm;
  const end = eh * 60 + em;
  const cur = now.getHours() * 60 + now.getMinutes();
  if (start === end) return true;
  if (start < end) return cur >= start && cur < end;
  return cur >= start || cur < end;
}

export function formatCalibrated(ts: number | null): string {
  if (!ts) return "Not calibrated yet";
  const date = new Date(ts);
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const then = new Date(date);
  then.setHours(0, 0, 0, 0);
  const time = date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  const diff = Math.round((start.getTime() - then.getTime()) / 86_400_000);
  if (diff === 0) return `Today, ${time}`;
  if (diff === 1) return `Yesterday, ${time}`;
  return `${date.toLocaleDateString([], { month: "short", day: "numeric" })}, ${time}`;
}

export function calibrationQuality(ts: number | null): "Calibrated" | "Needs recalibration" | "Not calibrated" {
  if (!ts) return "Not calibrated";
  const age = Date.now() - ts;
  if (age > 12 * 60 * 60 * 1000) return "Needs recalibration";
  return "Calibrated";
}

type PrefsContextValue = {
  prefs: AppPrefs;
  setPrefs: (next: AppPrefs) => void;
  patchPrefs: (partial: Partial<AppPrefs>) => void;
};

const PrefsContext = createContext<PrefsContextValue | null>(null);

export function PrefsProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefsState] = useState<AppPrefs>(loadPrefs);

  const setPrefs = useCallback((next: AppPrefs) => {
    setPrefsState(next);
    savePrefs(next);
  }, []);

  const patchPrefs = useCallback((partial: Partial<AppPrefs>) => {
    setPrefsState((prev) => {
      const next = mergePrefs({ ...prev, ...partial });
      savePrefs(next);
      return next;
    });
  }, []);

  const value = useMemo(() => ({ prefs, setPrefs, patchPrefs }), [prefs, setPrefs, patchPrefs]);
  return createElement(PrefsContext.Provider, { value }, children);
}

export function usePrefs(): PrefsContextValue {
  const ctx = useContext(PrefsContext);
  if (!ctx) throw new Error("usePrefs must be used inside PrefsProvider");
  return ctx;
}
