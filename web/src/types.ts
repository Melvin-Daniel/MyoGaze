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

export interface TrialSummary {
  total_records: number;
  decisions: number;
  actuations: number;
  confirms: number;
  acts: number;
  abstains: number;
  markers?: number;
}

export interface Settings {
  dwell_seconds: number;
  yaw_side_threshold: number;
  emg_confirm_threshold: number;
  act_cooldown_seconds: number;
  mqtt_host: string;
  emg_serial_port: string;
    dwell_required?: boolean;
    dwell_actuates?: boolean;
}

export type ConnectionStatus = "connected" | "reconnecting" | "offline";
export type SessionRunState = "running" | "idle";

export interface ActivityEntry {
  id: string;
  timestamp: number;
  decision: Decision;
}

export type ViewId = "home" | "live" | "activity" | "settings";

export interface ToastMessage {
  id: string;
  text: string;
  tone: "neutral" | "act" | "abstain";
}

/** One cued trial: the app names a target, the outcome is scored against it. */
export interface CuedTrial {
  index: number;
  cued_device_id: string;
  cued_label: string;
  cue_ts: string;
  dwell_required: boolean;
  detect_mode: string;
  outcome: "HIT" | "WRONG" | "MISS" | null;
  selected_device_id: string | null;
  selected_label: string | null;
  latency_s: number | null;
  resolved_ts: string | null;
}

export interface LatencyStats {
  median: number | null;
  mean: number | null;
  min: number | null;
  max: number | null;
}

export interface CuedScore {
  trials: number;
  hits: number;
  wrong: number;
  misses: number;
  accuracy: number;
  false_activation_rate: number;
  miss_rate: number;
  latency_s: LatencyStats;
}

export interface CuedSummary extends CuedScore {
  pending: number | null;
  by_condition: Partial<Record<"dwell_gated" | "instant_gaze", CuedScore>>;
}

export interface LiveTarget {
  id: string;
  label: string;
  conf: number;
  selected?: boolean;
  candidate?: boolean;
  relay?: string;
  ambiguous?: boolean;
  /** x0, y0, x1, y1 in 0–1 of the camera frame. */
  box?: [number, number, number, number] | null;
}
