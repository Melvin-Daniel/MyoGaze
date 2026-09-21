/**
 * Where the MyoGaze Control App backend lives.
 *
 * Browser / PWA: same origin, so the base stays empty and requests are relative.
 * Native (Capacitor): the app is served from localhost inside the WebView, so it
 * must be pointed at the laptop running the FastAPI server on the same Wi-Fi.
 */

import { LAN_SERVER_HINT } from "./lanHint";

const STORAGE_KEY = "myogaze.serverBase";

function normalize(raw: string): string {
  let value = raw.trim();
  if (!value) return "";
  if (!/^https?:\/\//i.test(value)) {
    const port = value.match(/:(\d+)$/)?.[1];
    value = `${port === "8443" ? "https" : "http"}://${value}`;
  }
  value = value.replace(/\/+$/, "");
  // Bare host or host without port → assume the default backend port
  if (!/:\d+$/.test(value.replace(/^https?:\/\//i, ""))) {
    const https = /^https:/i.test(value);
    value = `${value}:${https ? "8443" : "8000"}`;
  }
  return value;
}

export function isNativeApp(): boolean {
  const cap = (window as unknown as { Capacitor?: { isNativePlatform?: () => boolean } }).Capacitor;
  return typeof cap?.isNativePlatform === "function" ? cap.isNativePlatform() : false;
}

export function nativePlatform(): "ios" | "android" | "web" {
  const cap = (
    window as unknown as { Capacitor?: { getPlatform?: () => string } }
  ).Capacitor;
  const platform = typeof cap?.getPlatform === "function" ? cap.getPlatform() : "";
  if (platform === "android" || platform === "ios") return platform;
  if (/Android/i.test(navigator.userAgent || "")) return "android";
  if (/iPhone|iPad|iPod/i.test(navigator.userAgent || "")) return "ios";
  return "web";
}

export function isAndroidApp(): boolean {
  return isNativeApp() && nativePlatform() === "android";
}

const STALE_LAN_HOSTS = ["10.20.3.197", "172.20.10.3", "192.168.154.197"];

function remapNativeLoopback(value: string): string {
  if (!value) return value;
  try {
    const host = new URL(normalize(value)).hostname;
    if (STALE_LAN_HOSTS.includes(host)) return normalize(LAN_SERVER_HINT);
  } catch {
    return value;
  }
  return value;
}

export function getServerBase(): string {
  try {
    const stored = localStorage.getItem(STORAGE_KEY) ?? "";
    if (!isNativeApp()) return stored;
    const remapped = remapNativeLoopback(stored);
    if (remapped && remapped !== stored) {
      try {
        localStorage.setItem(STORAGE_KEY, remapped);
      } catch {
        /* keep using remapped in memory */
      }
    }
    return remapped;
  } catch {
    return "";
  }
}

export function setServerBase(value: string): string {
  let normalized = normalize(value);
  if (isNativeApp()) normalized = remapNativeLoopback(normalized);
  try {
    if (normalized) localStorage.setItem(STORAGE_KEY, normalized);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* storage unavailable — keep running with the in-memory default */
  }
  return normalized;
}

/** Prefix for REST calls. Empty string means "same origin". */
export function apiBase(): string {
  return getServerBase();
}

/** Absolute URL for links the browser opens directly (exports, reports). */
export function absoluteUrl(path: string): string {
  const base = getServerBase();
  return base ? `${base}${path}` : path;
}

/** True when a native build still needs the user to enter a server address. */
export function needsServerSetup(): boolean {
  if (!isNativeApp()) return false;
  if (getServerBase()) return false;
  try {
    const host = window.location.hostname;
    if (host && host !== "localhost" && host !== "127.0.0.1") return false;
  } catch {
    /* ignore */
  }
  return true;
}

export async function probeServer(candidate: string): Promise<{ ok: boolean; message: string }> {
  const base = normalize(candidate);
  if (!base) return { ok: false, message: "Enter the laptop address, e.g. 192.168.1.5:8000" };
  try {
    const res = await fetch(`${base}/api/health`, { signal: AbortSignal.timeout(4000) });
    if (!res.ok) return { ok: false, message: `Server replied ${res.status}` };
    const body = (await res.json()) as { version?: string };
    return { ok: true, message: `Connected to MyoGaze ${body.version ?? ""}`.trim() };
  } catch {
    return { ok: false, message: "No response — check Wi-Fi, IP address, and firewall" };
  }
}

const CAMERA_KEY = "myogaze.cameraSource";

export type CameraPref = "auto" | "local" | "remote";

export function isPhoneClient(): boolean {
  if (isNativeApp()) return true;
  const ua = navigator.userAgent || "";
  if (/iPhone|iPod|Android.+Mobile/i.test(ua)) return true;
  if (/iPad/i.test(ua)) return true;
  if (
    typeof navigator.maxTouchPoints === "number" &&
    navigator.maxTouchPoints > 2 &&
    /MacIntel/.test(navigator.platform || "")
  ) {
    return true;
  }
  return false;
}

export function getCameraPref(): CameraPref {
  try {
    const value = localStorage.getItem(CAMERA_KEY);
    if (value === "local" || value === "remote" || value === "auto") return value;
  } catch {
    /* storage unavailable */
  }
  return "auto";
}

export function setCameraPref(value: CameraPref): CameraPref {
  try {
    localStorage.setItem(CAMERA_KEY, value);
  } catch {
    /* storage unavailable */
  }
  return value;
}

/** Which camera the next Start will use. The phone is the control screen; the laptop webcam watches the room unless the user opts into this-device camera. */
export function resolveCameraSource(pref: CameraPref = getCameraPref()): "local" | "remote" {
  if (pref === "remote") return "remote";
  return "local";
}

export function suggestedHttpsOrigin(): string {
  try {
    const url = new URL(window.location.href);
    url.protocol = "https:";
    if (url.port === "8000" || url.port === "") url.port = "8443";
    return url.origin;
  } catch {
    return "";
  }
}

export function phoneCameraNeedsHttps(): boolean {
  if (isNativeApp()) return false;
  return isPhoneClient() && !window.isSecureContext;
}

/** HTTP page that installs the LAN certificate (Safari's Visit Website is a dead end). */
export function iphoneSetupUrl(): string {
  try {
    const url = new URL(window.location.href);
    url.protocol = "http:";
    if (url.port === "8443" || url.port === "") url.port = "8000";
    url.pathname = "/iphone";
    url.search = "";
    url.hash = "";
    return url.toString();
  } catch {
    return "/iphone";
  }
}
