import type { Device } from "../types";
import { LampIcon, FanIcon, PlugIcon } from "../icons";

function kindFor(device: Device): "lamp" | "fan" | "plug" {
  const key = `${device.id} ${device.label}`.toLowerCase();
  if (key.includes("fan")) return "fan";
  if (key.includes("plug")) return "plug";
  return "lamp";
}

const ICONS = { lamp: LampIcon, fan: FanIcon, plug: PlugIcon };
const PHOTOS = {
  lamp: "/device-lamp.png",
  fan: "/device-fan.png",
  plug: "/device-plug.png",
};

interface DeviceCardProps {
  device: Device;
  gazeState?: "locked" | "locking" | "unsure" | null;
  offline?: boolean;
  plain?: boolean;
  onOpen: () => void;
  onToggle: (id: string) => void;
}

export function DeviceCard({ device, gazeState, offline, plain, onOpen, onToggle }: DeviceCardProps) {
  const kind = kindFor(device);
  const Icon = ICONS[kind];

  let status = device.is_on ? "On" : "Off";
  let tone = device.is_on ? "on" : "off";
  if (offline) {
    status = "Offline";
    tone = "offline";
  } else if (gazeState === "locked") {
    status = "Locked";
    tone = "locked";
  } else if (gazeState === "locking") {
    status = "Locking";
    tone = "hold";
  } else if (gazeState === "unsure") {
    status = "Unsure";
    tone = "unsure";
  }

  return (
    <div className={plain ? "tile tile--plain" : "tile"} data-device={kind} data-on={device.is_on} data-gaze={gazeState ?? undefined}>
      <button type="button" className="tile__open" onClick={onOpen}>
        {plain ? (
          <img className="tile__photo" src={PHOTOS[kind]} alt="" />
        ) : (
          <span className="tile__icon" aria-hidden="true">
            <Icon size={18} />
          </span>
        )}
        <span className="tile__name">{device.label}</span>
        <span className="tile__status" data-tone={tone}>
          {status}
        </span>
      </button>
      {!plain && (
        <button
          type="button"
          className="switch"
          role="switch"
          aria-checked={device.is_on}
          aria-label={`Turn ${device.label} ${device.is_on ? "off" : "on"}`}
          onClick={() => onToggle(device.id)}
        />
      )}
    </div>
  );
}
