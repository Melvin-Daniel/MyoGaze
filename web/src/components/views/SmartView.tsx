import { useState } from "react";
import type { NeuroShiftEngine } from "../../useNeuroShift";
import { deriveGazeStatus } from "../../gazeStatus";

interface SmartViewProps {
  engine: NeuroShiftEngine;
  onOpenLive: () => void;
}

export function SmartView({ engine, onOpenLive }: SmartViewProps) {
  const [mode, setMode] = useState<"run" | "auto">("run");
  const running = engine.sessionState === "running";
  const status = deriveGazeStatus({
    running,
    decision: engine.decision,
    liveTargets: engine.liveTargets,
    dwellProgress: engine.dwellProgress,
    dwellRequired: engine.dwellRequired,
    dwellActuates: engine.settings.dwell_actuates !== false,
  });

  function start() {
    if (!running) engine.startSession();
    onOpenLive();
  }

  return (
    <div className="stack">
      <div className="seg" role="tablist">
        <button type="button" role="tab" aria-selected={mode === "run"} onClick={() => setMode("run")}>
          Tap-to-Run
        </button>
        <button type="button" role="tab" aria-selected={mode === "auto"} onClick={() => setMode("auto")}>
          Automation
        </button>
      </div>

      {mode === "run" ? (
        !running ? (
          <div className="empty-block">
            <h2>No session</h2>
            <p>Start a session, then look at a device for two seconds to toggle it.</p>
            <button type="button" className="btn btn--primary" onClick={start}>
              Start session
            </button>
          </div>
        ) : (
          <div className="list-card">
            <button type="button" className="list-row" onClick={onOpenLive}>
              <span className="list-row__main">
                <span className="list-row__title">Open Live</span>
                <span className="list-row__sub">{status.detail}</span>
              </span>
              <span className="list-row__chev" aria-hidden="true">›</span>
            </button>
            {status.canConfirm ? (
            <button
              type="button"
              className="list-row"
              onClick={() => engine.confirmIntent()}
            >
              <span className="list-row__main">
                <span className="list-row__title">
                  {status.targetLabel ? `Confirm ${status.targetLabel}` : "Confirm"}
                </span>
                <span className="list-row__sub">
                  Locked. This is the only action.
                </span>
              </span>
            </button>
            ) : null}
            <button type="button" className="list-row" onClick={() => engine.clearSession()}>
              <span className="list-row__main">
                <span className="list-row__title">Stop</span>
                <span className="list-row__sub">End this session</span>
              </span>
            </button>
          </div>
        )
      ) : (
        <div className="list-card">
          <div className="list-row">
            <span className="list-row__main">
              <span className="list-row__title">Hold to lock</span>
              <span className="list-row__sub">
                {engine.dwellRequired
                  ? "Keep looking for two seconds to toggle."
                  : "Looking is enough. Comparison mode."}
              </span>
            </span>
            <button
              type="button"
              className="switch"
              role="switch"
              aria-checked={engine.dwellRequired}
              aria-label="Hold to lock"
              onClick={() => engine.toggleDwellMode()}
            />
          </div>
        </div>
      )}
    </div>
  );
}
