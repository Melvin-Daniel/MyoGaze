/**
 * NeuroShift live engine — same hook contract as Claude's mockEngine,
 * backed by the FastAPI Control App (REST + WebSocket).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api, wsUrl, type Decision as ApiDecision, type Settings as ApiSettings } from "./api";
import type {
  ActivityEntry,
  ConnectionStatus,
  Decision,
  Device,
  LiveTarget,
  SessionRunState,
  SessionStats,
  Settings,
  ToastMessage,
} from "./types";

const REASON_MAP: Record<string, string> = {
  gaze_selected_and_emg_confirmed: "Gaze locked and muscle confirmed — safe to act.",
  gaze_selected_but_emg_not_confirmed: "Looking is not enough — waiting for confirmation.",
  emg_without_stable_gaze_target: "Muscle signal without a stable target — refused.",
  no_gaze_target_and_no_emg: "No target in view. Resting.",
};

const IDLE_DECISION: Decision = {
  action: "IDLE",
  selected_label: null,
  reason: "Session idle — start a monitor session to begin reading intention.",
  yaw: 0,
  emg: 0,
};

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

function humanReason(reason: string): string {
  return REASON_MAP[reason] || reason;
}

function toUiDecision(d: ApiDecision | null | undefined, fallback?: Partial<Decision>): Decision {
  if (!d) {
    return { ...IDLE_DECISION, ...fallback };
  }
  const action = (d.action === "ACT" || d.action === "ABSTAIN" ? d.action : "IDLE") as Decision["action"];
  return {
    action,
    selected_label: d.selected_label ?? d.selected_device ?? null,
    reason: humanReason(d.reason),
    yaw: typeof d.yaw === "number" ? d.yaw : 0,
    emg: typeof d.emg === "number" ? d.emg : 0,
  };
}

function toUiSettings(s: ApiSettings): Settings {
  return {
    dwell_seconds: s.dwell_seconds,
    yaw_side_threshold: s.yaw_side_threshold,
    emg_confirm_threshold: s.emg_confirm_threshold,
    act_cooldown_seconds: s.act_cooldown_seconds,
    mqtt_host: s.mqtt_host,
    emg_serial_port: s.emg_serial_port,
  };
}

export function useNeuroShift() {
  const [connection, setConnection] = useState<ConnectionStatus>("reconnecting");
  const [sessionState, setSessionState] = useState<SessionRunState>("idle");
  const [devices, setDevices] = useState<Device[]>([
    { id: "lamp", label: "Lamp", is_on: false, toggle_count: 0 },
    { id: "fan", label: "Fan", is_on: false, toggle_count: 0 },
    { id: "plug", label: "Plug", is_on: false, toggle_count: 0 },
  ]);
  const [settings, setSettings] = useState<Settings>({
    dwell_seconds: 0.55,
    yaw_side_threshold: 0.2,
    emg_confirm_threshold: 0.5,
    act_cooldown_seconds: 0.7,
    mqtt_host: "127.0.0.1",
    emg_serial_port: "COM3",
  });
  const [decision, setDecision] = useState<Decision>(IDLE_DECISION);
  const [stats, setStats] = useState<SessionStats>({
    acts: 0,
    abstains: 0,
    actuations: 0,
    far_proxy: 0,
  });
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [previewTick, setPreviewTick] = useState(0);
  const [previewJpeg, setPreviewJpeg] = useState<string | null>(null);
  const [detectMode, setDetectMode] = useState<"objects" | "slots">("objects");
  const [liveTargets, setLiveTargets] = useState<LiveTarget[]>([]);
  const saveTimer = useRef<number | null>(null);
  const lastLoggedKey = useRef<string>("");

  const pushToast = useCallback((text: string, tone: ToastMessage["tone"] = "neutral") => {
    const t: ToastMessage = { id: uid(), text, tone };
    setToasts((prev) => [...prev, t].slice(-4));
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((x) => x.id !== t.id));
    }, 3600);
  }, []);

  const applySession = useCallback((s: {
    acts?: number;
    abstains?: number;
    actuations?: number;
    far_proxy?: number;
  }) => {
    setStats({
      acts: s.acts ?? 0,
      abstains: s.abstains ?? 0,
      actuations: s.actuations ?? 0,
      far_proxy: s.far_proxy ?? 0,
    });
  }, []);

  const bootstrap = useCallback(async () => {
    try {
      const [st, dec, set] = await Promise.all([
        api.status(),
        api.decisions(),
        api.settings(),
      ]);
      setDevices(st.devices);
      setSessionState(st.demo_running ? "running" : "idle");
      applySession(st.session);
      setSettings(toUiSettings(set));
      if (st.last_decision) {
        setDecision(toUiDecision(st.last_decision));
      }
      setActivity(
        dec
          .map((d) => ({
            id: uid(),
            timestamp: d.ts ? Date.parse(d.ts) || Date.now() : Date.now(),
            decision: toUiDecision(d),
          }))
          .reverse(),
      );
    } catch {
      setConnection("offline");
    }
  }, [applySession]);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let alive = true;
    let retry: number | undefined;

    const connect = () => {
      ws = new WebSocket(wsUrl());
      ws.onopen = () => {
        if (!alive) return;
        setConnection("connected");
      };
      ws.onclose = () => {
        if (!alive) return;
        setConnection("reconnecting");
        retry = window.setTimeout(connect, 1500);
      };
      ws.onerror = () => {
        if (!alive) return;
        setConnection("reconnecting");
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === "hello" || msg.type === "session_reset") {
            const payload = msg.payload;
            if (payload?.devices) setDevices(payload.devices);
            if (payload?.session) applySession(payload.session);
      if (payload?.demo_running != null) {
              setSessionState(payload.demo_running ? "running" : "idle");
            }
            if (payload?.detect_mode === "objects" || payload?.detect_mode === "slots") {
              setDetectMode(payload.detect_mode);
            }
            if (payload?.last_decision) {
              setDecision(toUiDecision(payload.last_decision));
            }
          }
          if (msg.type === "demo_started") {
            setSessionState("running");
            setActivity([]);
            setPreviewJpeg(null);
            setLiveTargets([]);
            setDecision(IDLE_DECISION);
            lastLoggedKey.current = "";
            pushToast("Monitor session started", "neutral");
          }
          if (msg.type === "tick") {
            setPreviewTick((n) => n + 1);
            if (msg.devices) setDevices(msg.devices);
            if (msg.session) applySession(msg.session);
            if (Array.isArray(msg.targets)) setLiveTargets(msg.targets);
            if (msg.detect_mode === "objects" || msg.detect_mode === "slots") {
              setDetectMode(msg.detect_mode);
            }
            if (msg.preview_jpeg_b64) {
              setPreviewJpeg(`data:image/jpeg;base64,${msg.preview_jpeg_b64}`);
            }
            if (msg.decision) {
              const ui = toUiDecision(msg.decision);
              // Prefer live note during streaming if more specific
              if (msg.note && ui.action === "IDLE") {
                ui.reason = msg.note;
              }
              // Gaze progress from dwell when present
              if (typeof msg.dwell === "number" && ui.action === "IDLE") {
                ui.yaw = Math.max(Math.abs(ui.yaw), Math.min(1, msg.dwell));
              }
              setDecision(ui);
              const key = `${ui.action}|${ui.selected_label}|${ui.reason}|${ui.emg}|${ui.yaw}`;
              if (key !== lastLoggedKey.current && (ui.action === "ACT" || ui.action === "ABSTAIN")) {
                lastLoggedKey.current = key;
                setActivity((prev) =>
                  [{ id: uid(), timestamp: Date.now(), decision: ui }, ...prev].slice(0, 200),
                );
              }
            }
            if (msg.actuation) {
              pushToast(
                `${msg.actuation.label} switched — confirmed by gaze + muscle`,
                "act",
              );
            }
          }
          if (msg.type === "detect_mode" && (msg.detect_mode === "objects" || msg.detect_mode === "slots")) {
            setDetectMode(msg.detect_mode);
            if (msg.message) pushToast(msg.message, "neutral");
          }
          if (msg.type === "demo_complete") {
            setSessionState("idle");
            if (msg.session) applySession(msg.session);
            if (msg.devices) setDevices(msg.devices);
            pushToast("Monitor session complete", "neutral");
          }
          if (msg.type === "demo_stopped") {
            setSessionState("idle");
            pushToast("Monitor stopped", "neutral");
          }
          if (msg.type === "device_toggled" && msg.devices) {
            setDevices(msg.devices);
          }
        } catch {
          /* ignore */
        }
      };
    };

    connect();
    return () => {
      alive = false;
      if (retry) window.clearTimeout(retry);
      ws?.close();
    };
  }, [applySession, pushToast]);

  const startSession = useCallback(async () => {
    try {
      // Prefer live camera; backend falls back to mock if camera is busy/missing
      const r = await api.startDemo("live");
      if (!r.started) {
        pushToast(r.message || "Could not start session", "abstain");
      } else {
        pushToast(r.message || "Session started", r.mode === "live" ? "act" : "neutral");
      }
    } catch (e) {
      pushToast(String((e as Error).message || e), "abstain");
    }
  }, [pushToast]);

  const confirmIntent = useCallback(async () => {
    try {
      await api.confirm();
      pushToast("Confirm pulse sent (muscle stand-in)", "act");
    } catch (e) {
      pushToast(String((e as Error).message || e), "abstain");
    }
  }, [pushToast]);

  const toggleDetectMode = useCallback(async () => {
    const next = detectMode === "objects" ? "slots" : "objects";
    try {
      const r = await api.setDetectMode(next);
      if (r.ok) setDetectMode(r.detect_mode as "objects" | "slots");
      pushToast(r.message, "neutral");
    } catch (e) {
      pushToast(String((e as Error).message || e), "abstain");
    }
  }, [detectMode, pushToast]);

  const clearSession = useCallback(async () => {
    try {
      if (sessionState === "running") {
        await api.stopDemo();
      }
      await api.resetSession();
      setSessionState("idle");
      setDecision(IDLE_DECISION);
      setStats({ acts: 0, abstains: 0, actuations: 0, far_proxy: 0 });
      setActivity([]);
      setPreviewJpeg(null);
      setLiveTargets([]);
      lastLoggedKey.current = "";
      const st = await api.status();
      setDevices(st.devices);
      applySession(st.session);
      pushToast("Session cleared", "neutral");
    } catch (e) {
      pushToast(String((e as Error).message || e), "abstain");
    }
  }, [applySession, pushToast, sessionState]);

  const toggleDevice = useCallback(
    async (id: string) => {
      try {
        const d = await api.toggleDevice(id);
        setDevices((prev) => prev.map((x) => (x.id === id ? d : x)));
        pushToast(`${d.label} turned ${d.is_on ? "on" : "off"} — manual override`, "neutral");
      } catch (e) {
        pushToast(String((e as Error).message || e), "abstain");
      }
    },
    [pushToast],
  );

  const updateSettings = useCallback(
    (patch: Partial<Settings>) => {
      setSettings((prev) => {
        const next = { ...prev, ...patch };
        if (saveTimer.current) window.clearTimeout(saveTimer.current);
        saveTimer.current = window.setTimeout(async () => {
          try {
            const saved = await api.saveSettings(next);
            setSettings(toUiSettings(saved));
            pushToast("System settings saved", "neutral");
          } catch (e) {
            pushToast(String((e as Error).message || e), "abstain");
          }
        }, 450);
        return next;
      });
    },
    [pushToast],
  );

  return {
    connection,
    sessionState,
    devices,
    settings,
    decision,
    stats,
    activity,
    toasts,
    previewTick,
    previewJpeg,
    detectMode,
    liveTargets,
    startSession,
    clearSession,
    toggleDevice,
    updateSettings,
    confirmIntent,
    toggleDetectMode,
  };
}
