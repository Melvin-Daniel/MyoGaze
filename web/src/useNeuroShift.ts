/**
 * NeuroShift live engine — same hook contract as Claude's mockEngine,
 * backed by the FastAPI Control App (REST + WebSocket).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api, wsUrl, type Decision as ApiDecision, type Settings as ApiSettings } from "./api";
import {
  absoluteUrl,
  getCameraPref,
  phoneCameraNeedsHttps,
  resolveCameraSource,
  setCameraPref,
  suggestedHttpsOrigin,
  iphoneSetupUrl,
  type CameraPref,
} from "./serverConfig";
import { phoneCamera } from "./phoneCamera";
import type {
  ActivityEntry,
  ConnectionStatus,
  CuedSummary,
  CuedTrial,
  Decision,
  Device,
  LiveTarget,
  SessionRunState,
  SessionStats,
  Settings,
  TrialSummary,
  ToastMessage,
} from "./types";

const EMPTY_CUED: CuedSummary = {
  trials: 0,
  hits: 0,
  wrong: 0,
  misses: 0,
  accuracy: 0,
  false_activation_rate: 0,
  miss_rate: 0,
  latency_s: { median: null, mean: null, min: null, max: null },
  pending: null,
  by_condition: {},
};

const REASON_MAP: Record<string, string> = {
  gaze_selected_and_emg_confirmed: "Gaze locked and muscle confirmed — safe to act.",
  gaze_selected_but_emg_not_confirmed: "Looking is not enough — waiting for confirmation.",
  emg_without_stable_gaze_target: "Muscle signal without a stable target — refused.",
  no_gaze_target_and_no_emg: "No target in view. Resting.",
  ambiguous_gaze_targets: "Two objects under gaze — unsure, so abstain.",
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
    dwell_required: s.dwell_required ?? true,
    dwell_actuates: s.dwell_actuates ?? true,
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
    dwell_seconds: 2.0,
    yaw_side_threshold: 0.2,
    emg_confirm_threshold: 0.5,
    act_cooldown_seconds: 0.7,
    mqtt_host: "127.0.0.1",
    emg_serial_port: "COM3",
    dwell_actuates: true,
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
  const [gazePoint, setGazePoint] = useState<[number, number] | null>(null);
  const [dwellRequired, setDwellRequired] = useState(true);
  const [trialSummary, setTrialSummary] = useState<TrialSummary | null>(null);
  const [cuedSummary, setCuedSummary] = useState<CuedSummary>(EMPTY_CUED);
  const [activeCue, setActiveCue] = useState<CuedTrial | null>(null);
  const [cuedTrials, setCuedTrials] = useState<CuedTrial[]>([]);
  const [dwellProgress, setDwellProgress] = useState(0);
  const [cameraPref, setCameraPrefState] = useState<CameraPref>(() => getCameraPref());
  const [iphoneSetupLan, setIphoneSetupLan] = useState<string | null>(null);
  const [androidApkUrl, setAndroidApkUrl] = useState<string | null>(null);
  const saveTimer = useRef<number | null>(null);
  const lastLoggedKey = useRef<string>("");
  const lastCueKey = useRef<string>("");
  const wsRef = useRef<WebSocket | null>(null);

  const cameraSource = resolveCameraSource(cameraPref);
  const httpsHint = suggestedHttpsOrigin();
  const iphoneSetup = iphoneSetupUrl();
  const phoneNeedsHttps = phoneCameraNeedsHttps();

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
      if (st.iphone_setup_url) setIphoneSetupLan(st.iphone_setup_url);
      setAndroidApkUrl(st.android_apk_url ?? null);
      setSessionState(st.demo_running ? "running" : "idle");
      applySession(st.session);
      setSettings(toUiSettings(set));
      setDwellRequired(set.dwell_required ?? true);
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
      try {
        const evalState = await api.evalState();
        setCuedSummary(evalState.summary);
        setActiveCue(evalState.active);
        setCuedTrials(evalState.trials);
      } catch {
        /* eval endpoint optional during older servers */
      }
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
      wsRef.current = ws;
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
            if (typeof payload?.dwell_required === "boolean") {
              setDwellRequired(payload.dwell_required);
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
            setGazePoint(null);
            setDecision(IDLE_DECISION);
            lastLoggedKey.current = "";
            pushToast("Camera started", "neutral");
          }
          if (msg.type === "tick") {
            setPreviewTick((n) => n + 1);
            if (msg.devices) setDevices(msg.devices);
            if (msg.session) applySession(msg.session);
            if (Array.isArray(msg.targets)) setLiveTargets(msg.targets);
            if (
              Array.isArray(msg.gaze_xy) &&
              msg.gaze_xy.length === 2 &&
              Number.isFinite(msg.gaze_xy[0]) &&
              Number.isFinite(msg.gaze_xy[1])
            ) {
              setGazePoint([msg.gaze_xy[0], msg.gaze_xy[1]]);
            } else {
              setGazePoint(null);
            }
            if (msg.detect_mode === "objects" || msg.detect_mode === "slots") {
              setDetectMode(msg.detect_mode);
            }
            if (msg.preview_jpeg_b64) {
              setPreviewJpeg(`data:image/jpeg;base64,${msg.preview_jpeg_b64}`);
            }
            if (typeof msg.dwell === "number") {
              setDwellProgress(Math.max(0, Math.min(1, msg.dwell)));
            }
            if (msg.cued) {
              if (msg.cued.summary) setCuedSummary(msg.cued.summary as CuedSummary);
              setActiveCue((msg.cued.active as CuedTrial | null) ?? null);
              const resolved = msg.cued.last_resolved as CuedTrial | null | undefined;
              if (resolved?.outcome && resolved.resolved_ts && resolved.resolved_ts !== lastCueKey.current) {
                lastCueKey.current = resolved.resolved_ts;
                const tone = resolved.outcome === "HIT" ? "act" : "abstain";
                pushToast(`${resolved.outcome}: looked for ${resolved.cued_label}`, tone);
                setCuedTrials((prev) => {
                  const rest = prev.filter((t) => t.index !== resolved.index);
                  return [...rest, resolved].sort((a, b) => a.index - b.index);
                });
              }
            }
            if (msg.decision) {
              const ui = toUiDecision(msg.decision);
              // Prefer live note during streaming if more specific
              if (msg.note && ui.action === "IDLE") {
                ui.reason = msg.note;
              }
              setDecision(ui);
              const key = `${ui.action}|${ui.selected_label}|${ui.reason}`;
              const resting =
                ui.action === "ABSTAIN" &&
                (ui.reason.includes("Resting") || ui.reason.includes("No target in view"));
              if (key !== lastLoggedKey.current && (ui.action === "ACT" || (ui.action === "ABSTAIN" && !resting))) {
                lastLoggedKey.current = key;
                setActivity((prev) =>
                  [{ id: uid(), timestamp: Date.now(), decision: ui }, ...prev].slice(0, 200),
                );
              }
            }
            if (msg.actuation) {
              pushToast(
                `${msg.actuation.label} switched`,
                "act",
              );
            }
          }
          if (msg.type === "dwell_mode" && typeof msg.dwell_required === "boolean") {
            setDwellRequired(msg.dwell_required);
            if (msg.message) pushToast(msg.message, "neutral");
          }
          if (msg.type === "detect_mode" && (msg.detect_mode === "objects" || msg.detect_mode === "slots")) {
            setDetectMode(msg.detect_mode);
            if (msg.message) pushToast(msg.message, "neutral");
          }
          if (msg.type === "demo_complete") {
            setSessionState("idle");
            if (msg.session) applySession(msg.session);
            if (msg.devices) setDevices(msg.devices);
            void api.trials().then((t) => setTrialSummary(t.summary as unknown as TrialSummary));
            pushToast("Session saved", "neutral");
          }
          if (msg.type === "demo_stopped") {
            setSessionState("idle");
            setGazePoint(null);
            phoneCamera.stop();
            pushToast("Tracking paused", "neutral");
          }
          if (msg.type === "error" && msg.message) {
            setSessionState("idle");
            phoneCamera.stop();
            pushToast(String(msg.message), "abstain");
          }
          if (msg.type === "device_toggled" && msg.devices) {
            setDevices(msg.devices);
          }
          if (msg.type === "cue_started" || msg.type === "cue_skipped" || msg.type === "cue_reset") {
            if (msg.summary) setCuedSummary(msg.summary as CuedSummary);
            setActiveCue((msg.active as CuedTrial | null) ?? null);
            if (msg.message) pushToast(msg.message, "neutral");
          }
          if (msg.type === "calibrated" && msg.message) {
            pushToast(msg.message, "neutral");
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
      wsRef.current = null;
      phoneCamera.stop();
    };
  }, [applySession, pushToast]);

  const sendCameraFrame = useCallback((jpegB64: string) => {
    const socket = wsRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    if (socket.bufferedAmount > 80_000) return;
    socket.send(JSON.stringify({ cmd: "camera_frame", jpeg_b64: jpegB64 }));
  }, []);

  const startSession = useCallback(async () => {
    const camera = resolveCameraSource(getCameraPref());
    try {
      if (camera === "remote") {
        await phoneCamera.start(sendCameraFrame);
      } else {
        phoneCamera.stop();
      }
      const r = await api.startDemo("live", camera);
      if (!r.started && !/already running/i.test(r.message || "")) {
        phoneCamera.stop();
        pushToast(r.message || "Could not start session", "abstain");
      } else {
        pushToast(r.message || "Session started", r.mode === "live" ? "act" : "neutral");
      }
    } catch (e) {
      phoneCamera.stop();
      pushToast(String((e as Error).message || e), "abstain");
    }
  }, [pushToast, sendCameraFrame]);

  const startMockSession = useCallback(async () => {
    try {
      const r = await api.startDemo("mock");
      phoneCamera.stop();
      if (!r.started) {
        pushToast(r.message || "Could not start mock demo", "abstain");
      } else {
        pushToast(r.message || "Mock demo started", "neutral");
      }
    } catch (e) {
      pushToast(String((e as Error).message || e), "abstain");
    }
  }, [pushToast]);

  const confirmIntent = useCallback(async () => {
    try {
      await api.confirm();
      pushToast("Look complete — toggle sent", "act");
    } catch (e) {
      pushToast(String((e as Error).message || e), "abstain");
    }
  }, [pushToast]);

  const toggleDwellMode = useCallback(async () => {
    const next = !dwellRequired;
    try {
      const r = await api.setDwellMode(next);
      if (r.ok) setDwellRequired(r.dwell_required);
      pushToast(r.message, "neutral");
    } catch (e) {
      pushToast(String((e as Error).message || e), "abstain");
    }
  }, [dwellRequired, pushToast]);

  const exportTrials = useCallback((format: "json" | "csv") => {
    const path = format === "json" ? "/api/trials/export.json" : "/api/trials/export.csv";
    window.open(absoluteUrl(path), "_blank");
  }, []);

  const exportReport = useCallback(() => {
    window.open(absoluteUrl("/api/report.html"), "_blank");
  }, []);

  const markTrialBlock = useCallback(
    async (label: string) => {
      try {
        const r = await api.markTrial(label);
        if (r.summary) setTrialSummary(r.summary as unknown as TrialSummary);
        pushToast(r.message, "neutral");
      } catch (e) {
        pushToast(String((e as Error).message || e), "abstain");
      }
    },
    [pushToast],
  );

  const refreshTrials = useCallback(async () => {
    try {
      const t = await api.trials();
      setTrialSummary(t.summary as unknown as TrialSummary);
    } catch {
      /* ignore */
    }
  }, []);

  const startCue = useCallback(
    async (deviceId?: string) => {
      try {
        const r = await api.startCue(deviceId);
        if (r.summary) setCuedSummary(r.summary);
        setActiveCue(r.active ?? null);
        pushToast(r.message, "neutral");
      } catch (e) {
        pushToast(String((e as Error).message || e), "abstain");
      }
    },
    [pushToast],
  );

  const skipCue = useCallback(async () => {
    try {
      const r = await api.skipCue();
      if (r.summary) setCuedSummary(r.summary);
      setActiveCue(null);
      pushToast(r.message, "neutral");
    } catch (e) {
      pushToast(String((e as Error).message || e), "abstain");
    }
  }, [pushToast]);

  const resetCues = useCallback(async () => {
    try {
      const r = await api.resetCues();
      if (r.summary) setCuedSummary(r.summary);
      setActiveCue(null);
      setCuedTrials([]);
      lastCueKey.current = "";
      pushToast(r.message, "neutral");
    } catch (e) {
      pushToast(String((e as Error).message || e), "abstain");
    }
  }, [pushToast]);

  const calibrateGaze = useCallback(async () => {
    try {
      const r = await api.calibrate();
      pushToast(r.message, r.ok ? "neutral" : "abstain");
      return r;
    } catch (e) {
      const message = String((e as Error).message || e);
      pushToast(message, "abstain");
      return { ok: false as const, message };
    }
  }, [pushToast]);

  const exportCued = useCallback((format: "json" | "csv") => {
    const path = format === "json" ? "/api/eval/export.json" : "/api/eval/export.csv";
    window.open(absoluteUrl(path), "_blank");
  }, []);

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

  const pauseSession = useCallback(async () => {
    try {
      if (sessionState === "running") {
        await api.stopDemo();
      } else {
        phoneCamera.stop();
        setSessionState("idle");
      }
    } catch (e) {
      pushToast(String((e as Error).message || e), "abstain");
    }
  }, [pushToast, sessionState]);

  const clearSession = useCallback(async () => {
    try {
      if (sessionState === "running") {
        await api.stopDemo();
      }
      phoneCamera.stop();
      await api.resetSession();
      setSessionState("idle");
      setDecision(IDLE_DECISION);
      setStats({ acts: 0, abstains: 0, actuations: 0, far_proxy: 0 });
      setActivity([]);
      setPreviewJpeg(null);
      setLiveTargets([]);
      lastLoggedKey.current = "";
      setDwellProgress(0);
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

  const updateCameraPref = useCallback((next: CameraPref) => {
    setCameraPref(next);
    setCameraPrefState(next);
  }, []);

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
    gazePoint,
    dwellRequired,
    trialSummary,
    cuedSummary,
    activeCue,
    cuedTrials,
    dwellProgress,
    cameraPref,
    cameraSource,
    phoneNeedsHttps,
    httpsHint,
    iphoneSetup,
    iphoneSetupLan,
    androidApkUrl,
    startSession,
    startMockSession,
    pauseSession,
    clearSession,
    toggleDevice,
    updateSettings,
    updateCameraPref,
    confirmIntent,
    toggleDetectMode,
    toggleDwellMode,
    exportTrials,
    exportReport,
    exportCued,
    markTrialBlock,
    refreshTrials,
    startCue,
    skipCue,
    resetCues,
    calibrateGaze,
  };
}

export type NeuroShiftEngine = ReturnType<typeof useNeuroShift>;
