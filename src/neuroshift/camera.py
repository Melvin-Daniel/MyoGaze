"""Webcam capture wrapper (laptop now, eMeet S600 later)."""

from __future__ import annotations

import cv2
import numpy as np

from .config import Config, DEFAULT


class Camera:
    def __init__(self, cfg: Config = DEFAULT):
        self.cfg = cfg
        self.cap: cv2.VideoCapture | None = None

    def open(self) -> None:
        self.cap = cv2.VideoCapture(self.cfg.camera_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            # Fallback without CAP_DSHOW (some machines)
            self.cap = cv2.VideoCapture(self.cfg.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera index {self.cfg.camera_index}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cfg.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cfg.frame_height)

    def read(self) -> np.ndarray:
        assert self.cap is not None
        ok, frame = self.cap.read()
        if not ok or frame is None:
            raise RuntimeError("Camera read failed")
        return frame

    def release(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
