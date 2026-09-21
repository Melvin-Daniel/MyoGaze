"""Gaze from iris direction, with head pose as fallback.

MediaPipe Face Landmarker (478 points) includes iris centers. Head-facing
alone is not enough: the aim point must follow where the eyes look.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import time

import cv2
import numpy as np

from .types import GazeEstimate

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "face_landmarker.task"

__all__ = ["GazeEstimate", "FaceGazeEstimator", "MODEL_PATH", "iris_look", "aim_from_eyes", "face_oval_from_landmarks"]

# A full look (yaw/pitch = 1) moves this fraction of the frame away from the eyes.
_AIM_GAIN_X = 0.82
_AIM_GAIN_Y = 0.58
# Looking straight at the camera keeps the aim on the face.
_AIM_DEADZONE = 0.09

# Face Mesh / Face Landmarker iris + eye corners
_LEFT_IRIS, _LEFT_OUTER, _LEFT_INNER, _LEFT_TOP, _LEFT_BOT = 468, 33, 133, 159, 145
_RIGHT_IRIS, _RIGHT_OUTER, _RIGHT_INNER, _RIGHT_TOP, _RIGHT_BOT = 473, 263, 362, 386, 374


def _clip(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return float(max(lo, min(hi, value)))


def _combine_look(head: float, eye: float, eye_weight: float) -> float:
    """Eyes steer a glance; head keeps a look at a real object from falling off."""
    ew = float(np.clip(eye_weight, 0.0, 1.0))
    mag_h, mag_e = abs(head), abs(eye)
    # Head facing the camera but eyes "screaming" sideways is usually glasses noise.
    if mag_h < 0.10 and mag_e > 0.45:
        eye = _clip(eye * 0.25)
        mag_e = abs(eye)
    if head * eye > 0 and mag_h >= 0.08 and mag_e >= 0.06:
        return _clip(0.48 * head + 0.52 * eye)
    if mag_e >= 0.10 and mag_h < 0.08:
        return _clip((1.0 - ew) * head + ew * eye)
    if mag_h >= 0.10:
        return _clip(0.62 * head + 0.38 * eye)
    return _clip((1.0 - ew) * head + ew * eye)


def iris_look(lm: Any, width: int, height: int) -> tuple[float, float, tuple[float, float]] | None:
    """Return (eye_yaw, eye_pitch, iris_xy) from 478 face landmarks, or None."""
    try:
        n = len(lm)
    except TypeError:
        return None
    if n < 478:
        return None

    def one_eye(iris_i: int, outer_i: int, inner_i: int, top_i: int, bot_i: int) -> tuple[float, float, float, float]:
        iris, outer, inner, top, bot = lm[iris_i], lm[outer_i], lm[inner_i], lm[top_i], lm[bot_i]
        eye_w = inner.x - outer.x
        eye_h = bot.y - top.y
        mid_x = (inner.x + outer.x) / 2.0
        mid_y = (top.y + bot.y) / 2.0
        # Mild amplify — too strong saturates and pins the aim to the frame edge.
        yaw = (iris.x - mid_x) / (0.11 * abs(eye_w) + 1e-6)
        pitch = (iris.y - mid_y) / (0.15 * abs(eye_h) + 1e-6)
        return _clip(yaw), _clip(pitch), iris.x * width, iris.y * height

    try:
        ly, lp, lx, ly_px = one_eye(_LEFT_IRIS, _LEFT_OUTER, _LEFT_INNER, _LEFT_TOP, _LEFT_BOT)
        ry, rp, rx, ry_px = one_eye(_RIGHT_IRIS, _RIGHT_OUTER, _RIGHT_INNER, _RIGHT_TOP, _RIGHT_BOT)
    except (IndexError, AttributeError):
        return None
    # Average both eyes. A single wrecked iris (glasses) must not dominate.
    yaw = (ly + ry) / 2.0
    pitch = (lp + rp) / 2.0
    if ly * ry < 0 and abs(ly - ry) > 0.28:
        yaw *= 0.35
    if lp * rp < 0 and abs(lp - rp) > 0.28:
        pitch *= 0.35
    return _clip(yaw), _clip(pitch), ((lx + rx) / 2.0, (ly_px + ry_px) / 2.0)


def pupil_look(
    frame_bgr: np.ndarray,
    lm: Any,
    width: int,
    height: int,
) -> tuple[float, float] | None:
    """Estimate look from the dark pupil. Rejects glasses-frame shadows on the crop edge."""
    try:
        n = len(lm)
    except TypeError:
        return None
    if n < 468 or frame_bgr is None or frame_bgr.size == 0:
        return None

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    looks: list[tuple[float, float]] = []

    for outer_i, inner_i, top_i, bot_i in (
        (_LEFT_OUTER, _LEFT_INNER, _LEFT_TOP, _LEFT_BOT),
        (_RIGHT_OUTER, _RIGHT_INNER, _RIGHT_TOP, _RIGHT_BOT),
    ):
        try:
            outer, inner, top, bot = lm[outer_i], lm[inner_i], lm[top_i], lm[bot_i]
        except (IndexError, AttributeError):
            continue
        x0 = int(min(outer.x, inner.x) * width)
        x1 = int(max(outer.x, inner.x) * width)
        y0 = int(min(top.y, bot.y) * height)
        y1 = int(max(top.y, bot.y) * height)
        # Inset so the glasses rim is outside the crop.
        pad_x = max(1, int(0.18 * (x1 - x0)))
        pad_y = max(1, int(0.16 * (y1 - y0)))
        x0, x1 = x0 + pad_x, x1 - pad_x
        y0, y1 = y0 + pad_y, y1 - pad_y
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(width - 1, x1), min(height - 1, y1)
        if x1 - x0 < 8 or y1 - y0 < 6:
            continue
        crop = gray[y0:y1, x0:x1]
        if crop.size < 40:
            continue
        blur = cv2.GaussianBlur(crop, (5, 5), 0)
        floor = float(np.percentile(blur, 12))
        mask = blur <= floor + 4.0
        if int(mask.sum()) < 8:
            continue
        ys, xs = np.where(mask)
        cx = float(xs.mean())
        cy = float(ys.mean())
        ew = float(x1 - x0)
        eh = float(y1 - y0)
        # Dark blob on the crop border is usually the frame, not the pupil.
        if cx < 0.18 * ew or cx > 0.82 * ew or cy < 0.15 * eh or cy > 0.85 * eh:
            continue
        yaw = (cx - 0.5 * ew) / (0.28 * ew)
        pitch = (cy - 0.5 * eh) / (0.34 * eh)
        looks.append((_clip(yaw), _clip(pitch)))

    if len(looks) < 2:
        # One eye alone is too noisy with glasses — need both.
        return None
    (y0, p0), (y1, p1) = looks[0], looks[1]
    if y0 * y1 < 0 and abs(y0 - y1) > 0.25:
        return None
    yaw = 0.5 * (y0 + y1)
    pitch = 0.5 * (p0 + p1)
    # Saturating glances are almost always frame glare, not a real look.
    if abs(yaw) > 0.55 or abs(pitch) > 0.55:
        return None
    return _clip(yaw), _clip(pitch)


def _blend_eye_signals(
    iris_yaw: float,
    iris_pitch: float,
    pupil: tuple[float, float] | None,
) -> tuple[float, float]:
    """Merge landmark iris with pixel pupil. Iris stays primary; pupil only nudges."""
    if pupil is None:
        return iris_yaw, iris_pitch
    py, pp = pupil
    # Disagreeing signs → trust iris (pupil often hits the glasses rim).
    if py * iris_yaw < 0 and abs(py) > 0.12 and abs(iris_yaw) > 0.08:
        return iris_yaw, iris_pitch
    yaw = 0.72 * iris_yaw + 0.28 * py
    pitch = 0.72 * iris_pitch + 0.28 * pp
    return _clip(yaw), _clip(pitch)


def _deadzone(value: float, zone: float = _AIM_DEADZONE) -> float:
    """Collapse tiny residual looks so 'straight at camera' stays on the face."""
    a = abs(value)
    if a <= zone:
        return 0.0
    # Soft ramp out of the deadzone so locking is not a cliff.
    signed = 1.0 if value > 0 else -1.0
    return signed * min(1.0, (a - zone) / max(1.0 - zone, 1e-6))


def aim_from_eyes(
    eye_xy: tuple[float, float],
    yaw: float,
    pitch: float,
    frame_w: int,
    frame_h: int,
) -> tuple[float, float]:
    """Project a look from the eyes. Frame center is not the origin."""
    yaw = _deadzone(float(yaw))
    pitch = _deadzone(float(pitch), zone=0.11)
    ax = eye_xy[0] + yaw * _AIM_GAIN_X * frame_w
    ay = eye_xy[1] + pitch * _AIM_GAIN_Y * frame_h
    return (
        float(max(0.0, min(frame_w - 1, ax))),
        float(max(0.0, min(frame_h - 1, ay))),
    )


def align_head_to_image(
    matrix_yaw: float,
    matrix_pitch: float,
    image_yaw: float,
    image_pitch: float,
) -> tuple[float, float]:
    """Match head pose to the picture. A mirrored frame flips the matrix yaw."""
    yaw, pitch = matrix_yaw, matrix_pitch
    if image_yaw * yaw < -0.012 and abs(image_yaw) >= 0.05:
        yaw = -yaw
    if image_pitch * pitch < -0.012 and abs(image_pitch) >= 0.05:
        pitch = -pitch
    return _clip(yaw), _clip(pitch)


def look_axes(gaze: GazeEstimate) -> tuple[float, float]:
    """Smoothed look in the image. Do not swap in a raw iris sample — that jumps."""
    return gaze.yaw, gaze.pitch


def _eye_center(lm: Any, width: int, height: int) -> tuple[float, float] | None:
    try:
        centers = []
        for outer, inner, top, bot in (
            (_LEFT_OUTER, _LEFT_INNER, _LEFT_TOP, _LEFT_BOT),
            (_RIGHT_OUTER, _RIGHT_INNER, _RIGHT_TOP, _RIGHT_BOT),
        ):
            centers.append(
                (
                    (lm[outer].x + lm[inner].x) / 2.0 * width,
                    (lm[top].y + lm[bot].y) / 2.0 * height,
                )
            )
        return (
            (centers[0][0] + centers[1][0]) / 2.0,
            (centers[0][1] + centers[1][1]) / 2.0,
        )
    except (IndexError, TypeError, AttributeError):
        return None


def face_oval_from_landmarks(
    lm: Any, width: int, height: int
) -> tuple[float, float, float, float] | None:
    """Ellipse around the face (cx, cy, rx, ry) in pixels."""
    try:
        forehead, chin, left, right = lm[10], lm[152], lm[234], lm[454]
    except (IndexError, TypeError, AttributeError):
        return None
    xs = [left.x, right.x, forehead.x, chin.x]
    ys = [forehead.y, chin.y, left.y, right.y]
    x0, x1 = min(xs) * width, max(xs) * width
    y0, y1 = min(ys) * height, max(ys) * height
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    rx = max((x1 - x0) / 2.0 * 1.12, 8.0)
    ry = max((y1 - y0) / 2.0 * 1.18, 8.0)
    return (cx, cy, rx, ry)


class FaceGazeEstimator:
    def __init__(
        self,
        model_path: Path | None = None,
        max_faces: int = 1,
        smooth_alpha: float = 0.16,
        eye_weight: float = 0.55,
    ):
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        path = Path(model_path) if model_path else MODEL_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"Missing Face Landmarker model at {path}. "
                "Download face_landmarker.task into models/."
            )
        base = mp_python.BaseOptions(model_asset_path=str(path))
        options = vision.FaceLandmarkerOptions(
            base_options=base,
            running_mode=vision.RunningMode.VIDEO,
            num_faces=max_faces,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_facial_transformation_matrixes=True,
        )
        self._mp = mp
        self._landmarker = vision.FaceLandmarker.create_from_options(options)
        self._ts_ms = 0
        self.smooth_alpha = float(np.clip(smooth_alpha, 0.05, 1.0))
        self.eye_weight = float(np.clip(eye_weight, 0.0, 1.0))
        self.yaw_offset = 0.0
        self.pitch_offset = 0.0
        self._yaw_s = 0.0
        self._pitch_s = 0.0
        self._have_smooth = False
        self.has_iris = False
        self.look_templates: dict[str, tuple[float, float]] = {}

    def reset_session(self) -> None:
        # Do not reset _ts_ms — MediaPipe VIDEO mode requires timestamps
        # to keep increasing across Start/Stop, not jump back to 0.
        self._have_smooth = False
        self._yaw_s = 0.0
        self._pitch_s = 0.0
        self.reset_calibration()

    def calibrate_center(self) -> float:
        """Treat the current look direction as 'looking straight'."""
        if self._have_smooth:
            self.yaw_offset += self._yaw_s
            self.pitch_offset += self._pitch_s
            self._yaw_s = 0.0
            self._pitch_s = 0.0
        return self.yaw_offset

    def reset_calibration(self) -> None:
        self.yaw_offset = 0.0
        self.pitch_offset = 0.0
        self.look_templates = {}

    def set_look_template(self, key: str, yaw: float, pitch: float) -> None:
        self.look_templates[str(key).strip().lower()] = (float(yaw), float(pitch))

    def _image_head(self, lm: Any) -> tuple[float, float]:
        """Nose offset in the picture. Positive yaw is toward the right of the frame."""
        nose = lm[1]
        left = lm[234]
        right = lm[454]
        chin = lm[152]
        forehead = lm[10]
        mid_x = (left.x + right.x) / 2.0
        face_w = max(abs(right.x - left.x), 1e-6)
        yaw = _clip((nose.x - mid_x) / (0.35 * face_w))
        mid_y = (forehead.y + chin.y) / 2.0
        face_h = max(abs(chin.y - forehead.y), 1e-6)
        pitch = _clip((nose.y - mid_y) / (0.5 * face_h))
        return yaw, pitch

    def _head_pose(self, result: Any, lm: Any) -> tuple[float, float]:
        image_yaw, image_pitch = self._image_head(lm)
        if result.facial_transformation_matrixes:
            mat = np.array(result.facial_transformation_matrixes[0]).reshape(4, 4)
            r00, r02 = mat[0, 0], mat[0, 2]
            r12 = mat[1, 2]
            r22 = mat[2, 2]
            yaw = float(np.arctan2(r02, r22) / (np.pi / 2))
            pitch = float(np.arctan2(-r12, np.sqrt(r00 * r00 + r22 * r22)) / (np.pi / 2))
            return align_head_to_image(yaw, pitch, image_yaw, image_pitch)
        return image_yaw, image_pitch

    def estimate(self, frame_bgr: np.ndarray) -> GazeEstimate:
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        now_ms = int(time.monotonic() * 1000)
        if now_ms <= self._ts_ms:
            now_ms = self._ts_ms + 33
        self._ts_ms = now_ms
        try:
            result = self._landmarker.detect_for_video(mp_image, self._ts_ms)
        except Exception:
            self._ts_ms += 1000
            result = self._landmarker.detect_for_video(mp_image, self._ts_ms)
        if not result.face_landmarks:
            self._have_smooth = False
            return GazeEstimate(False, None, 0.0, 0.0, 0.0)

        lm = result.face_landmarks[0]
        nose = lm[1]
        nose_xy = (nose.x * w, nose.y * h)
        head_yaw, head_pitch = self._head_pose(result, lm)

        iris = iris_look(lm, w, h)
        pupil = pupil_look(frame_bgr, lm, w, h)
        if iris is not None:
            eye_yaw, eye_pitch, iris_xy = iris
            eye_yaw, eye_pitch = _blend_eye_signals(eye_yaw, eye_pitch, pupil)
            self.has_iris = True
            raw_yaw = _combine_look(head_yaw, eye_yaw, self.eye_weight)
            raw_pitch = _combine_look(head_pitch, eye_pitch, self.eye_weight)
            conf = 0.92
        elif pupil is not None:
            eye_yaw, eye_pitch = pupil
            iris_xy = None
            self.has_iris = False
            raw_yaw = _combine_look(head_yaw, eye_yaw, max(self.eye_weight, 0.78))
            raw_pitch = _combine_look(head_pitch, eye_pitch, max(self.eye_weight, 0.78))
            conf = 0.84
        else:
            eye_yaw, eye_pitch, iris_xy = 0.0, 0.0, None
            raw_yaw, raw_pitch = head_yaw, head_pitch
            conf = 0.72
            self.has_iris = False

        centered_yaw = _clip(raw_yaw - self.yaw_offset)
        centered_pitch = _clip(raw_pitch - self.pitch_offset)
        a = self.smooth_alpha
        if not self._have_smooth:
            self._yaw_s = centered_yaw
            self._pitch_s = centered_pitch
            self._have_smooth = True
        else:
            self._yaw_s = a * centered_yaw + (1.0 - a) * self._yaw_s
            self._pitch_s = a * centered_pitch + (1.0 - a) * self._pitch_s

        # Callers mirror the frame before estimate() when mirror_preview is on, so
        # image axes already match the Live preview. Do not flip again here — that
        # sent the aim the wrong way (dot stayed on the face while looking at a lamp).
        yaw = _clip(self._yaw_s)
        pitch = _clip(self._pitch_s)
        if abs(yaw) >= 0.95:
            conf = min(conf, 0.55)
        eyes = _eye_center(lm, w, h)
        aim_xy = aim_from_eyes(eyes, yaw, pitch, w, h) if eyes is not None else None
        return GazeEstimate(
            True,
            nose_xy,
            yaw,
            pitch,
            conf,
            raw_yaw=raw_yaw,
            raw_pitch=raw_pitch,
            eye_yaw=eye_yaw,
            eye_pitch=eye_pitch,
            head_yaw=head_yaw,
            head_pitch=head_pitch,
            iris_xy=iris_xy,
            has_iris=iris is not None,
            eye_xy=eyes,
            aim_xy=aim_xy,
            face_oval=face_oval_from_landmarks(lm, w, h),
        )

    def close(self) -> None:
        self._landmarker.close()
