import type { GazeStatus } from "../gazeStatus";

interface GazeStatusCardProps {
  status: GazeStatus;
  compact?: boolean;
}

const STEPS = [
  { id: "see", label: "See" },
  { id: "hold", label: "Hold" },
  { id: "confirm", label: "Confirm" },
] as const;

function stepState(status: GazeStatus, id: (typeof STEPS)[number]["id"]): "done" | "active" | "todo" {
  const { phase } = status;
  if (id === "see") {
    if (phase === "idle" || phase === "searching") return phase === "searching" ? "active" : "todo";
    return "done";
  }
  if (id === "hold") {
    if (phase === "looking") return "active";
    if (phase === "locked" || phase === "confirmed") return "done";
    if (phase === "unsure") return "active";
    return "todo";
  }
  if (phase === "locked") return "active";
  if (phase === "confirmed") return "done";
  return "todo";
}

export function GazeStatusCard({ status, compact }: GazeStatusCardProps) {
  const showBar = status.phase === "looking" || (status.phase === "locked" && status.dwellPct >= 100);

  return (
    <div className="gaze-status" data-phase={status.phase}>
      <div className="gaze-status__kicker">{status.kicker}</div>
      <div className="gaze-status__title">{status.title}</div>
      <p className="gaze-status__detail">{status.detail}</p>

      {showBar && (
        <div
          className="gaze-status__bar"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={status.dwellPct}
          aria-label="Lock progress"
        >
          <span style={{ width: `${status.dwellPct}%` }} />
        </div>
      )}

      {!compact && (
        <ol className="lock-steps" aria-label="How locking works">
          {STEPS.map((step) => (
            <li key={step.id} data-state={stepState(status, step.id)}>
              <span className="lock-steps__dot" aria-hidden="true" />
              {step.label}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
