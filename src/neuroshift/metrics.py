"""Simple session counters for demo / early FAR discussion."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class SessionMetrics:
    frames: int = 0
    acts: int = 0
    abstains: int = 0
    actuations: int = 0
    # Proxy unsafe events: EMG confirm without a stable gaze target
    emg_without_gaze: int = 0
    # Proxy safe rejects: had gaze target but no EMG (correct abstain)
    gaze_without_emg: int = 0
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def on_decision(self, action: str, reason: str) -> None:
        self.frames += 1
        if action == "ACT":
            self.acts += 1
        else:
            self.abstains += 1
        if reason == "emg_without_stable_gaze_target":
            self.emg_without_gaze += 1
        if reason == "gaze_selected_but_emg_not_confirmed":
            self.gaze_without_emg += 1

    def on_actuation(self) -> None:
        self.actuations += 1

    @property
    def far_proxy(self) -> float:
        """Early FAR proxy: share of decisions that were EMG-without-gaze."""
        total = max(self.acts + self.abstains, 1)
        return self.emg_without_gaze / total

    def summary(self) -> str:
        return (
            f"acts={self.acts} abstain={self.abstains} toggles={self.actuations} "
            f"EMG_no_gaze={self.emg_without_gaze} FAR_proxy={self.far_proxy:.3f}"
        )

    def to_dict(self) -> dict:
        total = max(self.acts + self.abstains, 1)
        return {
            **asdict(self),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "far_proxy": self.far_proxy,
            "abstain_rate": self.abstains / total,
            "act_rate": self.acts / total,
            "note": (
                "FAR_proxy here counts EMG confirms without a stable gazed "
                "target — a Phase-0 stand-in until labeled trial ground truth."
            ),
        }

    def save(self, path: Path | None = None) -> Path:
        root = Path(__file__).resolve().parents[2]
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = path or (root / "logs" / f"session_{stamp}.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return out
