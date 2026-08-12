"""Phase-1 head/face direction via MediaPipe Face Landmarker (Tasks API)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .types import GazeEstimate

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "face_landmarker.task"

__all__ = ["GazeEstimate", "FaceGazeEstimator", "MODEL_PATH"]


class FaceGazeEstimator:
    def __init__(
        self,
        model_path: Path | None = None,
        max_faces: int = 1,
        smooth_alpha: float = 0.28,
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
        self.yaw_offset = 0.0
        self._yaw_s = 0.0
        self._pitch_s = 0.0
        self._have_smooth = False

    def calibrate_center(self) -> float:
        """Treat current head pose as 'looking straight'. Returns new offset."""
        if self._have_smooth:
            self.yaw_offset += self._yaw_s
            self._yaw_s = 0.0
        return self.yaw_offset

    def reset_calibration(self) -> None:
        self.yaw_offset = 0.0

    def estimate(self, frame_bgr: np.ndarray) -> GazeEstimate:
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        self._ts_ms += 33
        result = self._landmarker.detect_for_video(mp_image, self._ts_ms)
        if not result.face_landmarks:
            self._have_smooth = False
            return GazeEstimate(False, None, 0.0, 0.0, 0.0)

        lm = result.face_landmarks[0]
        nose = lm[1]
        nose_xy = (nose.x * w, nose.y * h)

        raw_yaw = 0.0
        raw_pitch = 0.0
        if result.facial_transformation_matrixes:
            mat = np.array(result.facial_transformation_matrixes[0]).reshape(4, 4)
            r00, r02 = mat[0, 0], mat[0, 2]
            r12 = mat[1, 2]
            r22 = mat[2, 2]
            raw_yaw = float(np.clip(np.arctan2(r02, r22) / (np.pi / 2), -1.0, 1.0))
            raw_pitch = float(
                np.clip(
                    np.arctan2(-r12, np.sqrt(r00 * r00 + r22 * r22)) / (np.pi / 2),
                    -1.0,
                    1.0,
                )
            )
        else:
            left = lm[234]
            right = lm[454]
            chin = lm[152]
            forehead = lm[10]
            mid_x = (left.x + right.x) / 2.0
            face_w = max(abs(right.x - left.x), 1e-6)
            raw_yaw = float(np.clip((nose.x - mid_x) / (0.35 * face_w), -1.0, 1.0))
            mid_y = (forehead.y + chin.y) / 2.0
            face_h = max(abs(chin.y - forehead.y), 1e-6)
            raw_pitch = float(np.clip((nose.y - mid_y) / (0.5 * face_h), -1.0, 1.0))

        centered_yaw = float(np.clip(raw_yaw - self.yaw_offset, -1.0, 1.0))
        a = self.smooth_alpha
        if not self._have_smooth:
            self._yaw_s = centered_yaw
            self._pitch_s = raw_pitch
            self._have_smooth = True
        else:
            self._yaw_s = a * centered_yaw + (1.0 - a) * self._yaw_s
            self._pitch_s = a * raw_pitch + (1.0 - a) * self._pitch_s

        yaw = float(np.clip(self._yaw_s, -1.0, 1.0))
        pitch = float(np.clip(self._pitch_s, -1.0, 1.0))
        conf = 0.90 if abs(yaw) < 0.95 else 0.55
        return GazeEstimate(
            True,
            nose_xy,
            yaw,
            pitch,
            conf,
            raw_yaw=raw_yaw,
            raw_pitch=raw_pitch,
        )

    def close(self) -> None:
        self._landmarker.close()
