export type Device = {
  id: string
  label: string
  is_on: boolean
  toggle_count: number
}

export type Decision = {
  ts?: string | null
  action: string
  selected_device?: string | null
  selected_label?: string | null
  reason: string
  yaw?: number | null
  emg?: number | null
}

export type Session = {
  acts: number
  abstains: number
  actuations: number
  emg_without_gaze: number
  gaze_without_emg: number
  far_proxy: number
  act_rate: number
  abstain_rate: number
  started_at?: string | null
  ended_at?: string | null
  note?: string | null
}

export type Settings = {
  product_name: string
  dwell_seconds: number
  yaw_side_threshold: number
  emg_confirm_threshold: number
  act_cooldown_seconds: number
  mqtt_enabled: boolean
  mqtt_host: string
  emg_mode: string
  emg_serial_port: string
  principle: string
  pipeline_mode?: string
  camera_index?: number
  camera_ok?: boolean | null
}

export type Status = {
  ok: boolean
  version: string
  mode: string
  principle: string
  devices: Device[]
  last_decision: Decision | null
  session: Session
  demo_running: boolean
  camera_ok?: boolean | null
  camera_message?: string | null
  detect_mode?: string
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  status: () => json<Status>('/api/status'),
  camera: () => json<{ ok: boolean; message: string; index: number }>('/api/camera'),
  devices: () => json<Device[]>('/api/devices'),
  decisions: () => json<Decision[]>('/api/decisions'),
  session: () => json<Session>('/api/session'),
  settings: () => json<Settings>('/api/settings'),
  saveSettings: (body: Partial<Settings>) =>
    json<Settings>('/api/settings', { method: 'PUT', body: JSON.stringify(body) }),
  startDemo: (mode: 'live' | 'mock' = 'live') =>
    json<{ started: boolean; message: string; mode?: string }>('/api/demo/start', {
      method: 'POST',
      body: JSON.stringify({ mode }),
    }),
  stopDemo: () => json<{ stopped: boolean }>('/api/demo/stop', { method: 'POST' }),
  confirm: () => json<{ ok: boolean; message: string }>('/api/confirm', { method: 'POST' }),
  setDetectMode: (mode: 'objects' | 'slots') =>
    json<{ ok: boolean; detect_mode: string; message: string }>('/api/detect_mode', {
      method: 'POST',
      body: JSON.stringify({ mode }),
    }),
  resetSession: () => json<{ ok: boolean }>('/api/session/reset', { method: 'POST' }),
  toggleDevice: (id: string) =>
    json<Device>(`/api/devices/${id}/toggle`, { method: 'POST' }),
}

export function wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = window.location.host
  // In Vite dev, proxy /ws → backend
  return `${proto}://${host}/ws`
}
