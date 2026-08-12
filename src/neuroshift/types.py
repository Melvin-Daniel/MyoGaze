"""Shared lightweight types (no MediaPipe import)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GazeEstimate:
    face_found: bool
    nose_xy: tuple[float, float] | None
    # yaw: negative = look left on mirrored screen, positive = look right
    yaw: float
    pitch: float
    confidence: float
    raw_yaw: float = 0.0
    raw_pitch: float = 0.0
