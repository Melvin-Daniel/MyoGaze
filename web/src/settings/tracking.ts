import type { NeuroShiftEngine } from "../useNeuroShift";

export type LaptopState = "connected" | "reconnecting" | "offline";
export type CameraState = "on" | "idle" | "offline";
export type LampState = "on" | "off" | "offline";
export type TrackingLabel = "Active" | "Idle" | "Offline" | "Needs calibration";

export function lampDevice(engine: NeuroShiftEngine) {
  return (
    engine.devices.find((device) => /lamp|bulb|light/i.test(`${device.id} ${device.label}`)) ??
    engine.devices.find((device) => device.id === "lamp") ??
    null
  );
}

export function laptopState(engine: NeuroShiftEngine): LaptopState {
  return engine.connection;
}

export function cameraState(engine: NeuroShiftEngine): CameraState {
  if (engine.connection === "offline") return "offline";
  return engine.sessionState === "running" ? "on" : "idle";
}

export function lampState(engine: NeuroShiftEngine): LampState {
  if (engine.connection === "offline") return "offline";
  const lamp = lampDevice(engine);
  if (!lamp) return "offline";
  return lamp.is_on ? "on" : "off";
}

export function trackingLabel(engine: NeuroShiftEngine, lastCalibratedAt: number | null): TrackingLabel {
  if (engine.connection === "offline") return "Offline";
  if (engine.sessionState !== "running") return "Idle";
  if (!lastCalibratedAt) return "Needs calibration";
  return "Active";
}

export type WizardPhase = "need-session" | "ready" | "center" | "lamp" | "done" | "timeout" | "face";

export function wizardPhase(engine: NeuroShiftEngine): WizardPhase {
  if (engine.sessionState !== "running") return "need-session";
  const reason = (engine.decision.reason || "").trim();
  if (/timed out/i.test(reason)) return "timeout";
  if (/face the camera/i.test(reason)) return "face";
  if (/look templates saved|center saved/i.test(reason)) return "done";
  if (/look at the real lamp/i.test(reason)) return "lamp";
  if (/look at the camera/i.test(reason)) return "center";
  return "ready";
}

export function isCalibrationComplete(reason: string): boolean {
  return /look templates saved|center saved/i.test(reason);
}

export function isCalibrationFailure(reason: string): boolean {
  return /timed out/i.test(reason);
}

export type DiagnosticCheck = {
  id: string;
  label: string;
  ok: boolean;
  detail: string;
};

export function runDiagnostics(engine: NeuroShiftEngine, lastCalibratedAt: number | null, lastTickAt: number | null): DiagnosticCheck[] {
  const laptop = engine.connection === "connected";
  const cameraOn = engine.sessionState === "running";
  const hasPreview = Boolean(engine.previewJpeg);
  const lamp = lampDevice(engine);
  const recentTick = lastTickAt !== null && Date.now() - lastTickAt < 8000;
  const calibrated = lastCalibratedAt !== null;

  return [
    {
      id: "laptop",
      label: "Laptop",
      ok: laptop,
      detail: laptop ? "Connected" : engine.connection === "reconnecting" ? "Reconnecting" : "Offline",
    },
    {
      id: "camera",
      label: "Camera",
      ok: cameraOn && (hasPreview || recentTick),
      detail: !laptop
        ? "Laptop is offline"
        : cameraOn
          ? hasPreview || recentTick
            ? "Session running"
            : "Session on, no frame yet"
          : "Idle — start Live",
    },
    {
      id: "calibration",
      label: "Calibration",
      ok: calibrated,
      detail: calibrated ? "Saved on this phone" : "Not calibrated yet",
    },
    {
      id: "lamp",
      label: "Lamp",
      ok: laptop && Boolean(lamp),
      detail: !laptop ? "Laptop is offline" : lamp ? (lamp.is_on ? "On" : "Off") : "Not in device list",
    },
    {
      id: "sync",
      label: "Data sync",
      ok: laptop && (recentTick || cameraOn),
      detail: laptop ? (recentTick || cameraOn ? "Receiving session data" : "Connected, waiting for a tick") : "Not connected",
    },
  ];
}
