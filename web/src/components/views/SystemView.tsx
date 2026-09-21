import { useEffect, useRef, useState, type CSSProperties } from "react";
import type { NeuroShiftEngine } from "../../useNeuroShift";
import type { Settings } from "../../types";
import { getServerBase, isAndroidApp, isNativeApp, isPhoneClient, probeServer, setServerBase } from "../../serverConfig";
import { ResetIcon } from "../../icons";

export type SystemSection = "all" | "sensitivity" | "pair" | "calibration";

interface SystemViewProps {
  engine: NeuroShiftEngine;
  account?: { identifier: string; name: string };
  onSignOut?: () => void;
  section?: SystemSection;
}

const DEFAULTS: Pick<
  Settings,
  "dwell_seconds" | "act_cooldown_seconds" | "yaw_side_threshold" | "emg_confirm_threshold"
> = {
  dwell_seconds: 2.0,
  act_cooldown_seconds: 0.7,
  yaw_side_threshold: 0.2,
  emg_confirm_threshold: 0.5,
};

const SLIDERS: {
  key: Exclude<keyof typeof DEFAULTS, "emg_confirm_threshold">;
  label: string;
  min: number;
  max: number;
  step: number;
  unit: string;
  hint: string;
}[] = [
  {
    key: "dwell_seconds",
    label: "Look-and-hold time",
    min: 0.4,
    max: 3,
    step: 0.1,
    unit: "s",
    hint: "How long you must keep looking at the lamp before it turns on or off.",
  },
  {
    key: "act_cooldown_seconds",
    label: "Pause after a toggle",
    min: 0.5,
    max: 6,
    step: 0.5,
    unit: "s",
    hint: "Quiet time after a toggle so one long look does not fire twice.",
  },
  {
    key: "yaw_side_threshold",
    label: "Look-left / look-right sensitivity",
    min: 0.1,
    max: 0.8,
    step: 0.05,
    unit: "",
    hint: "Lower is easier to lock. Raise it if the wrong object keeps winning.",
  },
];

export function SystemView({ engine, account, onSignOut, section = "all" }: SystemViewProps) {
  const showAccount = section === "all";
  const showSensitivity = section === "all" || section === "sensitivity";
  const showPair = section === "all" || section === "pair";
  const showCalibration = section === "all" || section === "calibration";
  const [local, setLocal] = useState(engine.settings);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [serverInput, setServerInput] = useState(getServerBase());
  const [serverStatus, setServerStatus] = useState<{ ok: boolean; message: string } | null>(null);
  const [probing, setProbing] = useState(false);
  const lamps = engine.devices.filter((device) => /lamp|bulb|light/i.test(`${device.id} ${device.label}`));
  const pairDevices = lamps.length ? lamps : engine.devices.slice(0, 1);

  async function handleTestServer() {
    setProbing(true);
    setServerStatus(await probeServer(serverInput));
    setProbing(false);
  }

  function handleSaveServer() {
    setServerBase(serverInput);
    window.location.reload();
  }

  useEffect(() => {
    setLocal(engine.settings);
  }, [engine.settings]);

  function queueSave(next: Partial<Settings>) {
    setLocal((prev) => ({ ...prev, ...next }));
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      engine.updateSettings(next);
    }, 400);
  }

  function handleRestoreDefaults() {
    const next = {
      ...DEFAULTS,
      mqtt_host: "127.0.0.1",
      emg_serial_port: "COM3",
    };
    setLocal((prev) => ({ ...prev, ...next }));
    engine.updateSettings(next);
  }

  function trackStyle(value: number, min: number, max: number): CSSProperties {
    const pct = ((value - min) / (max - min)) * 100;
    return {
      background: `linear-gradient(to right, var(--accent) 0%, var(--accent) ${pct}%, var(--border-strong) ${pct}%, var(--border-strong) 100%)`,
    };
  }

  return (
    <div className="stack">
      {showCalibration && section !== "all" && (
        <div className="panel">
          <div className="panel__title">Calibration</div>
          <p className="field__hint">Look at the camera, then recalibrate so gaze lock matches this room.</p>
          <button type="button" className="btn btn--primary" onClick={() => engine.calibrateGaze()}>
            Recalibrate
          </button>
        </div>
      )}
      {showPair && (
        <div className="panel">
          <div className="panel__title">Lamp</div>
          <div className="stack">
            {pairDevices.map((device) => (
              <div className="toggle-row" key={device.id} style={{ borderTop: "none", paddingTop: 0 }}>
                <div>
                  <div className="field__label">{device.label === "lamp" ? "Lamp" : device.label}</div>
                  <div className="field__hint">{device.is_on ? "On" : "Off"} — tap to override.</div>
                </div>
                <button
                  type="button"
                  className="switch"
                  role="switch"
                  aria-checked={device.is_on}
                  aria-label={`Turn ${device.label} ${device.is_on ? "off" : "on"}`}
                  onClick={() => engine.toggleDevice(device.id)}
                />
              </div>
            ))}
          </div>
        </div>
      )}
      {showAccount && account && onSignOut && (
        <button type="button" className="list-row list-card" onClick={onSignOut}>
          <span className="list-row__main">
            <span className="list-row__title">{account.name}</span>
            <span className="list-row__sub">{account.identifier}</span>
          </span>
          <span className="list-row__chev">Sign out</span>
        </button>
      )}
      {showPair && (
      <div className="session-card">
        <div>
          <div className="session-card__k">Laptop</div>
          <div className="session-card__v">{engine.connection === "connected" ? "Online" : "Offline"}</div>
        </div>
      </div>
      )}

      {showPair && !isNativeApp() && !isPhoneClient() && (
        <div className="list-card">
          <a className="list-row" href={engine.iphoneSetupLan || engine.iphoneSetup}>
            <span className="list-row__main">
              <span className="list-row__title">iPhone setup</span>
              <span className="list-row__sub">Install the profile, then open HTTPS. Do not tap Visit Website.</span>
            </span>
            <span className="list-row__chev" aria-hidden="true">›</span>
          </a>
          {engine.androidApkUrl ? (
            <a className="list-row" href={engine.androidApkUrl}>
              <span className="list-row__main">
                <span className="list-row__title">Android APK</span>
                <span className="list-row__sub">Download, then pair this laptop on port 8000.</span>
              </span>
              <span className="list-row__chev" aria-hidden="true">›</span>
            </a>
          ) : (
            <div className="list-row">
              <span className="list-row__main">
                <span className="list-row__title">Android APK</span>
                <span className="list-row__sub">Not built yet.</span>
              </span>
            </div>
          )}
        </div>
      )}

      {showSensitivity && (
      <div className="panel">
        <div className="panel__title">Look-and-hold</div>
        <div className="stack">
          {SLIDERS.map((s) => (
            <div className="field" key={s.key}>
              <div className="field__label-row">
                <label className="field__label" htmlFor={s.key}>
                  {s.label}
                </label>
                <span className="field__value">
                  {local[s.key].toFixed(s.step < 1 ? 2 : 0)}
                  {s.unit}
                </span>
              </div>
              <input
                id={s.key}
                type="range"
                min={s.min}
                max={s.max}
                step={s.step}
                value={local[s.key]}
                style={trackStyle(local[s.key], s.min, s.max)}
                onChange={(e) => queueSave({ [s.key]: Number(e.target.value) } as Partial<Settings>)}
              />
              <span className="field__hint">{s.hint}</span>
            </div>
          ))}
        </div>
      </div>
      )}

      {showPair && (
      <>
      <div className="panel">
        <div className="panel__title">Laptop connection</div>
        <div className="stack">
          <div className="field">
            <label className="field__label" htmlFor="server_base">
              Server address
            </label>
            <input
              id="server_base"
              type="text"
              className="text-input"
              inputMode="url"
              autoCapitalize="off"
              autoCorrect="off"
              placeholder="192.168.1.5:8000"
              value={serverInput}
              onChange={(e) => setServerInput(e.target.value)}
            />
            <span className="field__hint">
              {isAndroidApp()
                ? "Laptop IPv4 and port 8000, for example 192.168.1.5:8000. HTTP only — allow Camera, and allow Install unknown apps if you downloaded the APK."
                : isNativeApp()
                  ? "Laptop IPv4 and port 8000, for example 192.168.1.5:8000. HTTP is enough in this app — no certificate."
                  : "Leave blank to use this same origin. Set it only when the app is installed on a phone."}
            </span>
          </div>
          {serverStatus && (
            <div className="connect-card__status" data-ok={serverStatus.ok}>
              {serverStatus.message}
            </div>
          )}
          <div className="export-row">
            <button type="button" className="btn btn--sm" disabled={probing} onClick={handleTestServer}>
              {probing ? "Checking…" : "Test connection"}
            </button>
            <button type="button" className="btn btn--sm btn--primary" onClick={handleSaveServer}>
              Save &amp; reload
            </button>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel__title">Camera</div>
        <div className="stack">
          <p className="field__hint">
            The laptop still runs detection and gaze. This chooses whose camera it looks through.
          </p>
          <div className="toggle-row" style={{ borderTop: "none", paddingTop: 0 }}>
            <div>
              <div className="field__label">This phone / this browser</div>
              <div className="field__hint">
                Back camera on this phone. Point it at the lamp.
              </div>
            </div>
            <button
              type="button"
              className="switch"
              role="switch"
              aria-checked={engine.cameraSource === "remote"}
              aria-label="Use this device camera"
              onClick={() =>
                engine.updateCameraPref(engine.cameraSource === "remote" ? "local" : "remote")
              }
            />
          </div>
          {!isNativeApp() && engine.phoneNeedsHttps && (
            <div className="connect-card__status" data-ok={false}>
              iPhone Safari’s Visit Website button stays blank. Open{" "}
              <a href={engine.iphoneSetup}>the certificate page</a>, install MyoGaze LAN CA, then use
              HTTPS.
            </div>
          )}
          <span className="field__hint">
            {engine.cameraSource === "remote"
              ? "Next Start uses this device's camera."
              : "Next Start uses the laptop webcam."}
          </span>
        </div>
      </div>

      <div className="panel">
        <div className="panel__title">Lamp hub</div>
        <div className="stack">
          <div className="field">
            <label className="field__label" htmlFor="mqtt_host">
              MQTT host
            </label>
            <input
              id="mqtt_host"
              type="text"
              className="text-input"
              value={local.mqtt_host}
              placeholder="mqtt://192.168.1.20:1883"
              onChange={(e) => queueSave({ mqtt_host: e.target.value })}
            />
            <span className="field__hint">Where this laptop talks to the lamp relay. Leave it unless the hub moved.</span>
          </div>
        </div>
      </div>
      </>
      )}

      {showSensitivity && (
      <>
      <div>
        <button type="button" className="btn btn--ghost" onClick={handleRestoreDefaults}>
          <ResetIcon size={14} />
          Restore defaults
        </button>
      </div>
      </>
      )}
    </div>
  );
}
