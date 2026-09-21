"""Shared lightweight types (no MediaPipe import)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GazeEstimate:
    face_found: bool
    nose_xy: tuple[float, float] | None
    # Combined look direction (eyes preferred, head as fallback)
    # yaw: negative = look left on mirrored screen, positive = look right
    yaw: float
    pitch: float
    confidence: float
    raw_yaw: float = 0.0
    raw_pitch: float = 0.0
    eye_yaw: float = 0.0
    eye_pitch: float = 0.0
    head_yaw: float = 0.0
    head_pitch: float = 0.0
    iris_xy: tuple[float, float] | None = None
    has_iris: bool = False
    # Eye center in image pixels. The look is a ray from here, not a short point.
    eye_xy: tuple[float, float] | None = None
    # Gaze point in image pixels, starting at the eyes — not the frame center.
    aim_xy: tuple[float, float] | None = None
    # Face ellipse (cx, cy, rx, ry) in pixels. Appliance boxes on it are dropped.
    face_oval: tuple[float, float, float, float] | None = None
