"""Map head yaw / gaze proxy onto detected objects or demo slots."""

from __future__ import annotations

from dataclasses import dataclass

from .devices import DEMO_DEVICES, Device, select_by_yaw
from .detector import DetectedObject
from .types import GazeEstimate


@dataclass
class Target:
    target_id: str
    label: str
    kind: str  # "detected" | "slot"
    xyxy: tuple[int, int, int, int] | None = None
    score: float = 0.0


def _yaw_to_screen_x(yaw: float, width: int, strength: float = 0.48) -> float:
    """Project head yaw to a horizontal aim point on the image."""
    return width * (0.5 + strength * max(-1.0, min(1.0, yaw)))


def _aim_point(gaze: GazeEstimate, frame_w: int, frame_h: int) -> tuple[float, float]:
    """Blend nose position with yaw so near objects (phone in hand) are easier to hit."""
    yaw_x = _yaw_to_screen_x(gaze.yaw, frame_w)
    yaw_y = frame_h * (0.38 + 0.12 * max(-1.0, min(1.0, gaze.pitch)))
    if gaze.nose_xy is None:
        return yaw_x, yaw_y
    nx, ny = gaze.nose_xy
    # Nose pulls aim toward where the face is looking in-frame
    return 0.45 * nx + 0.55 * yaw_x, 0.35 * ny + 0.65 * yaw_y


def select_target(
    gaze: GazeEstimate,
    detections: list[DetectedObject],
    frame_w: int,
    frame_h: int,
    side_threshold: float,
    prefer_detections: bool = True,
    hysteresis: float = 0.10,
    sticky_id: str | None = None,
) -> Target | None:
    if not gaze.face_found:
        return None

    if prefer_detections and detections:
        aim_x, aim_y = _aim_point(gaze, frame_w, frame_h)
        scored: list[tuple[float, DetectedObject]] = []
        for obj in detections:
            cx, cy = obj.center
            x0, y0, x1, y1 = obj.xyxy
            # Expand hit box slightly so small handheld objects are easier
            pad_x = 0.12 * (x1 - x0)
            pad_y = 0.12 * (y1 - y0)
            inside = (x0 - pad_x) <= aim_x <= (x1 + pad_x) and (y0 - pad_y) <= aim_y <= (y1 + pad_y)
            dist = ((cx - aim_x) ** 2 + (cy - aim_y) ** 2) ** 0.5 / max(frame_w, 1)
            area = ((x1 - x0) * (y1 - y0)) / max(frame_w * frame_h, 1)
            score = dist - 0.14 * min(area, 0.30)
            if inside:
                score -= 0.28
            if sticky_id and obj.obj_id == sticky_id:
                score -= 0.12
            scored.append((score, obj))

        if scored:
            scored.sort(key=lambda t: t[0])
            best_score, best = scored[0]
            # Allow a bit more reach so small phones are selectable
            if best_score < 0.48:
                return Target(
                    target_id=best.obj_id,
                    label=best.appliance or best.label,
                    kind="detected",
                    xyxy=best.xyxy,
                    score=1.0 - best_score,
                )

    # Fallback: virtual Lamp/Fan/Plug slots (with hysteresis)
    slot: Device | None = select_by_yaw(
        gaze.yaw,
        side_threshold=side_threshold,
        hysteresis=hysteresis,
        current_id=sticky_id if (sticky_id in {d.device_id for d in DEMO_DEVICES}) else None,
    )
    if slot is None:
        return None
    x0 = int(slot.region[0] * frame_w)
    y0 = int(slot.region[1] * frame_h)
    x1 = int(slot.region[2] * frame_w)
    y1 = int(slot.region[3] * frame_h)
    return Target(
        target_id=slot.device_id,
        label=slot.label.split("(")[0].strip(),
        kind="slot",
        xyxy=(x0, y0, x1, y1),
        score=gaze.confidence,
    )


def slot_overlays(frame_w: int, frame_h: int) -> list[Target]:
    out: list[Target] = []
    for d in DEMO_DEVICES:
        x0 = int(d.region[0] * frame_w)
        y0 = int(d.region[1] * frame_h)
        x1 = int(d.region[2] * frame_w)
        y1 = int(d.region[3] * frame_h)
        out.append(
            Target(
                target_id=d.device_id,
                label=d.label.split("(")[0].strip(),
                kind="slot",
                xyxy=(x0, y0, x1, y1),
            )
        )
    return out
