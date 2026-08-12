import type { Device } from "../types";
import { IconFan, IconLamp, IconPlug, IconMonitor } from "../icons";

function pickIcon(device: Device) {
  const key = `${device.id} ${device.label}`.toLowerCase();
  if (key.includes("lamp") || key.includes("bottle") || key.includes("vase") || key.includes("plant")) {
    return IconLamp;
  }
  if (key.includes("fan") || key.includes("cup") || key.includes("glass") || key.includes("bowl")) {
    return IconFan;
  }
  if (key.includes("phone") || key.includes("remote") || key.includes("plug") || key.includes("keyboard")) {
    return IconPlug;
  }
  if (key.includes("laptop") || key.includes("tv") || key.includes("book") || key.includes("monitor")) {
    return IconMonitor;
  }
  return IconPlug;
}

interface Props {
  device: Device;
  onToggle: (id: string) => void;
  justChanged?: boolean;
  highlight?: "selected" | "candidate" | null;
}

export function DeviceCard({ device, onToggle, justChanged, highlight }: Props) {
  const Icon = pickIcon(device);

  return (
    <div
      className={`device-card ${device.is_on ? "is-on" : ""} ${justChanged ? "just-changed" : ""} ${
        highlight === "selected" ? "is-selected" : highlight === "candidate" ? "is-candidate" : ""
      }`}
    >
      <div className="device-icon" aria-hidden="true">
        <Icon />
      </div>
      <div className="device-info">
        <span className="device-label">{device.label}</span>
        <span className="device-meta">
          {device.is_on ? "On" : "Off"} · {device.toggle_count} toggles
          {highlight === "selected" ? " · ready" : highlight === "candidate" ? " · dwelling" : ""}
        </span>
      </div>
      <button
        type="button"
        className="device-switch"
        role="switch"
        aria-checked={device.is_on}
        aria-label={`Turn ${device.label} ${device.is_on ? "off" : "on"}`}
        onClick={() => onToggle(device.id)}
      >
        <span className="device-switch-knob" />
      </button>
    </div>
  );
}
