import type { Decision } from "../types";

interface IntentionMeterProps {
  decision: Decision;
  compact?: boolean;
}

const LABELS: Record<Decision["action"], string> = {
  ACT: "Act",
  ABSTAIN: "Abstain",
  IDLE: "Idle",
};

/**
 * StatusPanel — current decision state, rendered as a reserved-color banner.
 * Kept as IntentionMeter for import compatibility; exports the same props
 * pattern (decision, compact).
 */
export function IntentionMeter({ decision, compact }: IntentionMeterProps) {
  const target = decision.selected_label ?? "No target";

  return (
    <div className="decision-banner" data-action={decision.action}>
      <span className="decision-banner__badge">{LABELS[decision.action]}</span>
      <div className="decision-banner__body">
        <div className="decision-banner__label">{target}</div>
        {!compact && (
          <div className="decision-banner__reason">
            {decision.reason || "Waiting for gaze and muscle signal."}
          </div>
        )}
      </div>
    </div>
  );
}

export const StatusPanel = IntentionMeter;
