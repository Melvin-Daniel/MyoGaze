import { useEffect, useRef, useState, type CSSProperties } from "react";
import { describeActivity, formatMinutesAgo } from "../../activityLog";
import { deriveGazeStatus } from "../../gazeStatus";
import { usePrefs } from "../../settings/prefs";
import type { NeuroShiftEngine } from "../../useNeuroShift";
import { ActivityRow, IconBack, IconGear } from "../RdIcons";

interface LiveViewProps {
  engine: NeuroShiftEngine;
  personName: string;
  onBack: () => void;
  onOpenSettings: () => void;
  onPaused: (paused: boolean) => void;
}

function lampTargets(targets: NeuroShiftEngine["liveTargets"]) {
  const lamps = targets.filter((item) => /lamp|bulb|light/i.test(`${item.id} ${item.label}`));
  return lamps.length ? lamps : [];
}

export function LiveView({ engine, personName, onBack, onOpenSettings, onPaused }: LiveViewProps) {
  const { prefs } = usePrefs();
  const running = engine.sessionState === "running";
  const online = engine.connection === "connected";
  const liveTargets = lampTargets(engine.liveTargets);
  const status = deriveGazeStatus({
    running,
    decision: engine.decision,
    liveTargets,
    dwellProgress: engine.dwellProgress,
    dwellRequired: engine.dwellRequired,
    dwellActuates: engine.settings.dwell_actuates !== false,
  });
  const recent = engine.activity.map((entry) => describeActivity(entry, personName)).slice(0, 2);
  const target = status.targetLabel ? status.targetLabel.toLowerCase() : "lamp";
  const looking =
    running &&
    (status.phase === "looking" || status.phase === "locked" || status.phase === "confirmed") &&
    Boolean(status.targetLabel);
  const wizardNote = (engine.decision.reason || "").trim();
  const isWizard = /look at the (camera|real )|look templates|center saved/i.test(wizardNote);
  const lineTitle = !running
    ? "Session paused"
    : isWizard
      ? wizardNote
      : looking
        ? `Looking at the ${target}`
        : status.phase === "unsure"
          ? "Wasn't sure — nothing switched"
          : liveTargets.length
            ? "Lamp in view"
            : "Find the lamp in the camera";
  const lineDetail = !running
    ? "Resume to keep watching"
    : isWizard
      ? "Look at the lamp in the room, not this screen"
      : looking
        ? status.detail
        : status.phase === "unsure"
          ? "Look at the lamp only"
          : "Hold your gaze on the lamp for two seconds to toggle it. Look away before the next toggle.";
  const pill = running ? "tracking" : online ? "paused" : "offline";
  const pillLabel = running ? "Looking" : online ? "Paused" : "Offline";

  return (
    <div className="rd-screen">
      <div className="topbar">
        <button type="button" className="iconbtn" aria-label="Back" onClick={onBack}>
          <IconBack />
        </button>
        <h1 className="title">Live</h1>
        <button type="button" className="iconbtn" aria-label="Settings" onClick={onOpenSettings}>
          <IconGear />
        </button>
      </div>

      <div className={`statepill ${pill}`}>
        <svg viewBox="0 0 24 24" fill="currentColor">
          <circle cx="12" cy="12" r="6" />
        </svg>
        {pillLabel}
      </div>

      <div className="videoframe">
        {engine.previewJpeg ? (
          <DetectionStage
            jpeg={engine.previewJpeg}
            targets={liveTargets}
            gazePoint={engine.gazePoint}
          />
        ) : (
          <div className="video-empty">
            <p>{running ? "Starting camera…" : "Camera is off"}</p>
            <span>The laptop webcam watches the lamp. This phone is the control screen.</span>
          </div>
        )}
      </div>

      {prefs.accessibility.visualFeedback ? (
        <div className={looking ? "confirm-line looking" : "confirm-line"}>
          <DwellMeter percent={looking ? status.dwellPct : 0} title={lineTitle} detail={lineDetail} />
        </div>
      ) : (
        <div className="confirm-line">
          <div className="confirm-text">
            <strong>{lineTitle}</strong>
            <span>{lineDetail}</span>
          </div>
        </div>
      )}

      <p className="section-label just">Just now</p>
      <div className="list">
        {recent.length === 0 ? (
          <div className="empty-card">
            <strong>Waiting for a look</strong>
            <span>A two-second hold on the lamp will show up here.</span>
          </div>
        ) : (
          recent.map((item) => <ActivityRow key={item.id} item={item} time={formatMinutesAgo(item.timestamp)} />)
        )}
      </div>

      <div className="btnrow">
        <button
          type="button"
          className="btn primary"
          onClick={() => {
            if (running) {
              onPaused(true);
              void engine.pauseSession();
            } else {
              onPaused(false);
              void engine.startSession();
            }
          }}
        >
          {running ? "Pause" : "Resume"}
        </button>
        <button type="button" className="btn" onClick={() => void engine.calibrateGaze()}>
          Recalibrate
        </button>
      </div>
    </div>
  );
}

function DetectionStage({
  jpeg,
  targets,
  gazePoint,
}: {
  jpeg: string;
  targets: NeuroShiftEngine["liveTargets"];
  gazePoint: [number, number] | null;
}) {
  const frameRef = useRef<HTMLDivElement>(null);
  const frontRef = useRef<HTMLImageElement>(null);
  const backRef = useRef<HTMLImageElement>(null);
  const showingFront = useRef(true);
  const [fit, setFit] = useState({ x: 0, y: 0, w: 0, h: 0 });

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return;
    const measure = (img: HTMLImageElement | null) => {
      if (!img || !img.naturalWidth) return;
      const fw = frame.clientWidth;
      const fh = frame.clientHeight;
      const iw = img.naturalWidth || 4;
      const ih = img.naturalHeight || 3;
      const scale = Math.min(fw / iw, fh / ih);
      const w = iw * scale;
      const h = ih * scale;
      setFit({ x: (fw - w) / 2, y: (fh - h) / 2, w, h });
    };
    const hidden = showingFront.current ? backRef.current : frontRef.current;
    const shown = showingFront.current ? frontRef.current : backRef.current;
    if (!hidden) return;
    const onLoad = () => {
      hidden.style.opacity = "1";
      hidden.style.zIndex = "1";
      if (shown) {
        shown.style.opacity = "0";
        shown.style.zIndex = "0";
      }
      showingFront.current = !showingFront.current;
      measure(hidden);
    };
    hidden.addEventListener("load", onLoad);
    hidden.src = jpeg;
    const observer = new ResizeObserver(() =>
      measure(showingFront.current ? frontRef.current : backRef.current),
    );
    observer.observe(frame);
    return () => {
      hidden.removeEventListener("load", onLoad);
      observer.disconnect();
    };
  }, [jpeg]);

  const boxes = targets.filter((item) => item.box && item.box.length === 4);

  return (
    <div className="video-stage" ref={frameRef}>
      <img ref={frontRef} className="video-feed video-feed-swap is-shown" alt="Live camera" />
      <img ref={backRef} className="video-feed video-feed-swap" alt="" />
      {fit.w > 0
        ? boxes.map((item) => {
            const [x0, y0, x1, y1] = item.box as [number, number, number, number];
            const hot = Boolean(item.selected || item.candidate);
            return (
              <div
                key={item.id}
                className={hot ? "det-box on" : "det-box"}
                style={{
                  left: fit.x + x0 * fit.w,
                  top: fit.y + y0 * fit.h,
                  width: Math.max(12, (x1 - x0) * fit.w),
                  height: Math.max(12, (y1 - y0) * fit.h),
                }}
              >
                <span className="det-tag">{item.label}</span>
              </div>
            );
          })
        : null}
      {fit.w > 0 && gazePoint ? (
        <span
          className="gaze-dot"
          style={{
            left: fit.x + gazePoint[0] * fit.w,
            top: fit.y + gazePoint[1] * fit.h,
          }}
        />
      ) : null}
    </div>
  );
}

function DwellMeter({ percent, title, detail }: { percent: number; title: string; detail: string }) {
  const pct = Math.max(0, Math.min(100, percent));
  return (
    <>
      <div className="ring" style={{ "--pct": pct } as CSSProperties} aria-hidden />
      <div className="confirm-text">
        <strong>{title}</strong>
        <span>{detail}</span>
      </div>
    </>
  );
}
