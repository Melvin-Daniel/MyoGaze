"""Live camera preview. Lock state is shown in the UI, not painted on the picture."""

from __future__ import annotations

import numpy as np

from ..selector import Target


def draw_live_frame(
    frame: np.ndarray,
    *,
    yaw: float,
    pitch: float = 0.0,
    nose_xy: tuple[float, float] | None,
    candidate: Target | None,
    selected: Target | None,
    dwell_progress: float,
    emg_score: float,
    action: str,
    hub_states: dict[str, bool],
    prefer_slots: bool,
    detections_xyxy: list[tuple[tuple[int, int, int, int], str, str, float]] | None = None,
) -> np.ndarray:
    del yaw, pitch, nose_xy, candidate, selected, dwell_progress, emg_score, action
    del hub_states, prefer_slots, detections_xyxy
    return frame
