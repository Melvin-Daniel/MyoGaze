import { useEffect, useState } from "react";
import type { AccountUser } from "../../auth";
import { describeActivity, formatMinutesAgo } from "../../activityLog";
import { LampIcon } from "../../icons";
import type { NeuroShiftEngine } from "../../useNeuroShift";
import { ActivityRow, IconChevron, IconGear, IconWarn } from "../RdIcons";

interface HomeViewProps {
  engine: NeuroShiftEngine;
  account: AccountUser;
  trackedMs: number;
  onOpenLive: () => void;
  onOpenReview: () => void;
  onOpenActivity: () => void;
  onOpenSettings: () => void;
}

function firstName(name: string): string {
  const raw = name.trim().split(/\s+/)[0] || "there";
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

function greeting(now: Date): string {
  const hour = now.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function formatToday(ms: number): string {
  const minutes = Math.floor(Math.max(0, ms) / 60000);
  if (minutes < 1) return "No session yet";
  if (minutes < 60) return `${minutes}m in session today`;
  const hours = Math.floor(minutes / 60);
  const rem = minutes % 60;
  return rem ? `${hours}h ${rem}m in session today` : `${hours}h in session today`;
}

export function HomeView({
  engine,
  account,
  trackedMs,
  onOpenLive,
  onOpenReview,
  onOpenActivity,
  onOpenSettings,
}: HomeViewProps) {
  const running = engine.sessionState === "running";
  const online = engine.connection === "connected";
  const name = firstName(account.name);
  const [now, setNow] = useState(Date.now());
  const items = engine.activity.map((entry) => describeActivity(entry, name));
  const reviewCount = items.filter((item) => item.alert).length;
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const today = items.filter((item) => item.timestamp >= start.getTime());
  const looks = today.filter((item) => item.kind === "look").length;
  const toggles = today.filter((item) => item.kind === "action").length;
  const unsure = today.filter((item) => item.kind === "review").length;
  const recent = items.slice(0, 3);
  const lamp = engine.devices.find((device) => device.id === "lamp") ?? engine.devices[0];
  const status = running ? "Live" : online ? "Ready" : "Offline";
  const heroSub = running
    ? "Looking at the lamp for two seconds toggles it"
    : online
      ? "Laptop is connected. Start a session to look."
      : "Waiting for the laptop. Open Live once it is online.";

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 15000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="rd-screen">
      <div className="topbar">
        <div>
          <p className="eyebrow">{greeting(new Date(now))}</p>
          <h1 className="title">{name}&apos;s room</h1>
        </div>
        <button type="button" className="iconbtn" aria-label="Settings" onClick={onOpenSettings}>
          <IconGear />
        </button>
      </div>

      <button type="button" className="hero" onClick={onOpenLive}>
        <div className="hero-top">
          <span className={running ? "live-dot" : "live-dot off"} />
          <span className={running ? "hero-status" : "hero-status muted"}>{status}</span>
        </div>
        <p className="hero-headline num">{formatToday(trackedMs)}</p>
        <p className="hero-sub">{heroSub}</p>
        <span className="hero-cta">{running ? "Open live view" : "Start looking"}</span>
      </button>

      {lamp ? (
        <div className="appliance">
          <div className="appliance-icon" data-on={lamp.is_on}>
            <LampIcon size={22} />
          </div>
          <div className="appliance-copy">
            <strong>Lamp</strong>
            <span>{online ? (lamp.is_on ? "On" : "Off") : "Hub offline"}</span>
          </div>
          <button
            type="button"
            className="switch"
            role="switch"
            aria-checked={lamp.is_on}
            aria-label={`Turn lamp ${lamp.is_on ? "off" : "on"}`}
            disabled={!online}
            onClick={() => engine.toggleDevice(lamp.id)}
          />
        </div>
      ) : null}

      {reviewCount > 0 ? (
        <button type="button" className="attn" onClick={onOpenReview}>
          <div className="attn-icon">
            <IconWarn />
          </div>
          <div className="attn-text">
            <strong>
              {reviewCount} unsure look{reviewCount === 1 ? "" : "s"}
            </strong>
            <span>MyoGaze waited instead of guessing</span>
          </div>
          <div className="attn-chev">
            <IconChevron />
          </div>
        </button>
      ) : null}

      <p className="section-label">Today</p>
      <div className="statstrip">
        <div className="stat">
          <div className="stat-num num">{looks}</div>
          <div className="stat-label">Looks</div>
        </div>
        <div className="stat">
          <div className="stat-num num">{toggles}</div>
          <div className="stat-label">Toggles</div>
        </div>
        <div className="stat">
          <div className="stat-num num">{unsure}</div>
          <div className="stat-label">Unsure</div>
        </div>
      </div>

      <p className="section-label">Recent</p>
      <div className="list">
        {recent.length === 0 ? (
          <div className="empty-card">
            <strong>Nothing logged yet</strong>
            <span>Start a session and look at the lamp for two seconds.</span>
          </div>
        ) : (
          recent.map((item) => <ActivityRow key={item.id} item={item} time={formatMinutesAgo(item.timestamp, now)} />)
        )}
      </div>
      <button type="button" className="seeall" onClick={onOpenActivity}>
        See all activity →
      </button>

      <div className="device-strip">
        <span>
          <span className={online ? "strip-dot on" : "strip-dot"} />
          {online ? "Laptop online" : "Laptop offline"}
        </span>
        <span>
          <span className={running ? "strip-dot on" : "strip-dot"} />
          {running ? "Camera on" : "Camera idle"}
        </span>
      </div>
    </div>
  );
}
