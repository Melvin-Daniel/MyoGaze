"""Structured Phase-I trial log for reports and CSV export."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class TrialRecord:
    trial_id: int
    ts: str
    event: str  # decision | actuation | confirm
    action: str
    device_id: str | None = None
    label: str | None = None
    reason: str = ""
    dwell_progress: float = 0.0
    dwell_required: bool = True
    detect_mode: str = "slots"
    yaw: float | None = None
    emg: float | None = None
    command: str | None = None
    note: str = ""


@dataclass
class TrialLog:
    records: list[TrialRecord] = field(default_factory=list)
    _next_id: int = 1

    def reset(self) -> None:
        self.records.clear()
        self._next_id = 1

    def log_confirm(self, *, dwell_required: bool, detect_mode: str) -> TrialRecord:
        return self._append(
            event="confirm",
            action="CONFIRM",
            reason="user_confirm_pulse",
            dwell_required=dwell_required,
            detect_mode=detect_mode,
            note="Confirm button (EMG stand-in)",
        )

    def log_decision(
        self,
        *,
        action: str,
        device_id: str | None,
        label: str | None,
        reason: str,
        dwell_progress: float,
        dwell_required: bool,
        detect_mode: str,
        yaw: float | None = None,
        emg: float | None = None,
    ) -> TrialRecord:
        return self._append(
            event="decision",
            action=action,
            device_id=device_id,
            label=label,
            reason=reason,
            dwell_progress=dwell_progress,
            dwell_required=dwell_required,
            detect_mode=detect_mode,
            yaw=yaw,
            emg=emg,
        )

    def log_actuation(
        self,
        *,
        device_id: str,
        label: str,
        command: str,
        dwell_required: bool,
        detect_mode: str,
    ) -> TrialRecord:
        return self._append(
            event="actuation",
            action="ACTUATE",
            device_id=device_id,
            label=label,
            command=command,
            dwell_required=dwell_required,
            detect_mode=detect_mode,
            reason="device_toggled",
        )

    def log_marker(
        self,
        *,
        note: str,
        dwell_required: bool,
        detect_mode: str,
    ) -> TrialRecord:
        return self._append(
            event="marker",
            action="MARK",
            reason="pilot_block",
            dwell_required=dwell_required,
            detect_mode=detect_mode,
            note=note,
        )

    def _append(self, **kwargs) -> TrialRecord:
        rec = TrialRecord(
            trial_id=self._next_id,
            ts=datetime.now(timezone.utc).isoformat(),
            **kwargs,
        )
        self._next_id += 1
        self.records.append(rec)
        return rec

    def summary(self) -> dict:
        decisions = [r for r in self.records if r.event == "decision"]
        actuations = [r for r in self.records if r.event == "actuation"]
        confirms = [r for r in self.records if r.event == "confirm"]
        markers = [r for r in self.records if r.event == "marker"]
        acts = sum(1 for r in decisions if r.action == "ACT")
        abstains = sum(1 for r in decisions if r.action == "ABSTAIN")
        return {
            "total_records": len(self.records),
            "decisions": len(decisions),
            "actuations": len(actuations),
            "confirms": len(confirms),
            "markers": len(markers),
            "acts": acts,
            "abstains": abstains,
        }

    def to_dicts(self) -> list[dict]:
        return [asdict(r) for r in self.records]

    def to_json(self) -> str:
        return json.dumps(
            {"summary": self.summary(), "trials": self.to_dicts()},
            indent=2,
        )

    def to_csv(self) -> str:
        fields = list(TrialRecord.__dataclass_fields__.keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields)
        writer.writeheader()
        for rec in self.records:
            writer.writerow(asdict(rec))
        return buf.getvalue()

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        csv_path = path.with_suffix(".csv")
        csv_path.write_text(self.to_csv(), encoding="utf-8")
        return path
