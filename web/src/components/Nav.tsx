import type { ConnectionStatus, SessionRunState, ViewId } from "../types";
import {
  IconActivity,
  IconHome,
  IconInsights,
  IconMonitor,
  IconSystem,
  IconWifi,
  IconWifiOff,
} from "../icons";

interface Props {
  active: ViewId;
  onChange: (v: ViewId) => void;
  connection: ConnectionStatus;
  sessionState: SessionRunState;
}

const ITEMS: { id: ViewId; label: string; icon: typeof IconHome }[] = [
  { id: "home", label: "Home", icon: IconHome },
  { id: "monitor", label: "Monitor", icon: IconMonitor },
  { id: "activity", label: "Activity", icon: IconActivity },
  { id: "insights", label: "Insights", icon: IconInsights },
  { id: "system", label: "System", icon: IconSystem },
];

export function Nav({ active, onChange, connection, sessionState }: Props) {
  return (
    <nav className="app-nav" aria-label="Primary">
      <div className="app-nav-brand">
        <span className="brand-mark" aria-hidden="true">
          <span className="brand-mark-dot" />
        </span>
        <span className="brand-word">NeuroShift</span>
      </div>

      <ul className="app-nav-list">
        {ITEMS.map(({ id, label, icon: Icon }) => (
          <li key={id}>
            <button
              type="button"
              className={`app-nav-item ${active === id ? "is-active" : ""}`}
              onClick={() => onChange(id)}
              aria-current={active === id ? "page" : undefined}
            >
              <Icon aria-hidden="true" />
              <span>{label}</span>
            </button>
          </li>
        ))}
      </ul>

      <div className="app-nav-status">
        <span className={`status-pill status-${connection}`}>
          {connection === "connected" ? <IconWifi aria-hidden="true" /> : <IconWifiOff aria-hidden="true" />}
          {connection === "connected" ? "Connected" : connection === "reconnecting" ? "Reconnecting" : "Offline"}
        </span>
        <span className={`status-pill status-session-${sessionState}`}>
          <span className="status-dot" aria-hidden="true" />
          {sessionState === "running" ? "Session running" : "Session idle"}
        </span>
      </div>
    </nav>
  );
}
