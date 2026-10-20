import type { NeuroShiftEngine } from "../../useNeuroShift";
import { DownloadIcon, RefreshIcon } from "../../icons";

interface InsightsViewProps {
  engine: NeuroShiftEngine;
}

const TRIAL_LABELS: Record<string, string> = {
  total_records: "Records",
  decisions: "Decisions",
  actuations: "Actuations",
  confirms: "Confirms",
  acts: "Acts",
  abstains: "Abstains",
  markers: "Block marks",
};

export function InsightsView({ engine }: InsightsViewProps) {
  const { acts, abstains, actuations, far_proxy } = engine.stats;
  const total = acts + abstains;
  const actPct = total > 0 ? (acts / total) * 100 : 0;
  const abstainPct = total > 0 ? (abstains / total) * 100 : 0;
  const confirms = engine.trialSummary?.confirms ?? 0;
  const summaryEntries = engine.trialSummary
    ? Object.entries(engine.trialSummary as unknown as Record<string, number>)
    : [];

  return (
    <div className="stack">
      <div className="view-header">
        <h1>Insights</h1>
        <p>Session accuracy and exports.</p>
      </div>

      <div className="grid grid--stats">
        <div className="stat-card">
          <div className="stat-card__label">Confirmed</div>
          <div className="stat-card__value">{acts}</div>
          <div className="stat-card__bar">
            <span data-tone="act" style={{ width: `${actPct}%` }} />
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card__label">Held back</div>
          <div className="stat-card__value">{abstains}</div>
          <div className="stat-card__bar">
            <span data-tone="abstain" style={{ width: `${abstainPct}%` }} />
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card__label">Devices switched</div>
          <div className="stat-card__value">{actuations}</div>
          <div className="stat-card__bar">
            <span style={{ width: `${Math.min(100, actuations * 10)}%` }} />
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card__label">Possible mistakes</div>
          <div className="stat-card__value">{(far_proxy * 100).toFixed(0)}%</div>
          <div className="stat-card__bar">
            <span
              data-tone={far_proxy > 0.15 ? "abstain" : "act"}
              style={{ width: `${Math.min(100, far_proxy * 100)}%` }}
            />
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel__title">Confirmed vs held back</div>
        {total === 0 ? (
          <p className="field__hint">No decisions recorded yet.</p>
        ) : (
          <>
            <div className="ratio-bar" role="img" aria-label={`${acts} acts, ${abstains} abstains`}>
              <div className="ratio-bar__act" style={{ width: `${actPct}%` }} />
              <div className="ratio-bar__abstain" style={{ width: `${abstainPct}%` }} />
            </div>
            <div className="ratio-legend">
              <span>
                <span className="ratio-legend__swatch" style={{ background: "var(--state-act)" }} />
                Confirmed {actPct.toFixed(0)}%
              </span>
              <span>
                <span className="ratio-legend__swatch" style={{ background: "var(--state-abstain)" }} />
                Held back {abstainPct.toFixed(0)}%
              </span>
            </div>
          </>
        )}
      </div>

      <div className="panel">
        <div className="panel__title">Accuracy trials</div>
        <p className="field__hint" style={{ marginBottom: 12 }}>
          The app names a device. Look at it, wait for lock, then Confirm. Hits and misses become
          the accuracy numbers in your report.
        </p>
        {engine.activeCue && !engine.activeCue.outcome ? (
          <div className="cue-banner" data-tone="accent" style={{ marginBottom: 12 }}>
            <div>
              <div className="cue-banner__k">Now look at</div>
              <div className="cue-banner__v">{engine.activeCue.cued_label}</div>
            </div>
            <button type="button" className="btn btn--sm" onClick={() => engine.skipCue()}>
              Skip (miss)
            </button>
          </div>
        ) : null}
        <div className="kv-grid" style={{ marginBottom: 12 }}>
          <div className="kv">
            <div className="kv__k">Accuracy</div>
            <div className="kv__v">{(engine.cuedSummary.accuracy * 100).toFixed(0)}%</div>
          </div>
          <div className="kv">
            <div className="kv__k">Hits</div>
            <div className="kv__v">{engine.cuedSummary.hits}</div>
          </div>
          <div className="kv">
            <div className="kv__k">Wrong device</div>
            <div className="kv__v">{engine.cuedSummary.wrong}</div>
          </div>
          <div className="kv">
            <div className="kv__k">Misses</div>
            <div className="kv__v">{engine.cuedSummary.misses}</div>
          </div>
          <div className="kv">
            <div className="kv__k">False activations</div>
            <div className="kv__v">{(engine.cuedSummary.false_activation_rate * 100).toFixed(0)}%</div>
          </div>
          <div className="kv">
            <div className="kv__k">Median latency</div>
            <div className="kv__v">
              {engine.cuedSummary.latency_s.median == null
                ? "—"
                : `${engine.cuedSummary.latency_s.median.toFixed(2)}s`}
            </div>
          </div>
        </div>
        <div className="export-row">
          <button type="button" className="btn btn--sm btn--primary" onClick={() => engine.startCue()}>
            Next cue
          </button>
          <button type="button" className="btn btn--sm" onClick={() => engine.startCue("lamp")}>
            Cue Lamp
          </button>
          <button type="button" className="btn btn--sm" onClick={() => engine.startCue("fan")}>
            Cue Fan
          </button>
          <button type="button" className="btn btn--sm" onClick={() => engine.startCue("plug")}>
            Cue Plug
          </button>
          <button type="button" className="btn btn--sm" onClick={() => engine.resetCues()}>
            Reset cues
          </button>
        </div>
      </div>

      <div className="panel">
        <div className="panel__title">Pilot checklist</div>
        <ol className="steps">
          <li>Start the camera on Live. Recalibrate if you move.</li>
          <li>Mark Block A with hold-to-lock on, then do about 15 look + Confirm trials.</li>
          <li>Turn hold-to-lock off, mark Block B, and run about 15 more for the comparison.</li>
          <li>Download the HTML report for your appendix.</li>
        </ol>

        <p className="field__hint" style={{ marginBottom: 12 }}>
          Current mode{" "}
          <span className="status-chip" data-tone="accent">
            {engine.dwellRequired ? "Hold to lock" : "Instant look"}
          </span>{" "}
          · Confirms logged: <strong>{confirms}</strong>
        </p>

        <div className="export-row">
          <button
            type="button"
            className="btn btn--sm"
            onClick={() => engine.markTrialBlock("block_A_dwell_gated")}
          >
            Mark Block A (dwell)
          </button>
          <button
            type="button"
            className="btn btn--sm"
            onClick={() => engine.markTrialBlock("block_B_instant_gaze")}
          >
            Mark Block B (instant)
          </button>
          <button
            type="button"
            className="btn btn--sm"
            aria-pressed={engine.dwellRequired}
            onClick={() => engine.toggleDwellMode()}
          >
            Toggle hold: {engine.dwellRequired ? "On" : "Off"}
          </button>
        </div>
      </div>

      {summaryEntries.length > 0 && (
        <div className="panel">
          <div className="panel__title">Trial summary</div>
          <div className="kv-grid">
            {summaryEntries.map(([key, value]) => (
              <div className="kv" key={key}>
                <div className="kv__k">{TRIAL_LABELS[key] ?? key.replace(/_/g, " ")}</div>
                <div className="kv__v">{value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel__title">Export evidence pack</div>
        <div className="export-row">
          <button type="button" className="btn btn--sm btn--primary" onClick={() => engine.exportReport()}>
            <DownloadIcon size={14} />
            Session HTML report
          </button>
          <button type="button" className="btn btn--sm" onClick={() => engine.exportTrials("csv")}>
            <DownloadIcon size={14} />
            Export CSV
          </button>
          <button type="button" className="btn btn--sm" onClick={() => engine.exportTrials("json")}>
            <DownloadIcon size={14} />
            Export JSON
          </button>
          <button type="button" className="btn btn--sm" onClick={() => engine.exportCued("csv")}>
            <DownloadIcon size={14} />
            Cued CSV
          </button>
          <button type="button" className="btn btn--sm btn--ghost" onClick={engine.refreshTrials}>
            <RefreshIcon size={14} />
            Refresh
          </button>
        </div>
      </div>

      <div className="callout">
        Possible mistakes counts a confirm with no locked device. After named trials, use False
        activations and Accuracy above in the report.
      </div>
    </div>
  );
}
