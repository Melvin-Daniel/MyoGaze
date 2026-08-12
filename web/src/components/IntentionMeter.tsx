import type { Decision, Settings, SessionRunState } from "../types";
import { IconGaze, IconMuscle, IconShieldCheck, IconShieldPause, IconGaze as IconWatch } from "../icons";

interface Props {
  decision: Decision;
  settings: Settings;
  sessionState: SessionRunState;
}

const STATE_COPY: Record<Decision["action"], string> = {
  ACT: "Act",
  ABSTAIN: "Abstain",
  IDLE: "Watching",
};

export function IntentionMeter({ decision, settings, sessionState }: Props) {
  const gazeProgress = clamp01(Math.abs(decision.yaw));
  const muscleProgress = clamp01(decision.emg / Math.max(settings.emg_confirm_threshold, 0.01));

  const stateClass =
    decision.action === "ACT" ? "is-act" : decision.action === "ABSTAIN" ? "is-abstain" : "is-idle";

  const StateIcon =
    decision.action === "ACT" ? IconShieldCheck : decision.action === "ABSTAIN" ? IconShieldPause : IconWatch;

  return (
    <div className={`meter ${stateClass}`} role="status" aria-live="polite">
      <div className="meter-top">
        <div className="meter-state">
          <StateIcon className="meter-state-icon" aria-hidden="true" />
          <span className="meter-state-label">{STATE_COPY[decision.action]}</span>
        </div>
        <p className="meter-reason">
          {sessionState === "running"
            ? decision.reason
            : "Session idle — start a monitor session to begin reading intention."}
        </p>
      </div>

      <div className="meter-tracks">
        <div className="track">
          <div className="track-label">
            <IconGaze aria-hidden="true" />
            <span>Gaze selects</span>
            {decision.selected_label && sessionState === "running" ? (
              <span className="track-target">{decision.selected_label}</span>
            ) : null}
          </div>
          <div className="track-bar">
            <div
              className="track-fill track-fill-gaze"
              style={{ width: `${sessionState === "running" ? gazeProgress * 100 : 0}%` }}
            />
          </div>
        </div>

        <div className="track">
          <div className="track-label">
            <IconMuscle aria-hidden="true" />
            <span>Muscle confirms</span>
          </div>
          <div className="track-bar">
            <div
              className="track-fill track-fill-muscle"
              style={{ width: `${sessionState === "running" ? muscleProgress * 100 : 0}%` }}
            />
            <div
              className="track-threshold"
              style={{ left: `${clamp01(settings.emg_confirm_threshold) * 100}%` }}
              title="Confirm threshold"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function clamp01(n: number) {
  return Math.max(0, Math.min(1, n));
}
