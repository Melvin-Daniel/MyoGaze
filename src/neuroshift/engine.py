"""Shared intention tick — used by live UI and offline mock product demos."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .appliances import ActuationEvent, ApplianceHub
from .config import Config, DEFAULT
from .detector import DetectedObject
from .emg_source import EmgSource
from .fusion import Decision, IntentionFusion
from .logger import DecisionLogger
from .metrics import SessionMetrics
from .mqtt_bridge import DecisionPublisher
from .selector import Target, select_target
from .types import GazeEstimate

# After a toggle, gaze must leave the object this long before another 2s hold can start.
_LOOKAWAY_SECONDS = 0.50


def _lock_token(target: Target) -> str:
    blob = f"{target.target_id} {target.label}".lower()
    if any(word in blob for word in ("lamp", "bulb", "light")):
        return "lamp"
    return (target.label or target.target_id).strip().lower()


@dataclass
class TickResult:
    decision: Decision
    selected: Target | None
    candidate: Target | None
    dwell_progress: float
    emg_score: float
    actuation: ActuationEvent | None
    changed: bool


class IntentionEngine:
    """Gaze-select state machine. A finished look-and-hold toggles; EMG is optional."""

    def __init__(
        self,
        cfg: Config = DEFAULT,
        logger: DecisionLogger | None = None,
        metrics: SessionMetrics | None = None,
        publisher: DecisionPublisher | None = None,
        hub: ApplianceHub | None = None,
        emg: EmgSource | None = None,
    ):
        self.cfg = cfg
        self.fusion = IntentionFusion(cfg)
        self.logger = logger or DecisionLogger()
        self.metrics = metrics or SessionMetrics()
        self.publisher = publisher
        self.hub = hub or ApplianceHub()
        self.emg = emg or EmgSource(cfg)

        self.dwell_id: str | None = None
        self.dwell_t0: float | None = None
        self.sticky_id: str | None = None
        self._dwell_target: Target | None = None
        self._dwell_grace_until: float | None = None
        self._dwell_frozen: float | None = None
        self.last_decision: Decision | None = None
        self.cooldown_until = 0.0
        self._emg_prev = 0.0
        self._emg_pulse_until = 0.0
        self._lock_key: str | None = None
        self._away_t0: float | None = None

    def reset_gaze_state(self) -> None:
        self.dwell_id = None
        self.dwell_t0 = None
        self.sticky_id = None
        self._dwell_target = None
        self._dwell_grace_until = None
        self._dwell_frozen = None

    def _matches_lock(self, candidate: Target | None) -> bool:
        if self._lock_key is None or candidate is None or candidate.ambiguous:
            return False
        return _lock_token(candidate) == self._lock_key

    def _lock_blocks_dwell(self, candidate: Target | None, now: float) -> bool:
        """True while the last toggled object is still being looked at."""
        if self._lock_key is None:
            return False
        if self._matches_lock(candidate):
            self._away_t0 = None
            return True
        if self._away_t0 is None:
            self._away_t0 = now
        if now - self._away_t0 >= _LOOKAWAY_SECONDS:
            self._lock_key = None
            self._away_t0 = None
            return False
        return True

    def _dwell_progress(self, now: float) -> float:
        if self.dwell_t0 is None:
            return 0.0
        return (now - self.dwell_t0) / max(self.cfg.dwell_seconds, 1e-3)

    def _hold_dwell(self, now: float) -> Target | None:
        """Keep the current look for a short grace so one dropped frame cannot reset it."""
        if self.dwell_id is None or self._dwell_target is None:
            return None
        if self._dwell_grace_until is None:
            self._dwell_grace_until = now + 0.35
        if now < self._dwell_grace_until:
            return self._dwell_target
        return None

    def tick(
        self,
        gaze: GazeEstimate,
        detections: list[DetectedObject],
        *,
        prefer_detections: bool,
        frame_w: int,
        frame_h: int,
        key: int = -1,
        mouse_y_norm: float | None = None,
        emg_score_override: float | None = None,
        now: float | None = None,
        allow_slots: bool = True,
        look_templates: dict[str, tuple[float, float]] | None = None,
    ) -> TickResult:
        now = time.time() if now is None else now

        candidate = None
        selected = None
        dwell_progress = 0.0

        if gaze.face_found and gaze.confidence >= self.cfg.gaze_select_threshold:
            candidate = select_target(
                gaze,
                detections,
                frame_w,
                frame_h,
                side_threshold=self.cfg.yaw_side_threshold,
                prefer_detections=prefer_detections,
                hysteresis=self.cfg.yaw_hysteresis,
                sticky_id=self.sticky_id,
                ambiguity_margin=self.cfg.gaze_ambiguity_margin,
                allow_slots=allow_slots,
                look_templates=look_templates,
            )
            if self._lock_blocks_dwell(candidate, now):
                self.dwell_id = None
                self.dwell_t0 = None
                self.sticky_id = None
                self._dwell_target = None
                self._dwell_grace_until = None
                self._dwell_frozen = None
                selected = None
                dwell_progress = 0.0
            else:
                same = (
                    candidate is not None
                    and not candidate.ambiguous
                    and (
                        self.dwell_id is None
                        or candidate.target_id == self.dwell_id
                        or (
                            self._dwell_target is not None
                            and _lock_token(candidate) == _lock_token(self._dwell_target)
                        )
                    )
                )
                if same and candidate is not None:
                    self._dwell_grace_until = None
                    # Resume a frozen look: clock continues from where it paused.
                    if self._dwell_frozen is not None and self.dwell_t0 is not None:
                        self.dwell_t0 = now - self._dwell_frozen * max(
                            self.cfg.dwell_seconds, 1e-3
                        )
                        self._dwell_frozen = None
                    self.sticky_id = candidate.target_id
                    if self.cfg.dwell_required:
                        if self.dwell_id is None:
                            self.dwell_id = candidate.target_id
                            self._dwell_target = candidate
                            self.dwell_t0 = now
                            self._dwell_frozen = None
                            dwell_progress = 0.0
                        else:
                            self.dwell_id = candidate.target_id
                            self._dwell_target = candidate
                            dwell_progress = self._dwell_progress(now)
                            if dwell_progress >= 1.0:
                                selected = candidate
                                dwell_progress = 1.0
                    else:
                        self.dwell_id = candidate.target_id
                        self._dwell_target = candidate
                        selected = candidate
                        dwell_progress = 1.0
                else:
                    held = self._hold_dwell(now)
                    if held is not None:
                        candidate = held
                        if detections:
                            # Object still visible but gaze left it — freeze; do not finish on a glance.
                            if self._dwell_frozen is None:
                                self._dwell_frozen = min(0.99, self._dwell_progress(now))
                            dwell_progress = self._dwell_frozen
                        else:
                            # Detector dropped a frame while still looking — keep the clock running.
                            if self._dwell_frozen is not None and self.dwell_t0 is not None:
                                self.dwell_t0 = now - self._dwell_frozen * max(
                                    self.cfg.dwell_seconds, 1e-3
                                )
                                self._dwell_frozen = None
                            dwell_progress = self._dwell_progress(now)
                            if self.cfg.dwell_required and dwell_progress >= 1.0:
                                selected = candidate
                                dwell_progress = 1.0
                    elif candidate is not None and not candidate.ambiguous:
                        self._dwell_grace_until = None
                        self._dwell_frozen = None
                        self.sticky_id = candidate.target_id
                        self._dwell_target = candidate
                        self.dwell_id = candidate.target_id
                        self.dwell_t0 = now
                        dwell_progress = 0.0
                        if not self.cfg.dwell_required:
                            selected = candidate
                            dwell_progress = 1.0
                    elif candidate is not None and candidate.ambiguous:
                        self.dwell_id = None
                        self.dwell_t0 = None
                        self._dwell_target = None
                        self._dwell_grace_until = None
                        self._dwell_frozen = None
                        dwell_progress = 0.0
                    else:
                        self.reset_gaze_state()
        elif self._lock_blocks_dwell(None, now):
            selected = None
            dwell_progress = 0.0
        else:
            held = self._hold_dwell(now)
            if held is not None:
                candidate = held
                # No face / weak gaze — treat like looking away.
                if self._dwell_frozen is None:
                    self._dwell_frozen = min(0.99, self._dwell_progress(now))
                dwell_progress = self._dwell_frozen
            else:
                self.reset_gaze_state()

        if emg_score_override is not None:
            raw_emg = float(emg_score_override)
        else:
            raw_emg = self.emg.poll(key, mouse_y_norm=mouse_y_norm)

        # Rising-edge confirm → short latch (one intentional burst)
        thr = self.cfg.emg_confirm_threshold
        if raw_emg >= thr and self._emg_prev < thr and now >= self.cooldown_until:
            self._emg_pulse_until = now + (self.cfg.emg_pulse_ms / 1000.0)
        self._emg_prev = raw_emg

        if now < self.cooldown_until:
            emg_score = 0.0
        elif now < self._emg_pulse_until:
            emg_score = 1.0
        else:
            emg_score = 0.0

        emg_ok = emg_score >= thr
        if (
            self.cfg.dwell_actuates
            and self.cfg.dwell_required
            and selected is not None
            and dwell_progress >= 1.0
            and now >= self.cooldown_until
        ):
            emg_score = 1.0
            emg_ok = True

        decision = self.fusion.decide(
            selected_device=selected.target_id if selected else None,
            gaze_confidence=gaze.confidence if gaze.face_found else 0.0,
            emg_score=emg_score,
            emg_confirmed=emg_ok,
            ambiguous=bool(candidate and candidate.ambiguous),
        )

        changed = (
            self.last_decision is None
            or decision.action != self.last_decision.action
            or decision.selected_device != self.last_decision.selected_device
        )
        if changed:
            self.metrics.on_decision(decision.action, decision.reason)
            self.logger.log(
                {
                    "action": decision.action,
                    "selected_device": decision.selected_device,
                    "selected_label": selected.label if selected else None,
                    "reason": decision.reason,
                    "yaw": round(gaze.yaw, 3),
                    "emg": round(emg_score, 3),
                    "emg_mode": self.cfg.emg_mode,
                    "mode": "yolo" if prefer_detections else "slots",
                    "n_detections": len(detections),
                }
            )
            if self.publisher is not None:
                self.publisher.publish_decision(
                    {
                        "action": decision.action,
                        "device": decision.selected_device,
                        "label": selected.label if selected else None,
                        "reason": decision.reason,
                        "yaw": round(gaze.yaw, 3),
                        "emg": round(emg_score, 3),
                    }
                )
            self.last_decision = decision

        actuation = self.hub.on_decision(
            decision.action,
            decision.selected_device,
            selected.label if selected else None,
        )
        if actuation is not None:
            self.metrics.on_actuation()
            self.emg.clear()
            self._emg_pulse_until = 0.0
            self.cooldown_until = now + max(self.cfg.act_cooldown_seconds, 0.4)
            if selected is not None:
                self._lock_key = _lock_token(selected)
            self._away_t0 = None
            self.dwell_id = None
            self.dwell_t0 = None
            self.sticky_id = None
            self._dwell_target = None
            self._dwell_grace_until = None
            self._dwell_frozen = None
            if self.publisher is not None:
                self.publisher.publish_actuate(
                    {
                        "device_id": actuation.device_id,
                        "label": actuation.label,
                        "command": actuation.command,
                        "state": actuation.new_state,
                    }
                )

        return TickResult(
            decision=decision,
            selected=selected,
            candidate=candidate,
            dwell_progress=dwell_progress,
            emg_score=emg_score,
            actuation=actuation,
            changed=changed,
        )
