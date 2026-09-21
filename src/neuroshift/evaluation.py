"""Cued-trial evaluation — ground truth for accuracy, false activations, latency.

The session log records what the system *did*. To report accuracy we also need
what the user *meant*, so this module runs a cued protocol: the app names a
target appliance, the participant looks at it and confirms, and the outcome is
scored against the cue.

Outcomes
    HIT    actuated the cued appliance
    WRONG  actuated a different appliance (a false activation)
    MISS   nothing actuated before the trial was skipped or timed out

These three give selection accuracy, a real false-activation rate (rather than
the Phase-0 proxy in SessionMetrics), and time-to-select.
"""

from __future__ import annotations

import csv
import io
import json
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from statistics import mean, median

HIT = "HIT"
WRONG = "WRONG"
MISS = "MISS"

# The ESP32 hub exposes three relays; every actuation maps onto one of them.
CUE_TARGETS: tuple[tuple[str, str], ...] = (
    ("lamp", "Lamp"),
    ("fan", "Fan"),
    ("plug", "Plug"),
)


@dataclass
class CuedTrial:
    index: int
    cued_device_id: str
    cued_label: str
    cue_ts: str
    dwell_required: bool
    detect_mode: str
    outcome: str | None = None
    selected_device_id: str | None = None
    selected_label: str | None = None
    latency_s: float | None = None
    resolved_ts: str | None = None

    @property
    def done(self) -> bool:
        return self.outcome is not None


def _stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"median": None, "mean": None, "min": None, "max": None}
    return {
        "median": round(median(values), 3),
        "mean": round(mean(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


def _score(trials: list[CuedTrial]) -> dict:
    done = [t for t in trials if t.done]
    n = len(done)
    hits = sum(1 for t in done if t.outcome == HIT)
    wrong = sum(1 for t in done if t.outcome == WRONG)
    misses = sum(1 for t in done if t.outcome == MISS)
    latencies = [t.latency_s for t in done if t.outcome == HIT and t.latency_s is not None]
    denom = n or 1
    return {
        "trials": n,
        "hits": hits,
        "wrong": wrong,
        "misses": misses,
        "accuracy": round(hits / denom, 4) if n else 0.0,
        "false_activation_rate": round(wrong / denom, 4) if n else 0.0,
        "miss_rate": round(misses / denom, 4) if n else 0.0,
        "latency_s": _stats([float(v) for v in latencies]),
    }


class CuedTrialRunner:
    """Drives the cued protocol and scores each trial against its cue.

    Time is injected so the protocol can be replayed deterministically in tests
    and offline analysis.
    """

    def __init__(self, *, timeout_s: float = 12.0, seed: int | None = None) -> None:
        self.timeout_s = float(timeout_s)
        self.trials: list[CuedTrial] = []
        self.active: CuedTrial | None = None
        # Most recently scored trial, so the UI can announce HIT/WRONG/MISS.
        self.last_resolved: CuedTrial | None = None
        self._rng = random.Random(seed)
        self._cue_monotonic: float | None = None

    # -- protocol ---------------------------------------------------------

    def next_cue(self) -> tuple[str, str]:
        """Pick a target, avoiding an immediate repeat so the participant
        cannot coast on the previous answer."""
        choices = list(CUE_TARGETS)
        if self.trials:
            last = self.trials[-1].cued_device_id
            remaining = [c for c in choices if c[0] != last]
            if remaining:
                choices = remaining
        return self._rng.choice(choices)

    def start(
        self,
        *,
        device_id: str | None = None,
        label: str | None = None,
        dwell_required: bool = True,
        detect_mode: str = "slots",
        now: float,
    ) -> CuedTrial:
        """Begin a trial. Any trial still open is closed as a MISS."""
        if self.active is not None:
            self._resolve(self.active, MISS, None, None, now=now)

        if device_id is None:
            device_id, label = self.next_cue()
        elif label is None:
            label = dict(CUE_TARGETS).get(device_id, device_id.title())

        trial = CuedTrial(
            index=len(self.trials) + 1,
            cued_device_id=device_id,
            cued_label=label or device_id,
            cue_ts=datetime.now(timezone.utc).isoformat(),
            dwell_required=dwell_required,
            detect_mode=detect_mode,
        )
        self.trials.append(trial)
        self.active = trial
        self._cue_monotonic = now
        return trial

    def on_actuation(self, *, device_id: str, label: str | None, now: float) -> CuedTrial | None:
        """Resolve the open trial against an actuation. Returns it, or None
        when no trial is running (free-play actuations are not scored)."""
        if self.active is None:
            return None
        outcome = HIT if device_id == self.active.cued_device_id else WRONG
        return self._resolve(self.active, outcome, device_id, label, now=now)

    def skip(self, *, now: float) -> CuedTrial | None:
        """Abandon the open trial; counts against accuracy as a MISS."""
        if self.active is None:
            return None
        return self._resolve(self.active, MISS, None, None, now=now)

    def check_timeout(self, *, now: float) -> CuedTrial | None:
        """Close the open trial if it has run past the timeout."""
        if self.active is None or self._cue_monotonic is None:
            return None
        if now - self._cue_monotonic < self.timeout_s:
            return None
        return self._resolve(self.active, MISS, None, None, now=now)

    def _resolve(
        self,
        trial: CuedTrial,
        outcome: str,
        device_id: str | None,
        label: str | None,
        *,
        now: float,
    ) -> CuedTrial:
        trial.outcome = outcome
        trial.selected_device_id = device_id
        trial.selected_label = label
        trial.resolved_ts = datetime.now(timezone.utc).isoformat()
        if self._cue_monotonic is not None:
            trial.latency_s = round(max(0.0, now - self._cue_monotonic), 3)
        self.active = None
        self._cue_monotonic = None
        self.last_resolved = trial
        return trial

    def reset(self) -> None:
        self.trials.clear()
        self.active = None
        self.last_resolved = None
        self._cue_monotonic = None

    # -- results ----------------------------------------------------------

    def summary(self) -> dict:
        """Overall scores plus a dwell-gated vs instant-gaze breakdown, which
        is the Phase-I comparison the report needs."""
        overall = _score(self.trials)
        by_condition = {}
        for name, want in (("dwell_gated", True), ("instant_gaze", False)):
            subset = [t for t in self.trials if t.dwell_required is want]
            if subset:
                by_condition[name] = _score(subset)
        return {
            **overall,
            "pending": self.active.index if self.active else None,
            "by_condition": by_condition,
        }

    def to_dicts(self) -> list[dict]:
        return [asdict(t) for t in self.trials]

    def to_json(self) -> str:
        return json.dumps({"summary": self.summary(), "trials": self.to_dicts()}, indent=2)

    def to_csv(self) -> str:
        fields = list(CuedTrial.__dataclass_fields__.keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields)
        writer.writeheader()
        for trial in self.trials:
            writer.writerow(asdict(trial))
        return buf.getvalue()
