"""Stand-in home devices for laptop-cam week (replace with YOLO boxes later)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Device:
    device_id: str
    label: str
    # Normalized screen regions [x0,y0,x1,y1] in 0..1 — left/center/right stand-ins
    region: tuple[float, float, float, float]


# Place real lamp/fan later; for now map head yaw to these slots
DEMO_DEVICES = [
    Device("lamp", "Lamp (look LEFT)", (0.05, 0.12, 0.32, 0.88)),
    Device("fan", "Fan (look STRAIGHT)", (0.34, 0.12, 0.66, 0.88)),
    Device("plug", "Plug (look RIGHT)", (0.68, 0.12, 0.95, 0.88)),
]


def select_by_yaw(
    yaw: float,
    devices: list[Device] = DEMO_DEVICES,
    side_threshold: float = 0.20,
    hysteresis: float = 0.10,
    current_id: str | None = None,
) -> Device | None:
    """
    Map head yaw [-1,1] to left/center/right with hysteresis.

    Neg yaw = left (Lamp), pos = right (Plug). Once a slot is active, you must
    cross the boundary by an extra `hysteresis` margin before switching — stops
    Fan↔Lamp flicker near the threshold.
    """
    left, center, right = devices[0], devices[1], devices[2]

    if current_id == left.device_id:
        # Stay on Lamp until clearly back toward center/right
        if yaw > -side_threshold + hysteresis:
            return center if yaw < side_threshold else right
        return left

    if current_id == right.device_id:
        if yaw < side_threshold - hysteresis:
            return center if yaw > -side_threshold else left
        return right

    if current_id == center.device_id:
        if yaw <= -side_threshold - hysteresis:
            return left
        if yaw >= side_threshold + hysteresis:
            return right
        return center

    # No sticky target yet
    if yaw <= -side_threshold:
        return left
    if yaw >= side_threshold:
        return right
    return center
