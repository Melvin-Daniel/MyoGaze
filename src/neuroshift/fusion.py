"""Gaze-select + EMG-confirm → Act / Abstain."""

from __future__ import annotations

from dataclasses import dataclass

from .config import Config, DEFAULT


@dataclass
class Decision:
    action: str  # ACT | ABSTAIN
    selected_device: str | None
    reason: str
    gaze_ok: bool
    emg_ok: bool


class IntentionFusion:
    def __init__(self, cfg: Config = DEFAULT):
        self.cfg = cfg

    def decide(
        self,
        selected_device: str | None,
        gaze_confidence: float,
        emg_score: float,
        emg_confirmed: bool,
        ambiguous: bool = False,
    ) -> Decision:
        emg_ok = emg_confirmed and emg_score >= self.cfg.emg_confirm_threshold

        if ambiguous:
            return Decision(
                action=self.cfg.abstain_label,
                selected_device=None,
                reason="ambiguous_gaze_targets",
                gaze_ok=False,
                emg_ok=emg_ok,
            )

        gaze_ok = (
            selected_device is not None
            and gaze_confidence >= self.cfg.gaze_select_threshold
        )

        if gaze_ok and emg_ok:
            return Decision(
                action=self.cfg.act_label,
                selected_device=selected_device,
                reason="gaze_selected_and_emg_confirmed",
                gaze_ok=True,
                emg_ok=True,
            )

        if not gaze_ok and not emg_ok:
            reason = "no_gaze_target_and_no_emg"
        elif not gaze_ok:
            reason = "emg_without_stable_gaze_target"
        else:
            reason = "gaze_selected_but_emg_not_confirmed"

        return Decision(
            action=self.cfg.abstain_label,
            selected_device=selected_device if gaze_ok else None,
            reason=reason,
            gaze_ok=gaze_ok,
            emg_ok=emg_ok,
        )
