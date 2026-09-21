import { useEffect, useRef, useState, type CSSProperties } from "react";
import type { AccountUser } from "../../auth";
import { getServerBase, isAndroidApp, isNativeApp, isPhoneClient, probeServer, setServerBase } from "../../serverConfig";
import {
  calibrationQuality,
  formatCalibrated,
  isQuietHour,
  usePrefs,
  type BreakInterval,
  type TextSize,
} from "../../settings/prefs";
import {
  cameraState,
  isCalibrationComplete,
  isCalibrationFailure,
  lampDevice,
  laptopState,
  runDiagnostics,
  trackingLabel,
  wizardPhase,
  type DiagnosticCheck,
} from "../../settings/tracking";
import { APP_NAME, APP_VERSION } from "../../settings/version";
import type { NeuroShiftEngine } from "../../useNeuroShift";
import {
  ConfirmModal,
  SettingsRow,
  SettingsSection,
  SettingsSelect,
  SettingsToggle,
  SoonRow,
  StatusBadge,
} from "./ui";

export function DevicePanel({ engine, onOpenLive }: { engine: NeuroShiftEngine; onOpenLive: () => void }) {
  const laptop = laptopState(engine);
  const camera = cameraState(engine);
  const device = lampDevice(engine);
  const running = engine.sessionState === "running";
  const [serverInput, setServerInput] = useState(getServerBase());
  const [serverStatus, setServerStatus] = useState<{ ok: boolean; message: string } | null>(null);
  const [probing, setProbing] = useState(false);
  const [mqtt, setMqtt] = useState(engine.settings.mqtt_host);
  const mqttTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => setMqtt(engine.settings.mqtt_host), [engine.settings.mqtt_host]);

  function queueMqtt(next: string) {
    setMqtt(next);
    if (mqttTimer.current) clearTimeout(mqttTimer.current);
    mqttTimer.current = setTimeout(() => engine.updateSettings({ mqtt_host: next }), 400);
  }

  return (
    <>
      <SettingsSection label="Laptop">
        <SettingsRow
          label="Connection"
          hint={laptop === "connected" ? "This phone is talking to the laptop." : laptop === "reconnecting" ? "Trying the laptop again." : "The laptop is not reachable."}
          trailing={
            <StatusBadge tone={laptop === "connected" ? "ok" : laptop === "reconnecting" ? "busy" : "off"}>
              {laptop === "connected" ? "Online" : laptop === "reconnecting" ? "Reconnecting" : "Offline"}
            </StatusBadge>
          }
        />
        <SettingsRow
          label="Camera"
          hint={camera === "on" ? "Live session is running." : camera === "idle" ? "Start Live to watch the room." : "Laptop is offline."}
          trailing={
            <StatusBadge tone={camera === "on" ? "ok" : camera === "idle" ? "warn" : "off"}>
              {camera === "on" ? "On" : camera === "idle" ? "Idle" : "Offline"}
            </StatusBadge>
          }
        />
      </SettingsSection>

      {device ? (
        <SettingsSection label="Lamp">
          <SettingsToggle
            label="Lamp"
            hint={!engine.connection || engine.connection === "offline" ? "Hub offline" : device.is_on ? "On — tap to override" : "Off — tap to override"}
            checked={device.is_on}
            disabled={engine.connection !== "connected"}
            onChange={() => void engine.toggleDevice(device.id)}
          />
        </SettingsSection>
      ) : null}

      <div className="btnrow">
        {running ? (
          <button type="button" className="btn" onClick={() => void engine.pauseSession()}>
            Pause camera
          </button>
        ) : (
          <button type="button" className="btn primary" onClick={onOpenLive} disabled={laptop === "offline"}>
            Open Live
          </button>
        )}
        <button
          type="button"
          className="btn"
          disabled={laptop === "connected"}
          onClick={() => window.location.reload()}
        >
          Reconnect
        </button>
      </div>
      <p className="note">Reconnect reloads this app so it can try the laptop again. Pause camera stops the live session. It does not unpair a headset — there is no wearable in Phase 1.</p>

      <SettingsSection label="Laptop connection">
        <label className="st-field">
          <span>Server address</span>
          <input
            className="text-input"
            value={serverInput}
            placeholder="192.168.1.5:8000"
            autoCapitalize="off"
            autoCorrect="off"
            onChange={(e) => setServerInput(e.target.value)}
          />
          <em>
            {isAndroidApp()
              ? "Laptop IPv4 and port 8000. HTTP only."
              : isNativeApp()
                ? "Laptop IPv4 and port 8000."
                : "Leave blank to use this same origin. Set it only on a phone install."}
          </em>
        </label>
        {serverStatus ? (
          <p className="st-probe" data-ok={serverStatus.ok}>
            {serverStatus.message}
          </p>
        ) : null}
        <div className="btnrow tight">
          <button
            type="button"
            className="btn"
            disabled={probing}
            onClick={async () => {
              setProbing(true);
              setServerStatus(await probeServer(serverInput));
              setProbing(false);
            }}
          >
            {probing ? "Checking…" : "Test connection"}
          </button>
          <button
            type="button"
            className="btn primary"
            onClick={() => {
              setServerBase(serverInput);
              window.location.reload();
            }}
          >
            Save &amp; reload
          </button>
        </div>
      </SettingsSection>

      <SettingsSection label="Camera source">
        <SettingsToggle
          label="This phone / this browser"
          hint={
            engine.cameraSource === "remote"
              ? "Next Start uses this device’s camera. Point it at the lamp."
              : "Live uses the laptop webcam. This phone is only the control screen."
          }
          checked={engine.cameraSource === "remote"}
          onChange={() => engine.updateCameraPref(engine.cameraSource === "remote" ? "local" : "remote")}
        />
        {!isNativeApp() && engine.phoneNeedsHttps ? (
          <p className="note">
            iPhone Safari needs the certificate page. Open <a href={engine.iphoneSetup}>iPhone setup</a>, then use HTTPS.
          </p>
        ) : null}
      </SettingsSection>

      <SettingsSection label="Lamp hub">
        <label className="st-field">
          <span>MQTT host</span>
          <input className="text-input" value={mqtt} onChange={(e) => queueMqtt(e.target.value)} />
          <em>Where this laptop talks to the lamp relay. Leave it unless the hub moved.</em>
        </label>
      </SettingsSection>

      {!isNativeApp() && !isPhoneClient() ? (
        <SettingsSection label="Install">
          <a className="st-row" href={engine.iphoneSetupLan || engine.iphoneSetup}>
            <span className="st-row-copy">
              <strong>iPhone setup</strong>
              <span>Install the profile, then open HTTPS.</span>
            </span>
            <span className="chev">›</span>
          </a>
          {engine.androidApkUrl ? (
            <a className="st-row" href={engine.androidApkUrl}>
              <span className="st-row-copy">
                <strong>Android APK</strong>
                <span>Download, then pair this laptop on port 8000.</span>
              </span>
              <span className="chev">›</span>
            </a>
          ) : (
            <SettingsRow label="Android APK" hint="Not built yet." />
          )}
        </SettingsSection>
      ) : null}
    </>
  );
}

export function CalibrationPanel({ engine }: { engine: NeuroShiftEngine }) {
  const { prefs, patchPrefs } = usePrefs();
  const phase = wizardPhase(engine);
  const reason = (engine.decision.reason || "").trim();
  const running = engine.sessionState === "running";
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const seenComplete = useRef("");

  useEffect(() => {
    if (isCalibrationComplete(reason) && seenComplete.current !== reason) {
      seenComplete.current = reason;
      patchPrefs({ lastCalibratedAt: Date.now() });
    }
  }, [reason, patchPrefs]);

  async function recalibrate() {
    setError("");
    setBusy(true);
    const result = await engine.calibrateGaze();
    setBusy(false);
    if (result && result.ok === false) setError(result.message);
  }

  const quality = calibrationQuality(prefs.lastCalibratedAt);
  const stepLabel =
    phase === "center" ? "Step 1 — look at the camera" : phase === "lamp" || phase === "face" ? "Step 2 — look at the lamp" : null;

  return (
    <>
      <p className="note">Calibration helps MyoGaze understand where you are looking in this room. Look at the laptop camera, then at the real lamp — not this screen.</p>
      <SettingsSection>
        <SettingsRow label="Status" trailing={<StatusBadge tone={quality === "Calibrated" ? "ok" : "warn"}>{quality}</StatusBadge>} />
        <SettingsRow label="Last calibrated" hint={formatCalibrated(prefs.lastCalibratedAt)} />
      </SettingsSection>

      {!running ? (
        <div className="empty-card">
          <strong>Start Live first</strong>
          <span>The laptop camera has to be on before calibration can run.</span>
        </div>
      ) : (
        <div className="st-wizard">
          {stepLabel ? <p className="st-wizard-step">{stepLabel}</p> : null}
          <strong>
            {phase === "timeout"
              ? "Calibration timed out"
              : phase === "done"
                ? "Calibration saved"
                : phase === "face"
                  ? "Face the camera"
                  : phase === "center"
                    ? "Look at the camera"
                    : phase === "lamp"
                      ? "Look at the lamp"
                      : "Ready to calibrate"}
          </strong>
          <span>
            {phase === "done"
              ? reason
              : phase === "timeout"
                ? reason
                : phase === "ready"
                  ? "Keep your head still. Recalibrate, then look at the camera."
                  : reason || "Keep your head still."}
          </span>
        </div>
      )}

      {error ? <p className="st-probe" data-ok={false}>{error}</p> : null}
      {isCalibrationFailure(reason) ? <p className="st-probe" data-ok={false}>{reason}</p> : null}

      <div className="btnrow">
        <button type="button" className="btn primary" disabled={!running || busy} onClick={() => void recalibrate()}>
          {busy ? "Starting…" : "Recalibrate"}
        </button>
      </div>
    </>
  );
}

export function TrackingPanel({ engine, onOpenLive }: { engine: NeuroShiftEngine; onOpenLive: () => void }) {
  const { prefs } = usePrefs();
  const label = trackingLabel(engine, prefs.lastCalibratedAt);
  const running = engine.sessionState === "running";
  const laptop = laptopState(engine);
  const [yaw, setYaw] = useState(engine.settings.yaw_side_threshold);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => setYaw(engine.settings.yaw_side_threshold), [engine.settings.yaw_side_threshold]);

  function queueYaw(next: number) {
    setYaw(next);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => engine.updateSettings({ yaw_side_threshold: next }), 400);
  }

  return (
    <>
      <SettingsSection>
        <SettingsRow
          label="Eye tracking"
          hint={label === "Active" ? "Session running on the laptop camera." : label === "Idle" ? "Camera is idle." : label === "Offline" ? "Laptop is offline." : "Calibrate so gaze matches this room."}
          trailing={<StatusBadge tone={label === "Active" ? "ok" : label === "Idle" ? "warn" : "off"}>{label}</StatusBadge>}
        />
        <SettingsRow label="Laptop" hint={laptop === "connected" ? "Online" : laptop === "reconnecting" ? "Reconnecting" : "Offline"} />
        <SettingsRow label="Last calibration" hint={formatCalibrated(prefs.lastCalibratedAt)} />
      </SettingsSection>
      <SettingsToggle
        label="Tracking"
        hint="Starts or pauses the live camera session."
        checked={running}
        disabled={laptop === "offline" && !running}
        onChange={(on) => {
          if (on) onOpenLive();
          else void engine.pauseSession();
        }}
      />
      <SettingsSection label="Sensitivity">
        <label className="st-field">
          <span>Look-left / look-right</span>
          <input
            type="range"
            min={0.1}
            max={0.8}
            step={0.05}
            value={yaw}
            onChange={(e) => queueYaw(Number(e.target.value))}
          />
          <em>Lower is easier to lock. Current {yaw.toFixed(2)}. This writes the existing yaw setting.</em>
        </label>
      </SettingsSection>
    </>
  );
}

const HOLD_PRESETS = [1, 1.5, 2, 2.5, 3];

export function LookHoldPanel({ engine }: { engine: NeuroShiftEngine }) {
  const { prefs, patchPrefs } = usePrefs();
  const [seconds, setSeconds] = useState(engine.settings.dwell_seconds);
  const [cooldown, setCooldown] = useState(engine.settings.act_cooldown_seconds);
  const [preview, setPreview] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const coolTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const raf = useRef<number>(0);

  useEffect(() => {
    setSeconds(engine.settings.dwell_seconds);
    setCooldown(engine.settings.act_cooldown_seconds);
  }, [engine.settings.dwell_seconds, engine.settings.act_cooldown_seconds]);

  function queueDwell(next: number) {
    setSeconds(next);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => engine.updateSettings({ dwell_seconds: next }), 400);
  }

  function queueCooldown(next: number) {
    setCooldown(next);
    if (coolTimer.current) clearTimeout(coolTimer.current);
    coolTimer.current = setTimeout(() => engine.updateSettings({ act_cooldown_seconds: next }), 400);
  }

  function playPreview() {
    cancelAnimationFrame(raf.current);
    const start = performance.now();
    const duration = Math.max(0.2, seconds) * 1000;
    const tick = (now: number) => {
      const pct = Math.min(100, ((now - start) / duration) * 100);
      setPreview(pct);
      if (pct < 100) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
  }

  useEffect(() => () => cancelAnimationFrame(raf.current), []);

  return (
    <>
      <p className="note">Look at an item for the selected duration to activate it. This is the same look-and-hold the lamp uses.</p>
      <SettingsToggle
        label="Look and hold"
        hint="On: you must keep looking until the hold fills. Off: comparison mode on the laptop."
        checked={engine.dwellRequired}
        onChange={() => void engine.toggleDwellMode()}
      />
      <SettingsSection label="Hold duration">
        <div className="st-presets">
          {HOLD_PRESETS.map((value) => (
            <button
              key={value}
              type="button"
              className={Math.abs(seconds - value) < 0.05 ? "chip active" : "chip"}
              onClick={() => queueDwell(value)}
            >
              {value.toFixed(1)}s
            </button>
          ))}
        </div>
        <label className="st-field">
          <span>Fine adjust</span>
          <input type="range" min={0.4} max={3} step={0.1} value={seconds} onChange={(e) => queueDwell(Number(e.target.value))} />
          <em>{seconds.toFixed(1)} seconds. Saved to the laptop.</em>
        </label>
        <label className="st-field">
          <span>Pause after a toggle</span>
          <input type="range" min={0.5} max={6} step={0.5} value={cooldown} onChange={(e) => queueCooldown(Number(e.target.value))} />
          <em>{cooldown.toFixed(1)}s quiet time so one long look does not fire twice.</em>
        </label>
      </SettingsSection>
      <SettingsSection label="Preview">
        <div className="st-preview">
          <div className="ring" style={{ "--pct": preview } as CSSProperties} aria-hidden />
          <div>
            <strong>Timing only</strong>
            <span>This ring fills for {seconds.toFixed(1)}s. It does not toggle the lamp.</span>
          </div>
        </div>
        <button type="button" className="btn" onClick={playPreview}>
          Preview hold
        </button>
      </SettingsSection>
      <SettingsToggle
        label="Visual feedback"
        hint="Show the look-and-hold ring in Live."
        checked={prefs.accessibility.visualFeedback}
        onChange={(on) => patchPrefs({ accessibility: { ...prefs.accessibility, visualFeedback: on } })}
      />
      <SettingsToggle
        label="Sound feedback"
        hint="Play a short click on this phone when a look toggles. It is not a muscle sensor."
        checked={prefs.accessibility.audioFeedback}
        onChange={(on) => patchPrefs({ accessibility: { ...prefs.accessibility, audioFeedback: on } })}
      />
    </>
  );
}

export function WellnessPanel() {
  const { prefs, patchPrefs } = usePrefs();
  const quietNow = isQuietHour(new Date(), prefs);
  return (
    <>
      <p className="note">Break reminders live on this phone while the app is open. They are not a medical reading from the camera.</p>
      <SettingsToggle
        label="Break reminders"
        hint={quietNow && prefs.quietHours.enabled ? "Quiet hours are on — reminders are paused." : "A rest reminder after the interval you pick."}
        checked={prefs.breaks.enabled}
        onChange={(on) => patchPrefs({ breaks: { ...prefs.breaks, enabled: on } })}
      />
      <SettingsSelect
        label="Interval"
        value={prefs.breaks.intervalMin}
        options={[
          { value: 20, label: "20 min" },
          { value: 30, label: "30 min" },
          { value: 45, label: "45 min" },
          { value: 60, label: "60 min" },
        ]}
        onChange={(value) => patchPrefs({ breaks: { ...prefs.breaks, intervalMin: value as BreakInterval } })}
      />
      <SettingsToggle
        label="Quiet hours"
        hint="No break reminders in this window."
        checked={prefs.quietHours.enabled}
        onChange={(on) => patchPrefs({ quietHours: { ...prefs.quietHours, enabled: on } })}
      />
      <label className="st-field">
        <span>Starts</span>
        <input
          className="text-input"
          type="time"
          value={prefs.quietHours.start}
          onChange={(e) => patchPrefs({ quietHours: { ...prefs.quietHours, start: e.target.value } })}
        />
      </label>
      <label className="st-field">
        <span>Ends</span>
        <input
          className="text-input"
          type="time"
          value={prefs.quietHours.end}
          onChange={(e) => patchPrefs({ quietHours: { ...prefs.quietHours, end: e.target.value } })}
        />
      </label>
      <SoonRow label="Eye fatigue monitoring" hint="The camera does not score fatigue yet." />
      <SoonRow label="Smart wellness insights" hint="No camera-based wellness model in Phase 1." />
    </>
  );
}

export function NotificationsPanel() {
  const { prefs, patchPrefs } = usePrefs();
  const n = prefs.notifications;
  return (
    <>
      <p className="note">These control alerts on this phone. There is no push inbox.</p>
      <SettingsToggle
        label="Eye break reminders"
        checked={n.breakReminders}
        onChange={(on) => patchPrefs({ notifications: { ...n, breakReminders: on } })}
      />
      <SettingsToggle
        label="Calibration alerts"
        checked={n.calibration}
        onChange={(on) => patchPrefs({ notifications: { ...n, calibration: on } })}
      />
      <SettingsToggle
        label="Laptop disconnected"
        checked={n.laptopDisconnected}
        onChange={(on) => patchPrefs({ notifications: { ...n, laptopDisconnected: on } })}
      />
      <SettingsToggle
        label="Daily eye summary"
        hint="A once-a-day note from time already tracked on Home."
        checked={n.dailySummary}
        onChange={(on) => patchPrefs({ notifications: { ...n, dailySummary: on } })}
      />
      <SoonRow label="Wellness insights" hint="No wellness model yet." />
    </>
  );
}

export function AccessibilityPanel({ engine }: { engine: NeuroShiftEngine }) {
  const { prefs, patchPrefs } = usePrefs();
  const a = prefs.accessibility;
  return (
    <>
      <SettingsSelect
        label="Text size"
        value={a.textSize}
        options={[
          { value: "normal", label: "Normal" },
          { value: "large", label: "Large" },
          { value: "xl", label: "Extra large" },
        ]}
        onChange={(value) => patchPrefs({ accessibility: { ...a, textSize: value as TextSize } })}
      />
      <SettingsToggle
        label="High contrast"
        checked={a.highContrast}
        onChange={(on) => patchPrefs({ accessibility: { ...a, highContrast: on } })}
      />
      <SettingsToggle
        label="Reduce motion"
        checked={a.reduceMotion}
        onChange={(on) => patchPrefs({ accessibility: { ...a, reduceMotion: on } })}
      />
      <SettingsRow label="Look and hold duration" hint={`${engine.settings.dwell_seconds.toFixed(1)}s — change it under Look & hold.`} />
      <SettingsToggle
        label="Visual feedback"
        checked={a.visualFeedback}
        onChange={(on) => patchPrefs({ accessibility: { ...a, visualFeedback: on } })}
      />
      <SettingsToggle
        label="Audio feedback"
        checked={a.audioFeedback}
        onChange={(on) => patchPrefs({ accessibility: { ...a, audioFeedback: on } })}
      />
    </>
  );
}

export function AppearancePanel() {
  return (
    <p className="note">
      Home, Live, Activity, and Settings stay on paper. Harbor is the active color. High contrast and text size live under Accessibility.
    </p>
  );
}

export function RecordsPanel() {
  return (
    <>
      <p className="note">Clear language for what this laptop keeps. Camera frames are used for tracking and are not stored as a photo album.</p>
      <SettingsSection>
        <SettingsRow label="Eye gaze measurements" hint="Look direction used to pick the lamp." />
        <SettingsRow label="Tracking sessions" hint="When Live is running, and how long." />
        <SettingsRow label="Lamp commands" hint="On/off toggles sent to the hub." />
        <SettingsRow label="Calibration" hint="Look templates for this room, kept in the live session." />
        <SettingsRow label="Activity list" hint="Looks, toggles, and unsure events shown on this phone." />
      </SettingsSection>
      <SoonRow label="Blink information" hint="No blink detector in Phase 1." />
      <SoonRow label="Wellness reports" hint="Break reminders are local only." />
    </>
  );
}

export function PermissionsPanel() {
  return (
    <p className="note">
      This phone may use the camera only if you switch “This phone / this browser” on under Laptop &amp; camera. The laptop webcam is
      the default. MyoGaze does not send gaze data to a cloud account in this build.
    </p>
  );
}

export function ExportPanel({ engine }: { engine: NeuroShiftEngine }) {
  const [confirm, setConfirm] = useState(false);
  return (
    <>
      <p className="note">
        Export the look history stored on this laptop. Clearing this session stops tracking and removes the activity list on this
        phone. It does not delete the account.
      </p>
      <div className="btnrow">
        <button type="button" className="btn" onClick={() => engine.exportReport()}>
          Report
        </button>
        <button type="button" className="btn" onClick={() => engine.exportTrials("csv")}>
          CSV
        </button>
      </div>
      <div className="btnrow tight">
        <button type="button" className="btn" onClick={() => engine.exportTrials("json")}>
          JSON
        </button>
        <button type="button" className="btn" disabled>
          PDF — Coming soon
        </button>
      </div>
      <button type="button" className="btn warn" onClick={() => setConfirm(true)}>
        Clear this session
      </button>
      {confirm ? (
        <ConfirmModal
          title="Clear this session?"
          body="Tracking stops and the activity list on this phone is removed. The account stays."
          confirmLabel="Clear session"
          danger
          onCancel={() => setConfirm(false)}
          onConfirm={() => {
            setConfirm(false);
            void engine.clearSession();
          }}
        />
      ) : null}
    </>
  );
}

export function PrivacyPanel() {
  return (
    <p className="note">
      Gaze, lamp commands, and account sign-in stay on this laptop. There is no separate privacy-policy host in this build. Camera
      frames are not kept as an album. Export and session clear are under Data.
    </p>
  );
}

export function HelpPanel() {
  return (
    <p className="note">
      Open Live. Point the laptop camera at the lamp. Look at the lamp for two seconds — that toggles it. Unsure means MyoGaze
      waited. Recalibrate if looks miss. Pause camera from Live or Laptop &amp; camera when you are done.
    </p>
  );
}

export function GettingStartedPanel() {
  return (
    <>
      <p className="note">1. Keep the laptop and this phone on the same Wi-Fi.</p>
      <p className="note">2. Open Live so the camera starts.</p>
      <p className="note">3. Recalibrate: look at the camera, then at the real lamp.</p>
      <p className="note">4. Hold your gaze on the lamp for two seconds to toggle it.</p>
    </>
  );
}

export function TroubleshootPanel() {
  return (
    <>
      <SettingsRow label="Laptop offline" hint="Same Wi-Fi. Test connection under Laptop & camera. Then Reconnect." />
      <SettingsRow label="Camera idle" hint="Open Live. Allow the camera if the browser asks." />
      <SettingsRow label="Lamp does not switch" hint="Confirm the hub is powered. Override the lamp switch, then try a two-second look." />
      <SettingsRow label="Looks miss" hint="Recalibrate. Face the camera. Look at the lamp in the room, not this screen." />
    </>
  );
}

export function ContactPanel() {
  return <p className="note">This laptop build has no support inbox. Use Report a problem to copy diagnostics.</p>;
}

export function ReportPanel({ engine }: { engine: NeuroShiftEngine }) {
  const { prefs } = usePrefs();
  const [category, setCategory] = useState("tracking");
  const [description, setDescription] = useState("");
  const [copied, setCopied] = useState(false);
  const [lastTick] = useLastTick(engine);

  async function copyDump() {
    const checks = runDiagnostics(engine, prefs.lastCalibratedAt, lastTick);
    const dump = [
      `${APP_NAME} ${APP_VERSION}`,
      `Category: ${category}`,
      description.trim() || "(no description)",
      "",
      ...checks.map((item) => `${item.ok ? "OK" : "FAIL"} ${item.label}: ${item.detail}`),
      `Laptop: ${engine.connection}`,
      `Session: ${engine.sessionState}`,
      `Dwell: ${engine.settings.dwell_seconds}s`,
    ].join("\n");
    try {
      await navigator.clipboard.writeText(dump);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <>
      <p className="note">There is no ticket inbox. Copy diagnostics and send them yourself.</p>
      <SettingsSelect
        label="Problem category"
        value={category}
        options={[
          { value: "tracking", label: "Eye tracking" },
          { value: "calibration", label: "Calibration" },
          { value: "lamp", label: "Lamp" },
          { value: "connection", label: "Laptop connection" },
          { value: "other", label: "Other" },
        ]}
        onChange={setCategory}
      />
      <label className="st-field">
        <span>Description</span>
        <textarea className="text-input st-area" rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <button type="button" className="btn primary" onClick={() => void copyDump()}>
        Copy diagnostic notes
      </button>
      {copied ? <p className="st-probe" data-ok>Copied. Not submitted anywhere.</p> : null}
    </>
  );
}

function useLastTick(engine: NeuroShiftEngine) {
  const [lastTick, setLastTick] = useState<number | null>(null);
  useEffect(() => {
    if (engine.previewTick || engine.previewJpeg) setLastTick(Date.now());
  }, [engine.previewTick, engine.previewJpeg]);
  return [lastTick] as const;
}

export function DiagnosticsPanel({ engine }: { engine: NeuroShiftEngine }) {
  const { prefs } = usePrefs();
  const [lastTick] = useLastTick(engine);
  const [running, setRunning] = useState(false);
  const [step, setStep] = useState("");
  const [results, setResults] = useState<DiagnosticCheck[] | null>(null);

  async function run() {
    setRunning(true);
    setResults(null);
    const labels = ["Checking laptop", "Checking camera", "Checking calibration", "Checking lamp", "Checking sync"];
    for (const label of labels) {
      setStep(label);
      await new Promise((resolve) => window.setTimeout(resolve, 280));
    }
    setResults(runDiagnostics(engine, prefs.lastCalibratedAt, lastTick));
    setRunning(false);
    setStep("");
  }

  return (
    <>
      <p className="note">Checks this phone can actually make: laptop link, camera session, saved calibration, lamp in the device list, data arriving.</p>
      {running ? (
        <div className="empty-card">
          <strong>Running diagnostics…</strong>
          <span>{step}</span>
        </div>
      ) : null}
      {results ? (
        <SettingsSection>
          {results.map((item) => (
            <SettingsRow
              key={item.id}
              label={item.label}
              hint={item.detail}
              trailing={<StatusBadge tone={item.ok ? "ok" : "off"}>{item.ok ? "Working" : "Needs attention"}</StatusBadge>}
            />
          ))}
        </SettingsSection>
      ) : null}
      <button type="button" className="btn primary" disabled={running} onClick={() => void run()}>
        Run diagnostics
      </button>
    </>
  );
}

export function AboutPanel() {
  return (
    <>
      <SettingsSection>
        <SettingsRow label={APP_NAME} hint={`Version ${APP_VERSION}`} />
        <SettingsRow label="Phase 1" hint="Laptop camera, look-and-hold, lamp. No wearable firmware in this build." />
      </SettingsSection>
      <SettingsRow label="Terms of Service" hint="Use on your own laptop and room. No cloud terms host in this build." />
      <SettingsRow label="Privacy Policy" hint="See Data & privacy. Gaze stays on this laptop." />
      <SettingsRow label="Open source licenses" hint="React, Vite, and the Python stack listed in the repository." />
    </>
  );
}

export function OwnerPanel({ account }: { account: AccountUser }) {
  return (
    <p className="note">
      {account.name} owns this laptop. Signed in as {account.identifier}. Family invites are not on this device yet.
    </p>
  );
}

export function TermsPanel() {
  return (
    <p className="note">
      MyoGaze Phase 1 is a local laptop camera product. Look at the lamp for two seconds to toggle it. There is no separate terms
      website in this build.
    </p>
  );
}
