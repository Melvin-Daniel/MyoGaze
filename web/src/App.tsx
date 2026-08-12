import { useMemo, useState } from "react";
import "./index.css";
import type { ViewId } from "./types";
import { useNeuroShift } from "./useNeuroShift";
import { Nav } from "./components/Nav";
import { ToastStack } from "./components/Toast";
import { IntentionMeter } from "./components/IntentionMeter";
import { DeviceCard } from "./components/DeviceCard";
import {
  IconGaze,
  IconMuscle,
  IconPlay,
  IconRefresh,
  IconShieldCheck,
  IconShieldPause,
} from "./icons";

export default function App() {
  const [view, setView] = useState<ViewId>("home");
  const engine = useNeuroShift();

  return (
    <div className="app-shell">
      <Nav active={view} onChange={setView} connection={engine.connection} sessionState={engine.sessionState} />

      <main className="app-main">
        {view === "home" && <HomeView engine={engine} onOpenMonitor={() => setView("monitor")} />}
        {view === "monitor" && <MonitorView engine={engine} />}
        {view === "activity" && <ActivityView engine={engine} />}
        {view === "insights" && <InsightsView engine={engine} />}
        {view === "system" && <SystemView engine={engine} />}
      </main>

      <ToastStack toasts={engine.toasts} />
    </div>
  );
}

type Engine = ReturnType<typeof useNeuroShift>;

// ---------- Home ----------

function HomeView({ engine, onOpenMonitor }: { engine: Engine; onOpenMonitor: () => void }) {
  return (
    <div className="view view-home">
      <header className="page-header">
        <p className="page-eyebrow">Living room</p>
        <h1 className="principle">
          Looking selects. <span className="principle-dim">Muscle confirms.</span>{" "}
          <span className="principle-safe">Unsure → abstain.</span>
        </h1>
      </header>

      <IntentionMeter decision={engine.decision} settings={engine.settings} sessionState={engine.sessionState} />

      <div className="home-actions">
        {engine.sessionState === "idle" ? (
          <button
            type="button"
            className="btn btn-primary"
            onClick={async () => {
              await engine.startSession();
              onOpenMonitor();
            }}
          >
            <IconPlay aria-hidden="true" />
            Start live camera
          </button>
        ) : (
          <>
            <button type="button" className="btn btn-primary btn-running" disabled>
              <span className="pulse-dot" aria-hidden="true" />
              Camera session running
            </button>
            <button type="button" className="btn btn-primary" onClick={engine.confirmIntent}>
              Confirm (EMG)
            </button>
          </>
        )}
        <button type="button" className="btn btn-ghost" onClick={engine.clearSession}>
          Clear session
        </button>
      </div>

      <section className="devices-section">
        <div className="section-heading">
          <h2>Devices</h2>
          <span className="section-sub">
            {engine.sessionState === "running" && engine.liveTargets.length > 0
              ? `${engine.liveTargets.length} object(s) in view`
              : "Tap to override manually"}
          </span>
        </div>
        <div className="devices-grid">
          {engine.devices.map((d) => {
            const hit = engine.liveTargets.find((t) => t.id === d.id);
            return (
              <DeviceCard
                key={d.id}
                device={d}
                onToggle={engine.toggleDevice}
                highlight={hit?.selected ? "selected" : hit?.candidate ? "candidate" : null}
              />
            );
          })}
        </div>
        {engine.sessionState === "running" && engine.detectMode === "objects" && engine.liveTargets.length === 0 && (
          <p className="page-lede" style={{ marginTop: 12 }}>
            Tip: hold a phone, bottle, or cup clearly in frame — then look toward it until it turns green and press Confirm.
          </p>
        )}
      </section>
    </div>
  );
}

// ---------- Monitor ----------

function MonitorView({ engine }: { engine: Engine }) {
  const { decision, sessionState, previewTick, previewJpeg } = engine;
  const noise = useMemo(() => makeNoiseSeed(previewTick), [previewTick]);

  return (
    <div className="view view-monitor">
      <header className="page-header">
        <p className="page-eyebrow">Live pipeline</p>
        <h1>Monitor</h1>
        <p className="page-lede">
          A read-only preview of what the pipeline currently sees. Nothing here can be tapped to actuate a device —
          this view is for understanding, not control.
        </p>
      </header>

      <div className="preview-frame">
        <div className="preview-canvas" aria-hidden="true">
          {sessionState === "running" && previewJpeg ? (
            <img src={previewJpeg} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : sessionState === "running" ? (
            <svg viewBox="0 0 400 240" className="preview-svg">
              <rect x="0" y="0" width="400" height="240" fill="var(--surface-2)" />
              {noise.map((n, i) => (
                <rect key={i} x={n.x} y={n.y} width={n.w} height={n.h} fill="var(--border)" opacity={0.5} />
              ))}
              <circle
                cx={200 + decision.yaw * 120}
                cy="120"
                r={18 + decision.emg * 10}
                fill="none"
                stroke={decision.action === "ACT" ? "var(--act)" : decision.action === "ABSTAIN" ? "var(--abstain)" : "var(--idle)"}
                strokeWidth="2.5"
              />
              <circle cx={200 + decision.yaw * 120} cy="120" r="2.5" fill="currentColor" />
            </svg>
          ) : (
            <div className="preview-empty">
              <p>Preview is off</p>
              <span>Start a monitor session from Home to see the live gaze target and confirmation ring.</span>
            </div>
          )}
        </div>

        <div className="preview-readout">
          <div className="readout-item">
            <IconGaze aria-hidden="true" />
            <span className="readout-label">Yaw</span>
            <span className="readout-value">{decision.yaw.toFixed(2)}</span>
          </div>
          <div className="readout-item">
            <IconMuscle aria-hidden="true" />
            <span className="readout-label">EMG</span>
            <span className="readout-value">{decision.emg.toFixed(2)}</span>
          </div>
          <div className="readout-item">
            {decision.action === "ACT" ? (
              <IconShieldCheck aria-hidden="true" />
            ) : (
              <IconShieldPause aria-hidden="true" />
            )}
            <span className="readout-label">State</span>
            <span className="readout-value">{decision.action}</span>
          </div>
        </div>
      </div>

      <p className="preview-reason">{decision.reason}</p>

      {sessionState === "running" && engine.detectMode === "objects" && (
        <section className="devices-section" style={{ marginTop: 16 }}>
          <div className="section-heading">
            <h2>Seen now</h2>
            <span className="section-sub">
              {engine.liveTargets.length
                ? "Look until ready, then Confirm"
                : "Hold phone / bottle / cup in frame"}
            </span>
          </div>
          {engine.liveTargets.length > 0 ? (
            <ul className="seen-list">
              {engine.liveTargets.map((t) => (
                <li
                  key={t.id}
                  className={`seen-chip ${t.selected ? "is-selected" : t.candidate ? "is-candidate" : ""}`}
                >
                  {t.label}
                  <span>{t.conf.toFixed(2)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="page-lede">No COCO objects yet — bright light and a clear silhouette help YOLO.</p>
          )}
        </section>
      )}

      {sessionState === "running" && (
        <div className="home-actions" style={{ marginTop: 16 }}>
          <button type="button" className="btn btn-primary" onClick={engine.confirmIntent}>
            Confirm (muscle stand-in)
          </button>
          <button type="button" className="btn btn-ghost" onClick={engine.toggleDetectMode}>
            Mode: {engine.detectMode === "objects" ? "Objects" : "Slots"}
          </button>
          <button type="button" className="btn btn-ghost" onClick={engine.clearSession}>
            Stop camera
          </button>
        </div>
      )}
    </div>
  );
}

function makeNoiseSeed(tick: number) {
  const arr: { x: number; y: number; w: number; h: number }[] = [];
  const rand = mulberry32(tick);
  for (let i = 0; i < 5; i++) {
    arr.push({
      x: rand() * 360,
      y: rand() * 200,
      w: 10 + rand() * 30,
      h: 6 + rand() * 18,
    });
  }
  return arr;
}

function mulberry32(seed: number) {
  let a = seed + 0x6d2b79f5;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---------- Activity ----------

function ActivityView({ engine }: { engine: Engine }) {
  return (
    <div className="view view-activity">
      <header className="page-header">
        <p className="page-eyebrow">Timeline</p>
        <h1>Activity</h1>
        <p className="page-lede">Every decision the system made, in plain language, newest first.</p>
      </header>

      {engine.activity.length === 0 ? (
        <div className="empty-state">
          <p>No decisions yet</p>
          <span>Start a monitor session and each act or abstain will appear here as it happens.</span>
        </div>
      ) : (
        <ul className="timeline">
          {engine.activity.map((entry) => (
            <li key={entry.id} className={`timeline-item timeline-${entry.decision.action.toLowerCase()}`}>
              <div className="timeline-marker" aria-hidden="true">
                {entry.decision.action === "ACT" ? <IconShieldCheck /> : <IconShieldPause />}
              </div>
              <div className="timeline-body">
                <div className="timeline-top">
                  <span className="timeline-action">{entry.decision.action}</span>
                  {entry.decision.selected_label && (
                    <span className="timeline-target">{entry.decision.selected_label}</span>
                  )}
                  <span className="timeline-time">{formatTime(entry.timestamp)}</span>
                </div>
                <p className="timeline-reason">{entry.decision.reason}</p>
                <div className="timeline-metrics">
                  <span>yaw {entry.decision.yaw.toFixed(2)}</span>
                  <span>emg {entry.decision.emg.toFixed(2)}</span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// ---------- Insights ----------

function InsightsView({ engine }: { engine: Engine }) {
  const { stats, devices } = engine;
  const total = stats.acts + stats.abstains;
  const actShare = total > 0 ? stats.acts / total : 0;

  return (
    <div className="view view-insights">
      <header className="page-header">
        <p className="page-eyebrow">Session summary</p>
        <h1>Insights</h1>
        <p className="page-lede">
          A quick read on how often the system acted, how often it held back, and how safe those actions were.
        </p>
      </header>

      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-label">Acts</span>
          <span className="stat-value stat-act">{stats.acts}</span>
          <span className="stat-note">Confirmed and actuated</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Abstains</span>
          <span className="stat-value stat-abstain">{stats.abstains}</span>
          <span className="stat-note">Held back when unsure</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Device toggles</span>
          <span className="stat-value">{devices.reduce((sum, d) => sum + d.toggle_count, 0)}</span>
          <span className="stat-note">Includes manual overrides</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">FAR proxy</span>
          <span className="stat-value">{(stats.far_proxy * 100).toFixed(1)}%</span>
          <span className="stat-note">Estimated false-activation rate</span>
        </div>
      </div>

      <div className="ratio-card">
        <div className="ratio-header">
          <span>Act vs. abstain</span>
          <span>{total > 0 ? `${Math.round(actShare * 100)}% acted` : "No decisions yet"}</span>
        </div>
        <div className="ratio-bar">
          <div className="ratio-fill" style={{ width: `${actShare * 100}%` }} />
        </div>
      </div>

      <div className="explainer-card">
        <h3>What is FAR?</h3>
        <p>
          The false-activation rate is how often the system would have acted when it shouldn't have. NeuroShift
          estimates this proxy from abstained moments where the muscle signal looked confirmatory but the gaze
          target wasn't stable — the system errs toward refusing rather than guessing.
        </p>
      </div>
    </div>
  );
}

// ---------- System ----------

function SystemView({ engine }: { engine: Engine }) {
  const { settings, updateSettings } = engine;

  return (
    <div className="view view-system">
      <header className="page-header">
        <p className="page-eyebrow">Calibration</p>
        <h1>System</h1>
        <p className="page-lede">Tune how deliberate the system must be before it selects or confirms.</p>
      </header>

      <div className="settings-group">
        <h2 className="settings-group-title">Timing</h2>
        <SettingSlider
          label="Dwell time"
          hint="How long a gaze must hold on a target before it's considered selected."
          value={settings.dwell_seconds}
          min={0.4}
          max={3}
          step={0.1}
          unit="s"
          onChange={(v) => updateSettings({ dwell_seconds: v })}
        />
        <SettingSlider
          label="Act cooldown"
          hint="Minimum time between two actions, to prevent rapid re-triggering."
          value={settings.act_cooldown_seconds}
          min={0.5}
          max={6}
          step={0.5}
          unit="s"
          onChange={(v) => updateSettings({ act_cooldown_seconds: v })}
        />
      </div>

      <div className="settings-group">
        <h2 className="settings-group-title">Thresholds</h2>
        <SettingSlider
          label="Yaw side threshold"
          hint="How far off-center the gaze must turn before a device is considered targeted."
          value={settings.yaw_side_threshold}
          min={0.1}
          max={0.8}
          step={0.05}
          unit=""
          onChange={(v) => updateSettings({ yaw_side_threshold: v })}
        />
        <SettingSlider
          label="EMG confirm threshold"
          hint="Minimum muscle effort required to confirm an action."
          value={settings.emg_confirm_threshold}
          min={0.2}
          max={0.9}
          step={0.05}
          unit=""
          onChange={(v) => updateSettings({ emg_confirm_threshold: v })}
        />
      </div>

      <div className="settings-group">
        <h2 className="settings-group-title">Connections</h2>
        <div className="setting-field">
          <label htmlFor="mqtt">
            MQTT host
            <span className="setting-hint">Broker address for device actuation.</span>
          </label>
          <input
            id="mqtt"
            type="text"
            value={settings.mqtt_host}
            onChange={(e) => updateSettings({ mqtt_host: e.target.value })}
          />
        </div>
        <div className="setting-field">
          <label htmlFor="serial">
            EMG serial port
            <span className="setting-hint">Device path for the muscle-sensor reader.</span>
          </label>
          <input
            id="serial"
            type="text"
            value={settings.emg_serial_port}
            onChange={(e) => updateSettings({ emg_serial_port: e.target.value })}
          />
        </div>
      </div>

      <button
        type="button"
        className="btn btn-ghost settings-reset"
        onClick={() =>
          engine.updateSettings({
            dwell_seconds: 0.55,
            yaw_side_threshold: 0.2,
            emg_confirm_threshold: 0.5,
            act_cooldown_seconds: 0.7,
            mqtt_host: "127.0.0.1",
            emg_serial_port: "COM3",
          })
        }
      >
        <IconRefresh aria-hidden="true" />
        Restore defaults
      </button>
    </div>
  );
}

function SettingSlider({
  label,
  hint,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  label: string;
  hint: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="setting-field">
      <label>
        <span className="setting-label-row">
          {label}
          <span className="setting-value">
            {value.toFixed(2)}
            {unit}
          </span>
        </span>
        <span className="setting-hint">{hint}</span>
      </label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
    </div>
  );
}
