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
    """Gaze-select + EMG-confirm state machine (camera-agnostic)."""

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
        self.last_decision: Decision | None = None
        self.cooldown_until = 0.0
        self._emg_prev = 0.0
        self._emg_pulse_until = 0.0

    def reset_gaze_state(self) -> None:
        self.dwell_id = None
        self.dwell_t0 = None
        self.sticky_id = None

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
            )
            if candidate is not None:
                self.sticky_id = candidate.target_id
                if self.dwell_id != candidate.target_id:
                    self.dwell_id = candidate.target_id
                    self.dwell_t0 = now
                    dwell_progress = 0.0
                elif self.dwell_t0 is not None:
                    dwell_progress = (now - self.dwell_t0) / self.cfg.dwell_seconds
                    if dwell_progress >= 1.0:
                        selected = candidate
                        dwell_progress = 1.0
            else:
                self.reset_gaze_state()
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

        decision = self.fusion.decide(
            selected_device=selected.target_id if selected else None,
            gaze_confidence=gaze.confidence if gaze.face_found else 0.0,
            emg_score=emg_score,
            emg_confirmed=emg_ok,
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
            self.cooldown_until = now + self.cfg.act_cooldown_seconds
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
