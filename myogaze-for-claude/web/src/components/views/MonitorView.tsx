import type { NeuroShiftEngine } from "../../useNeuroShift";
import { deriveGazeStatus } from "../../gazeStatus";
import { isNativeApp } from "../../serverConfig";
import { CameraIcon } from "../../icons";

interface MonitorViewProps {
  engine: NeuroShiftEngine;
}

export function MonitorView({ engine }: MonitorViewProps) {
  const running = engine.sessionState === "running";
  const status = deriveGazeStatus({
    running,
    decision: engine.decision,
    liveTargets: engine.liveTargets,
    dwellProgress: engine.dwellProgress,
    dwellRequired: engine.dwellRequired,
    dwellActuates: engine.settings.dwell_actuates !== false,
  });
  const cue = engine.activeCue;

  return (
    <div className="live-screen">
      {!isNativeApp() && engine.phoneNeedsHttps && engine.cameraSource === "remote" && (
        <p className="live-note">
          iPhone camera needs the certificate. <a href={engine.iphoneSetup}>Install it</a>, then use HTTPS.
        </p>
      )}

      {cue && !cue.outcome && (
        <div className="live-cue">
          <span>Look at {cue.cued_label}</span>
          <button type="button" onClick={() => engine.skipCue()}>
            Skip
          </button>
        </div>
      )}

      <p className="live-status" data-phase={status.phase}>
        {status.title}
      </p>

      <div className="preview live-preview" data-phase={status.phase}>
        {running && engine.previewJpeg ? (
          <img src={engine.previewJpeg} alt="Live camera" />
        ) : (
          <div className="preview__empty">
            <span className="preview__empty-icon" aria-hidden="true">
              <CameraIcon size={22} />
            </span>
            <p>{running ? "Connecting camera" : "Camera off"}</p>
          </div>
        )}

      </div>

      <div className="live-actions">
        {!running ? (
          <button type="button" className="btn btn--primary live-confirm" onClick={() => engine.startSession()}>
            Start session
          </button>
        ) : status.canConfirm ? (
          <button
            type="button"
            className="btn btn--primary live-confirm"
            onClick={() => engine.confirmIntent()}
          >
            {status.targetLabel ? `Confirm ${status.targetLabel}` : "Confirm"}
          </button>
        ) : (
          <p className="live-note">{status.detail}</p>
        )}
        <div className="live-quiet">
          {running && (
            <>
              <button type="button" onClick={() => engine.calibrateGaze()}>
                Recalibrate
              </button>
              <button type="button" onClick={() => engine.clearSession()}>
                Stop
              </button>
              <button type="button" onClick={() => engine.toggleDetectMode()}>
                {engine.detectMode === "objects" ? "Objects" : "Slots"}
              </button>
            </>
          )}
          {!running && (
            <button type="button" onClick={() => engine.startMockSession()}>
              Demo
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
