"""Webcam capture wrapper (laptop now, eMeet S600 later)."""

from __future__ import annotations

import time

import cv2
import numpy as np

from .config import Config, DEFAULT


def score_frame(frame: np.ndarray | None) -> float:
    """Higher is a real color picture. Near-zero means an empty/black buffer."""
    if frame is None or frame.size == 0:
        return -1.0
    if frame.ndim == 2:
        std = float(frame.std())
        mean = float(frame.mean())
        if mean < 1.5 and std < 1.5:
            return -1.0
        return std * 0.4
    mean = float(frame.mean())
    std = float(frame.std())
    if mean < 1.5 and std < 1.5:
        return -1.0
    b, g, r = cv2.split(frame[:, :, :3])
    chroma = float(
        np.mean(np.abs(r.astype(np.float32) - g.astype(np.float32)))
        + np.mean(np.abs(g.astype(np.float32) - b.astype(np.float32)))
    )
    return std + 2.0 * chroma + 0.05 * mean


class Camera:
    def __init__(self, cfg: Config = DEFAULT):
        self.cfg = cfg
        self.cap: cv2.VideoCapture | None = None
        self.opened_index = int(cfg.camera_index)
        self.opened_backend = "dshow"

    def open(self) -> None:
        last_error = "Cannot open camera"
        indices = [int(self.cfg.camera_index)]
        for extra in range(0, 4):
            if extra not in indices:
                indices.append(extra)
        backends = [
            ("dshow", cv2.CAP_DSHOW),
            ("msmf", cv2.CAP_MSMF),
        ]
        best_score = 8.0
        best: tuple[cv2.VideoCapture, int, str, np.ndarray] | None = None

        def _release_best() -> None:
            nonlocal best
            if best is not None:
                best[0].release()
                best = None

        for index in indices:
            for backend_name, backend in backends:
                cap = cv2.VideoCapture(index, backend)
                if not cap.isOpened():
                    cap.release()
                    continue
                try:
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                except Exception:
                    pass
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.cfg.frame_width))
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.cfg.frame_height))
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                try:
                    cap.set(cv2.CAP_PROP_FPS, 30)
                except Exception:
                    pass
                try:
                    cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)
                except Exception:
                    pass
                try:
                    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
                except Exception:
                    pass
                local_best = -1.0
                local_frame = None
                for _ in range(14):
                    ok, candidate = cap.read()
                    if not ok:
                        time.sleep(0.03)
                        continue
                    if candidate.ndim == 2:
                        candidate = cv2.cvtColor(candidate, cv2.COLOR_GRAY2BGR)
                    scored = score_frame(candidate)
                    if scored > local_best:
                        local_best = scored
                        local_frame = candidate
                    if scored > 25.0:
                        break
                    time.sleep(0.03)
                if local_frame is None or local_best <= 0:
                    last_error = (
                        f"Camera index {index} ({backend_name}) opened but only "
                        "returned black frames"
                    )
                    cap.release()
                    continue
                if local_best > best_score:
                    _release_best()
                    best = (cap, index, backend_name, local_frame)
                    best_score = local_best
                    if local_best > 25.0:
                        self.cap = cap
                        self.opened_index = index
                        self.opened_backend = backend_name
                        print(
                            f"[camera] opened index={index} backend={backend_name} "
                            f"{int(local_frame.shape[1])}x{int(local_frame.shape[0])} "
                            f"score={local_best:.1f} mean={local_frame.mean():.1f}",
                            flush=True,
                        )
                        return
                else:
                    cap.release()

        if best is None:
            raise RuntimeError(last_error)

        cap, index, backend_name, frame = best
        self.cap = cap
        self.opened_index = index
        self.opened_backend = backend_name
        print(
            f"[camera] opened index={index} backend={backend_name} "
            f"{int(frame.shape[1])}x{int(frame.shape[0])} "
            f"score={best_score:.1f} mean={frame.mean():.1f}",
            flush=True,
        )

    def read(self) -> np.ndarray:
        assert self.cap is not None
        last: Exception | None = None
        for _ in range(4):
            ok, frame = self.cap.read()
            if ok and frame is not None and frame.size > 0:
                if frame.ndim == 2:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                want_w = int(getattr(self.cfg, "frame_width", 0) or 0)
                if want_w > 0 and frame.shape[1] > want_w:
                    scale = want_w / float(frame.shape[1])
                    frame = cv2.resize(
                        frame,
                        (want_w, max(1, int(round(frame.shape[0] * scale)))),
                        interpolation=cv2.INTER_AREA,
                    )
                return frame
            last = RuntimeError("Camera read failed")
            time.sleep(0.02)
        raise last or RuntimeError("Camera read failed")

    def release(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
