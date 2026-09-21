"""Map head yaw / gaze proxy onto detected objects or demo slots."""

from __future__ import annotations

from dataclasses import dataclass

from .devices import DEMO_DEVICES, Device, select_by_yaw
from .detector import DetectedObject, _iou
from .gaze import aim_from_eyes, look_axes
from .types import GazeEstimate


@dataclass
class Target:
    target_id: str
    label: str
    kind: str  # "detected" | "slot"
    xyxy: tuple[int, int, int, int] | None = None
    score: float = 0.0
    ambiguous: bool = False
    rival_label: str | None = None


_FACE_LABELS = {
    "fan",
    "lamp",
    "cup",
    "bottle",
    "led bulb",
    "desk lamp",
    "table lamp",
    "light bulb",
    "light",
}


def box_on_face(xyxy: tuple[int, int, int, int], face_oval: tuple[float, float, float, float]) -> bool:
    """True when a box center sits in the face ellipse, or furniture wraps the head."""
    cx, cy, rx, ry = face_oval
    if rx < 1 or ry < 1:
        return False
    x0, y0, x1, y1 = xyxy
    box_cx = (x0 + x1) / 2.0
    box_cy = (y0 + y1) / 2.0
    nx = (box_cx - cx) / rx
    ny = (box_cy - cy) / ry
    # Center in the face, not a fan held against the cheek that only clips the oval.
    if nx * nx + ny * ny <= 1.0:
        return True
    # A wardrobe/mirror box that swallows the head is not a held lamp.
    if x0 <= cx <= x1 and y0 <= cy <= y1:
        bw, bh = max(x1 - x0, 1), max(y1 - y0, 1)
        if bw >= 2.8 * rx or bh >= 2.8 * ry:
            return True
    return False


def box_on_body(xyxy: tuple[int, int, int, int], face_oval: tuple[float, float, float, float]) -> bool:
    """True for a badge / lanyard / shirt highlight sitting under the face."""
    if box_on_face(xyxy, face_oval):
        return True
    cx, cy, rx, ry = face_oval
    if rx < 1 or ry < 1:
        return False
    x0, y0, x1, y1 = xyxy
    box_cx = (x0 + x1) / 2.0
    box_cy = (y0 + y1) / 2.0
    bw, bh = max(x1 - x0, 1), max(y1 - y0, 1)
    # Shoulders are wider than the face. A desk lamp sits further out.
    if abs(box_cx - cx) > rx * 1.9:
        return False
    if bw >= 2.4 * rx and bh >= 2.4 * ry:
        return False
    return (cy + 0.15 * ry) <= box_cy <= (cy + ry * 7.2)


def drop_boxes_on_face(
    detections: list[DetectedObject],
    face_oval: tuple[float, float, float, float] | None,
) -> list[DetectedObject]:
    """Lamp boxes on the face, chest, or lanyard are false matches."""
    if not face_oval:
        return detections
    kept: list[DetectedObject] = []
    for det in detections:
        blob = f"{det.label or ''} {det.appliance or ''}".lower()
        if not (
            any(token in blob for token in _FACE_LABELS)
            or any(token in blob for token in ("lamp", "bulb", "light"))
        ):
            kept.append(det)
            continue
        if box_on_face(det.xyxy, face_oval):
            # Globe matcher (~0.88): a shown bulb, including one held in front of the face.
            if det.conf >= 0.82:
                kept.append(det)
                continue
            continue
        # Globe matcher (~0.88) is a shown bulb. Weak YOLO on a badge is not.
        if det.conf < 0.82 and box_on_body(det.xyxy, face_oval):
            continue
        kept.append(det)
    return kept


def keep_lamp_detections(detections: list[DetectedObject]) -> list[DetectedObject]:
    """Phase 1 only locks a lamp. Phones, fans, and bottles must not steal gaze."""
    lamps: list[DetectedObject] = []
    for det in detections:
        blob = f"{det.label or ''} {det.appliance or ''}".lower()
        if any(token in blob for token in ("lamp", "bulb", "light")):
            lamps.append(det)
    return lamps


def drop_lamps_on_people(
    detections: list[DetectedObject],
    people: list[tuple[int, int, int, int]] | None,
    frame_w: int = 0,
    frame_h: int = 0,
) -> list[DetectedObject]:
    """Drop lamp boxes that sit on a face / head, including a second person."""
    if not people:
        return detections
    from .detector import _on_any_head

    kept: list[DetectedObject] = []
    for det in detections:
        blob = f"{det.label or ''} {det.appliance or ''}".lower()
        if (
            any(token in blob for token in ("lamp", "bulb", "light"))
            and det.conf < 0.82
            and _on_any_head(det.xyxy, people, frame_w, frame_h)
        ):
            continue
        kept.append(det)
    return kept


def _point_hits(obj: DetectedObject, ax: float, ay: float) -> bool:
    x0, y0, x1, y1 = obj.xyxy
    bw = max(x1 - x0, 1)
    bh = max(y1 - y0, 1)
    pad_x = min(0.08 * bw, 16)
    pad_y = min(0.08 * bh, 16)
    return (x0 - pad_x) <= ax <= (x1 + pad_x) and (y0 - pad_y) <= ay <= (y1 + pad_y)


def _ray_enter(
    origin: tuple[float, float],
    direction: tuple[float, float],
    xyxy: tuple[int, int, int, int],
    pad: float,
) -> float | None:
    """Distance along the look ray to the box, or None if the ray misses it."""
    ox, oy = origin
    dx, dy = direction
    x0, y0, x1, y1 = xyxy
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    tmin, tmax = 0.0, 1e6
    for origin_c, dir_c, lo, hi in ((ox, dx, x0, x1), (oy, dy, y0, y1)):
        if abs(dir_c) < 1e-6:
            if origin_c < lo or origin_c > hi:
                return None
            continue
        t1 = (lo - origin_c) / dir_c
        t2 = (hi - origin_c) / dir_c
        if t1 > t2:
            t1, t2 = t2, t1
        tmin = max(tmin, t1)
        tmax = min(tmax, t2)
        if tmin > tmax:
            return None
    if tmax < 0:
        return None
    return max(tmin, 0.0)


def _select_along_ray(
    gaze: GazeEstimate,
    detections: list[DetectedObject],
    frame_w: int,
    frame_h: int,
    sticky_id: str | None,
    ambiguity_margin: float,
) -> Target | None:
    """A glance toward an object counts, even if the short aim point stops on the face."""
    assert gaze.eye_xy is not None
    # Iris wins when mirrored head pose points the other way. Same-side looks stay on the blend.
    yaw, pitch = look_axes(gaze)
    dx = yaw * frame_w
    dy = pitch * frame_h
    # Looking at the real object turns the eyes sideways. The preview sits on
    # the screen, so that same look is higher or lower than the box in the
    # camera picture — allow some vertical slack, not the whole frame.
    side_glance = abs(yaw) >= 0.12 and abs(yaw) >= abs(pitch)
    if side_glance:
        dy = 0.0
    if (dx * dx + dy * dy) ** 0.5 < (0.035 if sticky_id else 0.055) * frame_w:
        return None
    hits: list[tuple[float, DetectedObject]] = []
    for obj in detections:
        x0, y0, x1, y1 = obj.xyxy
        bh = max(y1 - y0, 1)
        pad_x = max(14.0, 0.18 * max(x1 - x0, 1))
        pad_y = max(36.0, 0.45 * bh) if side_glance else max(36.0, 0.40 * bh)
        entered = _ray_enter(
            gaze.eye_xy,
            (dx, dy),
            (int(x0 - pad_x), int(y0 - pad_y), int(x1 + pad_x), int(y1 + pad_y)),
            0,
        )
        if entered is None:
            continue
        if sticky_id and obj.obj_id == sticky_id:
            entered -= 0.04
        hits.append((entered, obj))
    if not hits:
        return None
    hits.sort(key=lambda item: item[0])
    best_t, best = hits[0]
    rival_label = None
    ambiguous = False
    if len(hits) >= 2:
        second_t, second = hits[1]
        same_object = _iou(best.xyxy, second.xyxy) >= 0.12
        if not same_object and (second_t - best_t) < ambiguity_margin:
            ambiguous = True
            rival_label = second.appliance or second.label
    return Target(
        target_id=best.obj_id,
        label=best.appliance or best.label,
        kind="detected",
        xyxy=best.xyxy,
        score=1.0 / (1.0 + max(best_t, 0.0)),
        ambiguous=ambiguous,
        rival_label=rival_label,
    )


def _select_by_angle(
    gaze: GazeEstimate,
    detections: list[DetectedObject],
    frame_w: int,
    frame_h: int,
    sticky_id: str | None,
) -> Target | None:
    """A steady glance toward an object counts, even if the point stops short of the box."""
    assert gaze.eye_xy is not None
    yaw, pitch = look_axes(gaze)
    look_x = yaw * frame_w
    look_y = pitch * frame_h
    mag = (look_x * look_x + look_y * look_y) ** 0.5
    if mag < (0.035 if sticky_id else 0.055) * frame_w:
        return None
    scored: list[tuple[float, DetectedObject]] = []
    for obj in detections:
        cx, cy = obj.center
        vx = cx - gaze.eye_xy[0]
        vy = cy - gaze.eye_xy[1]
        dist = (vx * vx + vy * vy) ** 0.5
        if dist < 0.07 * frame_w:
            continue
        align = (look_x * vx + look_y * vy) / (mag * dist)
        if sticky_id and obj.obj_id == sticky_id:
            align += 0.06
        scored.append((align, obj))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    best_align, best = scored[0]
    if best_align < (0.72 if sticky_id else 0.82):
        return None
    rival_label = None
    ambiguous = False
    if len(scored) >= 2:
        second_align, second = scored[1]
        same_object = _iou(best.xyxy, second.xyxy) >= 0.12
        if not same_object and second_align >= 0.82 and (best_align - second_align) < 0.08:
            ambiguous = True
            rival_label = second.appliance or second.label
    return Target(
        target_id=best.obj_id,
        label=best.appliance or best.label,
        kind="detected",
        xyxy=best.xyxy,
        score=best_align,
        ambiguous=ambiguous,
        rival_label=rival_label,
    )


def _select_at_aim(
    gaze: GazeEstimate,
    detections: list[DetectedObject],
    frame_w: int,
    frame_h: int,
    sticky_id: str | None,
    ambiguity_margin: float,
) -> Target | None:
    """Hit-test the eye-anchored gaze point. A nearby box is not a look."""
    assert gaze.aim_xy is not None
    aim_x, aim_y = gaze.aim_xy
    scored: list[tuple[float, DetectedObject]] = []
    for obj in detections:
        if _ceiling_fringe(obj, aim_x, aim_y, frame_w, frame_h):
            continue
        if not _point_hits(obj, aim_x, aim_y):
            continue
        cx, cy = obj.center
        dist = ((cx - aim_x) ** 2 + (cy - aim_y) ** 2) ** 0.5 / max(frame_w, 1)
        score = dist - 0.28
        if sticky_id and obj.obj_id == sticky_id:
            score -= 0.08
        scored.append((score, obj))
    if not scored:
        return None
    scored.sort(key=lambda t: t[0])
    best_score, best = scored[0]
    if best_score >= 0.48:
        return None
    rival_label = None
    ambiguous = False
    if len(scored) >= 2:
        second_score, second = scored[1]
        if second_score < 0.48 and (second_score - best_score) < ambiguity_margin:
            ambiguous = True
            rival_label = second.appliance or second.label
    return Target(
        target_id=best.obj_id,
        label=best.appliance or best.label,
        kind="detected",
        xyxy=best.xyxy,
        score=1.0 - best_score,
        ambiguous=ambiguous,
        rival_label=rival_label,
    )


def _yaw_to_screen_x(yaw: float, width: int, strength: float = 0.48) -> float:
    """Project head yaw to a horizontal aim point on the image."""
    return width * (0.5 + strength * max(-1.0, min(1.0, yaw)))


def _aim_point(gaze: GazeEstimate, frame_w: int, frame_h: int) -> tuple[float, float]:
    """Project look direction onto the image. Eyes, not the nose, drive the aim."""
    x = frame_w * (0.5 + 0.62 * max(-1.0, min(1.0, gaze.yaw)))
    y = frame_h * (0.42 + 0.38 * max(-1.0, min(1.0, gaze.pitch)))
    return x, y


def _box_area(obj: DetectedObject, frame_w: int, frame_h: int) -> float:
    x0, y0, x1, y1 = obj.xyxy
    return ((x1 - x0) * (y1 - y0)) / max(frame_w * frame_h, 1)


def _ceiling_fringe(
    obj: DetectedObject,
    aim_x: float,
    aim_y: float,
    frame_w: int,
    frame_h: int,
) -> bool:
    """A large light stuck to the top of the frame.

    The camera-look point sits a little high (y ≈ 0.42h), so a ceiling box
    that hangs down over the lens contains that point even though the user is
    looking into empty air. A lamp they actually look at has the aim near the
    box center, and a phone held on the axis does not start at the top edge.
    """
    del aim_x
    x0, y0, x1, y1 = obj.xyxy
    bh = max(y1 - y0, 1)
    area = _box_area(obj, frame_w, frame_h)
    if area < 0.08 or y0 > frame_h * 0.10:
        return False
    cy = (y0 + y1) / 2.0
    if cy >= frame_h * 0.42:
        return False
    rel_y = (aim_y - y0) / bh
    # Aim near the middle of the box — they are looking at the lamp.
    if rel_y < 0.62 and abs(cy - aim_y) <= 0.35 * bh:
        return False
    return rel_y >= 0.62


def _on_camera_axis(
    obj: DetectedObject,
    aim_x: float,
    aim_y: float,
    frame_w: int,
    frame_h: int,
) -> bool:
    """Handheld object in front of the lens.

    Neutral aim is y = h*(0.42+0.38*pitch), which lands in the empty wall
    just above a phone held in front of the face. That is still a look at
    the phone: it sits on the camera axis, under the aim, not at the ceiling.
    """
    x0, y0, x1, y1 = obj.xyxy
    area = _box_area(obj, frame_w, frame_h)
    if area >= 0.35:
        return False
    cx, cy = obj.center
    pad_x = max(0.05 * frame_w, 0.12 * (x1 - x0))
    if not (x0 - pad_x <= aim_x <= x1 + pad_x):
        return False
    # Below the look, not a light whose mass sits above it.
    if cy < aim_y - 0.06 * frame_h:
        return False
    if y0 > aim_y + 0.22 * frame_h:
        return False
    if cy > aim_y + 0.40 * frame_h:
        return False
    return True


def _look_iris(gaze: GazeEstimate) -> tuple[float, float]:
    """Iris vs the face. Not the mirrored screen yaw."""
    if gaze.has_iris:
        return float(gaze.eye_yaw), float(gaze.eye_pitch)
    return float(gaze.yaw), float(gaze.pitch)


def _image_look(gaze: GazeEstimate) -> tuple[float, float]:
    """Eyes and head in the camera picture, so a look at the real object counts."""
    if gaze.has_iris:
        yaw, pitch = float(gaze.eye_yaw), float(gaze.eye_pitch)
    else:
        yaw, pitch = float(gaze.yaw), float(gaze.pitch)
    hy, hp = float(gaze.head_yaw), float(gaze.head_pitch)
    if abs(hy) >= 0.10 and (abs(yaw) < 0.08 or yaw * hy >= 0):
        yaw = hy if abs(yaw) < 0.08 else 0.50 * yaw + 0.50 * hy
    if abs(hp) >= 0.10 and (abs(pitch) < 0.08 or pitch * hp >= 0):
        pitch = hp if abs(pitch) < 0.08 else 0.50 * pitch + 0.50 * hp
    return yaw, pitch


def _face_anchor(gaze: GazeEstimate, frame_w: int, frame_h: int) -> tuple[float, float]:
    if gaze.face_oval:
        return gaze.face_oval[0], gaze.face_oval[1]
    if gaze.eye_xy:
        return gaze.eye_xy
    if gaze.nose_xy:
        return gaze.nose_xy
    return frame_w / 2.0, frame_h / 2.0


def _object_key(obj: DetectedObject) -> str:
    return (obj.appliance or obj.label or "").strip().lower()


def _sides_of_face(
    obj: DetectedObject,
    face_cx: float,
    face_cy: float,
    frame_w: int,
    frame_h: int,
) -> set[str]:
    """Sides of the face the box occupies. A low handheld fan is both right and below."""
    ox, oy = obj.center
    dx = (ox - face_cx) / max(frame_w, 1)
    dy = (oy - face_cy) / max(frame_h, 1)
    sides: set[str] = set()
    if dx > 0.06:
        sides.add("right")
    elif dx < -0.06:
        sides.add("left")
    if dy > 0.08:
        sides.add("below")
    elif dy < -0.08:
        sides.add("above")
    return sides


def _look_side(yaw: float, pitch: float, *, sticky: bool = False) -> str | None:
    """Which way the eyes and head look. None if they are on the camera."""
    dead_yaw = 0.10 if sticky else 0.14
    dead_pitch = 0.12 if sticky else 0.16
    if abs(yaw) < dead_yaw and abs(pitch) < dead_pitch:
        return None
    if abs(yaw) >= abs(pitch):
        return "right" if yaw > 0 else "left"
    return "below" if pitch > 0 else "above"


def _as_target(
    obj: DetectedObject,
    score: float,
    *,
    ambiguous: bool = False,
    rival_label: str | None = None,
) -> Target:
    return Target(
        target_id=obj.obj_id,
        label=obj.appliance or obj.label,
        kind="detected",
        xyxy=obj.xyxy,
        score=score,
        ambiguous=ambiguous,
        rival_label=rival_label,
    )


def select_by_world_look(
    gaze: GazeEstimate,
    detections: list[DetectedObject],
    frame_w: int,
    frame_h: int,
    sticky_id: str | None = None,
    look_templates: dict[str, tuple[float, float]] | None = None,
) -> Target | None:
    """Lock the object the eyes are aimed at in the room, not a box on the preview."""
    if not detections:
        return None
    yaw, pitch = _look_iris(gaze)
    face_cx, face_cy = _face_anchor(gaze, frame_w, frame_h)

    templates = {str(k).strip().lower(): (float(v[0]), float(v[1])) for k, v in (look_templates or {}).items()}
    if templates:
        scored: list[tuple[float, DetectedObject]] = []
        for obj in detections:
            tmpl = templates.get(_object_key(obj))
            if tmpl is None:
                continue
            dist = ((yaw - tmpl[0]) ** 2 + (pitch - tmpl[1]) ** 2) ** 0.5
            if sticky_id and obj.obj_id == sticky_id:
                dist -= 0.04
            scored.append((dist, obj))
        if scored:
            scored.sort(key=lambda item: item[0])
            best_d, best = scored[0]
            if best_d <= 0.38:
                ambiguous = False
                rival_label = None
                if len(scored) >= 2:
                    second_d, second = scored[1]
                    same = _iou(best.xyxy, second.xyxy) >= 0.12
                    if not same and second_d <= 0.38 and (second_d - best_d) < 0.08:
                        ambiguous = True
                        rival_label = second.appliance or second.label
                return _as_target(best, 1.0 / (1.0 + max(best_d, 0.0)), ambiguous=ambiguous, rival_label=rival_label)

    look = _look_side(*_image_look(gaze), sticky=bool(sticky_id))
    if look is None:
        return None
    hits: list[DetectedObject] = []
    for obj in detections:
        if look not in _sides_of_face(obj, face_cx, face_cy, frame_w, frame_h):
            continue
        # A ceiling fixture above the face is not a held lamp you are looking at.
        ox, oy = obj.center
        if look in ("left", "right") and oy < face_cy - 0.22 * frame_h:
            continue
        hits.append(obj)
    if not hits:
        return None
    unique: list[DetectedObject] = []
    for obj in hits:
        if any(_iou(obj.xyxy, other.xyxy) >= 0.12 for other in unique):
            continue
        unique.append(obj)
    if len(unique) >= 2:
        rival = unique[1]
        return _as_target(
            unique[0],
            0.45,
            ambiguous=True,
            rival_label=rival.appliance or rival.label,
        )
    return _as_target(unique[0], 0.82)


def _is_lamp_det(obj: DetectedObject) -> bool:
    blob = f"{obj.label or ''} {obj.appliance or ''}".lower()
    return any(token in blob for token in ("lamp", "bulb", "light"))


def _gaze_aim_points(
    gaze: GazeEstimate, frame_w: int, frame_h: int
) -> list[tuple[float, float]]:
    """Candidate look points on the image — iris aim first, then projected look."""
    points: list[tuple[float, float]] = []
    if gaze.aim_xy is not None:
        points.append(gaze.aim_xy)
    yaw, pitch = look_axes(gaze)
    if gaze.eye_xy is not None:
        points.append(aim_from_eyes(gaze.eye_xy, yaw, pitch, frame_w, frame_h))
    points.append(_aim_point(gaze, frame_w, frame_h))
    return points


def _point_in_padded_box(
    xyxy: tuple[int, int, int, int],
    ax: float,
    ay: float,
    pad_frac: float,
) -> bool:
    x0, y0, x1, y1 = xyxy
    bw, bh = max(x1 - x0, 1), max(y1 - y0, 1)
    pad_x = pad_frac * bw
    pad_y = pad_frac * bh
    return (x0 - pad_x) <= ax <= (x1 + pad_x) and (y0 - pad_y) <= ay <= (y1 + pad_y)


def _aim_along_path_to(
    obj: DetectedObject,
    eye_xy: tuple[float, float],
    aim_xy: tuple[float, float],
    frame_w: int,
) -> float | None:
    """How far the aim has traveled from the eyes toward the object (0..1+).

    None when the aim is still on the face or off the look corridor.
    """
    ox, oy = obj.center
    ex, ey = eye_xy
    ax, ay = aim_xy
    vx, vy = ox - ex, oy - ey
    den = vx * vx + vy * vy
    if den < (0.06 * frame_w) ** 2:
        return None
    t = ((ax - ex) * vx + (ay - ey) * vy) / den
    # Still on / beside the eyes — not a look at the object yet.
    if t < 0.22:
        return None
    closest_x = ex + t * vx
    closest_y = ey + t * vy
    off = ((ax - closest_x) ** 2 + (ay - closest_y) ** 2) ** 0.5
    if off > 0.14 * frame_w:
        return None
    return t


def _aim_still_on_face(gaze: GazeEstimate, frame_w: int) -> bool:
    """True when the aim has not left the eyes yet (common with glasses / weak iris)."""
    if gaze.aim_xy is None:
        return True
    if gaze.eye_xy is None:
        return False
    ax, ay = gaze.aim_xy
    ex, ey = gaze.eye_xy
    return ((ax - ex) ** 2 + (ay - ey) ** 2) ** 0.5 < 0.10 * max(frame_w, 1)


def _select_lamp_by_gaze(
    gaze: GazeEstimate,
    lamps: list[DetectedObject],
    frame_w: int,
    frame_h: int,
    sticky_id: str | None,
) -> Target | None:
    """Lock a lamp when the look aims at it — not a casual stare at the camera."""
    if not lamps:
        return None
    pad = 0.58 if sticky_id else 0.45
    scored: list[tuple[float, DetectedObject]] = []

    aim_useful = gaze.aim_xy is not None and not _aim_still_on_face(gaze, frame_w)
    if aim_useful:
        assert gaze.aim_xy is not None
        ax, ay = gaze.aim_xy
        for obj in lamps:
            if _ceiling_fringe(obj, ax, ay, frame_w, frame_h):
                continue
            cx, cy = obj.center
            dist = ((cx - ax) ** 2 + (cy - ay) ** 2) ** 0.5 / max(frame_w, 1)
            hit = _point_in_padded_box(obj.xyxy, ax, ay, pad)
            if not hit and gaze.eye_xy is not None:
                progress = _aim_along_path_to(obj, gaze.eye_xy, gaze.aim_xy, frame_w)
                hit = progress is not None and progress >= (0.22 if sticky_id else 0.30)
                if hit:
                    dist = max(0.0, 0.42 - float(progress) * 0.35)
            if not hit:
                continue
            if sticky_id and obj.obj_id == sticky_id:
                dist -= 0.06
            scored.append((dist, obj))
        if scored:
            scored.sort(key=lambda item: item[0])
            best_d, best = scored[0]
            if best_d <= 0.55:
                return _as_target(best, 1.0 - best_d)
        # Aim left the face but not toward any lamp — do not ray-lock a side glance.
        return None

    # Aim still on the eyes (or missing): use look direction toward the lamp.
    if gaze.eye_xy is None:
        return None
    yaw, pitch = look_axes(gaze)
    mag = (yaw * yaw + pitch * pitch) ** 0.5
    if mag < (0.06 if sticky_id else 0.09):
        return None
    face_x = gaze.eye_xy[0]
    side_hits: list[DetectedObject] = []
    for obj in lamps:
        cx, _cy = obj.center
        if yaw >= 0.06 and cx > face_x + 0.04 * frame_w:
            side_hits.append(obj)
        elif yaw <= -0.06 and cx < face_x - 0.04 * frame_w:
            side_hits.append(obj)
        elif abs(pitch) >= 0.10 and sticky_id and obj.obj_id == sticky_id:
            side_hits.append(obj)
    pool = side_hits if side_hits else []
    if not pool:
        return None
    along = _select_along_ray(gaze, pool, frame_w, frame_h, sticky_id, 0.10)
    if along is not None:
        return along
    angled = _select_by_angle(gaze, pool, frame_w, frame_h, sticky_id)
    return angled


def select_target(
    gaze: GazeEstimate,
    detections: list[DetectedObject],
    frame_w: int,
    frame_h: int,
    side_threshold: float,
    prefer_detections: bool = True,
    hysteresis: float = 0.10,
    sticky_id: str | None = None,
    ambiguity_margin: float = 0.10,
    allow_slots: bool = True,
    look_templates: dict[str, tuple[float, float]] | None = None,
) -> Target | None:
    if not gaze.face_found:
        return None

    if prefer_detections and detections:
        lamps = [obj for obj in detections if _is_lamp_det(obj)]
        others = [obj for obj in detections if not _is_lamp_det(obj)]

        # Phase-1 lamps: require the look point on the green box. Side turns / rays do not count.
        if lamps:
            lamp_hit = _select_lamp_by_gaze(gaze, lamps, frame_w, frame_h, sticky_id)
            if lamp_hit is not None:
                return lamp_hit
            if not others:
                if not allow_slots:
                    return None
                # fall through to slots only

        pool = others if lamps and others else (others or detections)
        if pool and (not lamps or others):
            world = select_by_world_look(
                gaze, pool, frame_w, frame_h, sticky_id, look_templates
            )
            if world is not None:
                return world
            if gaze.eye_xy is not None:
                along = _select_along_ray(
                    gaze, pool, frame_w, frame_h, sticky_id, ambiguity_margin
                )
                if along is not None:
                    return along
                angled = _select_by_angle(gaze, pool, frame_w, frame_h, sticky_id)
                if angled is not None:
                    return angled
            if gaze.aim_xy is not None:
                at_aim = _select_at_aim(
                    gaze, pool, frame_w, frame_h, sticky_id, ambiguity_margin
                )
                if at_aim is not None:
                    return at_aim
            aim_x, aim_y = _aim_point(gaze, frame_w, frame_h)
            scored: list[tuple[float, DetectedObject]] = []
            for obj in pool:
                if _ceiling_fringe(obj, aim_x, aim_y, frame_w, frame_h):
                    continue
                cx, cy = obj.center
                x0, y0, x1, y1 = obj.xyxy
                pad_x = 0.12 * (x1 - x0)
                pad_y = 0.12 * (y1 - y0)
                inside = (x0 - pad_x) <= aim_x <= (x1 + pad_x) and (y0 - pad_y) <= aim_y <= (
                    y1 + pad_y
                )
                dist = ((cx - aim_x) ** 2 + (cy - aim_y) ** 2) ** 0.5 / max(frame_w, 1)
                area = _box_area(obj, frame_w, frame_h)
                near = dist < 0.10 and area < 0.10
                on_axis = _on_camera_axis(obj, aim_x, aim_y, frame_w, frame_h)
                if not inside and not near and not on_axis:
                    continue
                score = dist - 0.14 * min(area, 0.30)
                if inside or on_axis:
                    score -= 0.28
                    score -= 0.18 * (1.0 - min(area, 0.25) / 0.25)
                if sticky_id and obj.obj_id == sticky_id:
                    score -= 0.12
                scored.append((score, obj))

            if scored:
                scored.sort(key=lambda t: t[0])
                best_score, best = scored[0]
                if best_score < 0.36:
                    rival_label = None
                    ambiguous = False
                    if len(scored) >= 2:
                        second_score, second = scored[1]
                        if second_score < 0.36 and (second_score - best_score) < ambiguity_margin:
                            ambiguous = True
                            rival_label = second.appliance or second.label
                    return Target(
                        target_id=best.obj_id,
                        label=best.appliance or best.label,
                        kind="detected",
                        xyxy=best.xyxy,
                        score=1.0 - best_score,
                        ambiguous=ambiguous,
                        rival_label=rival_label,
                    )

    if not allow_slots:
        return None

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
