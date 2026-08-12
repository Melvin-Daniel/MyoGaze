"""Offline mock scene — no webcam required."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .detector import DetectedObject
from .types import GazeEstimate
from .selector import slot_overlays


@dataclass
class MockFrame:
    """One simulated product-demo frame."""

    t: float
    gaze: GazeEstimate
    detections: list[DetectedObject]
    emg_score: float
    note: str
    prefer_detections: bool = False


@dataclass
class ScenarioStep:
    duration: float
    yaw: float
    emg: float
    note: str
    face_found: bool = True


# Product demo script covering Act + Abstain cases (guide-ready).
DEFAULT_SCENARIO: list[ScenarioStep] = [
    ScenarioStep(1.0, 0.00, 0.0, "Idle looking straight (Fan) — should ABSTAIN"),
    ScenarioStep(1.2, -0.45, 0.0, "Look LEFT at Lamp — dwell, no EMG — ABSTAIN"),
    ScenarioStep(0.5, -0.45, 1.0, "Lamp selected + EMG confirm — ACT Lamp"),
    ScenarioStep(0.8, -0.45, 0.0, "Hold gaze, EMG released — ABSTAIN"),
    ScenarioStep(1.0, 0.00, 0.0, "Return to Fan center — ABSTAIN"),
    ScenarioStep(1.0, 0.48, 0.0, "Look RIGHT at Plug — dwell only — ABSTAIN"),
    ScenarioStep(0.5, 0.48, 1.0, "Plug + EMG — ACT Plug"),
    ScenarioStep(0.7, 0.48, 0.0, "EMG gone — ABSTAIN"),
    ScenarioStep(0.9, 0.00, 1.0, "EMG with no face/gaze — must ABSTAIN", face_found=False),
    ScenarioStep(1.0, 0.00, 0.0, "Settle — ABSTAIN"),
    ScenarioStep(1.0, -0.42, 0.0, "Lamp again — dwell"),
    ScenarioStep(0.5, -0.42, 1.0, "Second Lamp toggle (OFF) — ACT"),
    ScenarioStep(0.8, 0.00, 0.0, "Done — idle"),
]


def render_mock_frame(
    w: int,
    h: int,
    yaw: float,
    pitch: float = 0.0,
    emg: float = 0.0,
    note: str = "",
    hub_states: dict[str, bool] | None = None,
    selected_id: str | None = None,
    candidate_id: str | None = None,
    dwell_progress: float = 0.0,
    action: str = "ABSTAIN",
) -> tuple[np.ndarray, GazeEstimate, list[DetectedObject]]:
    """Draw a synthetic room + face proxy + Lamp/Fan/Plug slots."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    # Soft gradient background (product look, not flat black)
    for y in range(h):
        shade = int(28 + 40 * (y / max(h, 1)))
        frame[y, :] = (shade + 8, shade, shade + 18)

    # Title bar
    cv2.rectangle(frame, (0, 0), (w, 56), (20, 24, 36), -1)
    cv2.putText(
        frame,
        "NeuroShift  |  MOCK DEMO (no camera)",
        (16, 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        (220, 230, 255),
        2,
    )

    # Face proxy circle that shifts with yaw
    cx = int(w * (0.5 + 0.18 * yaw))
    cy = int(h * (0.62 + 0.08 * pitch))
    cv2.circle(frame, (cx, cy), 48, (60, 90, 140), -1)
    cv2.circle(frame, (cx, cy), 48, (180, 200, 255), 2)
    # Eyes
    cv2.circle(frame, (cx - 16, cy - 8), 6, (240, 240, 240), -1)
    cv2.circle(frame, (cx + 16, cy - 8), 6, (240, 240, 240), -1)
    cv2.circle(frame, (cx - 16, cy - 8), 2, (20, 20, 20), -1)
    cv2.circle(frame, (cx + 16, cy - 8), 2, (20, 20, 20), -1)

    gaze = GazeEstimate(
        face_found=True,
        nose_xy=(float(cx), float(cy)),
        yaw=float(yaw),
        pitch=float(pitch),
        confidence=0.92,
        raw_yaw=float(yaw),
        raw_pitch=float(pitch),
    )

    detections: list[DetectedObject] = []
    hub_states = hub_states or {}
    for t in slot_overlays(w, h):
        assert t.xyxy is not None
        x0, y0, x1, y1 = t.xyxy
        on = hub_states.get(t.target_id, False)
        is_sel = selected_id == t.target_id
        is_cand = candidate_id == t.target_id
        color = (0, 255, 120) if is_sel else (0, 210, 255) if is_cand else (90, 90, 110)
        thick = 3 if is_sel or is_cand else 2
        cv2.rectangle(frame, (x0, y0), (x1, y1), color, thick)
        label = f"{t.label} [{'ON' if on else 'off'}]"
        cv2.putText(frame, label, (x0 + 8, y0 + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        if is_cand or is_sel:
            bar_y0 = min(y1 + 8, h - 12)
            fill = int(x0 + (x1 - x0) * max(0.0, min(1.0, dwell_progress)))
            cv2.rectangle(frame, (x0, bar_y0), (x1, bar_y0 + 8), (40, 40, 40), -1)
            cv2.rectangle(frame, (x0, bar_y0), (fill, bar_y0 + 8), color, -1)

    # Aim ray
    aim_x = int(w * (0.5 + 0.42 * yaw))
    aim_y = int(h * 0.32)
    cv2.line(frame, (cx, cy), (aim_x, aim_y), (0, 200, 255), 2)
    cv2.circle(frame, (aim_x, aim_y), 7, (0, 200, 255), -1)

    # EMG strip
    ex, ey, ew, eh = 16, h - 90, 240, 44
    cv2.rectangle(frame, (ex, ey), (ex + ew, ey + eh), (25, 25, 25), -1)
    thr = int(ey + eh * 0.5)
    cv2.line(frame, (ex, thr), (ex + ew, thr), (80, 80, 200), 1)
    fill_h = int(eh * max(0.0, min(1.0, emg)))
    cv2.rectangle(frame, (ex, ey + eh - fill_h), (ex + 28, ey + eh), (0, 255, 160), -1)
    cv2.putText(
        frame,
        f"EMG {emg:.2f}  |  {action}",
        (ex + 40, ey + 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (200, 255, 220),
        1,
    )

    if note:
        cv2.putText(frame, note[:90], (16, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (210, 220, 230), 1)

    return frame, gaze, detections


def iter_scenario(
    scenario: list[ScenarioStep] | None = None,
    fps: float = 20.0,
):
    """Yield (t, step) samples at fps across the scenario timeline."""
    steps = scenario or DEFAULT_SCENARIO
    t = 0.0
    dt = 1.0 / max(fps, 1.0)
    for step in steps:
        end = t + step.duration
        while t < end - 1e-9:
            yield t, step
            t += dt
