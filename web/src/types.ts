// NeuroShift — shared types
// These mirror the data shapes described by the backend/API.

export type IntentionAction = "ACT" | "ABSTAIN" | "IDLE";

export interface Device {
  id: string;
  label: string;
  is_on: boolean;
  toggle_count: number;
}

export interface Decision {
  action: IntentionAction;
  selected_label: string | null;
  reason: string;
  yaw: number; // normalized head/gaze yaw, -1..1
  emg: number; // normalized muscle effort, 0..1
}

export interface SessionStats {
  acts: number;
  abstains: number;
  actuations: number;
  far_proxy: number; // false-activation-rate proxy, 0..1
}

export interface Settings {
  dwell_seconds: number;
  yaw_side_threshold: number;
  emg_confirm_threshold: number;
  act_cooldown_seconds: number;
  mqtt_host: string;
  emg_serial_port: string;
}

export type ConnectionStatus = "connected" | "reconnecting" | "offline";
export type SessionRunState = "running" | "idle";

export interface ActivityEntry {
  id: string;
  timestamp: number;
  decision: Decision;
}

export type ViewId = "home" | "monitor" | "activity" | "insights" | "system";

export interface ToastMessage {
  id: string;
  text: string;
  tone: "neutral" | "act" | "abstain";
}

export interface LiveTarget {
  id: string;
  label: string;
  conf: number;
  selected?: boolean;
  candidate?: boolean;
}
