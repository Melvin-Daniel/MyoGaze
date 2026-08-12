"""Draw live camera overlays for the Control App preview stream."""

from __future__ import annotations

import cv2
import numpy as np

from ..selector import Target, slot_overlays


def draw_live_frame(
    frame: np.ndarray,
    *,
    yaw: float,
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
    """Return annotated BGR frame (mutates a copy)."""
    out = frame.copy()
    h, w = out.shape[:2]

    # Soft top bar
    cv2.rectangle(out, (0, 0), (w, 48), (20, 28, 24), -1)
    cv2.putText(
        out,
        f"NeuroShift LIVE  |  {action}  |  EMG {emg_score:.2f}",
        (14, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (220, 240, 230),
        2,
    )

    if prefer_slots or not detections_xyxy:
        for t in slot_overlays(w, h):
            assert t.xyxy is not None
            x0, y0, x1, y1 = t.xyxy
            on = hub_states.get(t.target_id, False)
            is_sel = selected and selected.target_id == t.target_id
            is_cand = candidate and candidate.target_id == t.target_id
            color = (80, 220, 120) if is_sel else (60, 200, 255) if is_cand else (90, 90, 90)
            thick = 3 if (is_sel or is_cand) else 1
            cv2.rectangle(out, (x0, y0), (x1, y1), color, thick)
            cv2.putText(
                out,
                f"{t.label} [{'ON' if on else 'off'}]",
                (x0 + 8, y0 + 26),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )
            if is_cand or is_sel:
                _dwell_bar(out, t.xyxy, dwell_progress, bool(is_sel))
    else:
        for xyxy, label, obj_id, conf in detections_xyxy:
            x0, y0, x1, y1 = xyxy
            on = hub_states.get(obj_id, False)
            is_sel = selected and selected.target_id == obj_id
            is_cand = candidate and candidate.target_id == obj_id
            color = (80, 220, 120) if is_sel else (60, 200, 255) if is_cand else (40, 180, 200)
            cv2.rectangle(out, (x0, y0), (x1, y1), color, 2 if is_cand or is_sel else 1)
            cv2.putText(
                out,
                f"{label} {conf:.2f} [{'ON' if on else 'off'}]",
                (x0, max(20, y0 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
            )
            if is_cand or is_sel:
                _dwell_bar(out, xyxy, dwell_progress, bool(is_sel))

    if nose_xy is not None:
        nx, ny = int(nose_xy[0]), int(nose_xy[1])
        aim = selected or candidate
        if aim is not None and aim.xyxy is not None:
            ax0, ay0, ax1, ay1 = aim.xyxy
            aim_x, aim_y = (ax0 + ax1) // 2, (ay0 + ay1) // 2
        else:
            aim_x = int(w * (0.5 + 0.42 * yaw))
            aim_y = int(h * 0.35)
        ray = (80, 220, 120) if selected else (60, 200, 255)
        cv2.circle(out, (nx, ny), 6, (40, 180, 255), -1)
        cv2.line(out, (nx, ny), (aim_x, aim_y), ray, 2)
        cv2.circle(out, (aim_x, aim_y), 7, ray, -1)

    tip = "Look at a boxed object, dwell green, then Confirm"
    if prefer_slots:
        tip = "LEFT Lamp | STRAIGHT Fan | RIGHT Plug | then Confirm"
    cv2.putText(out, tip, (14, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 200, 190), 1)
    return out


def _dwell_bar(
    frame: np.ndarray,
    xyxy: tuple[int, int, int, int],
    progress: float,
    selected: bool,
) -> None:
    x0, y0, x1, y1 = xyxy
    p = max(0.0, min(1.0, progress))
    bar_y0 = min(y1 + 6, frame.shape[0] - 10)
    bar_y1 = bar_y0 + 8
    cv2.rectangle(frame, (x0, bar_y0), (x1, bar_y1), (40, 40, 40), -1)
    fill_x = int(x0 + (x1 - x0) * p)
    color = (80, 220, 120) if selected or p >= 1.0 else (60, 200, 255)
    if fill_x > x0:
        cv2.rectangle(frame, (x0, bar_y0), (fill_x, bar_y1), color, -1)
