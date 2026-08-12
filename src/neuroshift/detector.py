"""YOLO-based object detection for live targeting."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .aliases import appliance_label, display_label

# COCO classes we treat as selectable stand-in "appliances"
DEFAULT_TARGET_CLASSES = {
    "tv",
    "laptop",
    "cell phone",
    "bottle",
    "cup",
    "wine glass",
    "book",
    "clock",
    "vase",
    "remote",
    "keyboard",
    "mouse",
    "bowl",
    "potted plant",
    "chair",
    "toothbrush",
    "scissors",
    "teddy bear",
    "sports ball",
    "backpack",
    "handbag",
    "umbrella",
}


@dataclass
class DetectedObject:
    obj_id: str
    label: str  # raw COCO label
    conf: float
    xyxy: tuple[int, int, int, int]
    appliance: str = ""  # friendly display name

    def __post_init__(self) -> None:
        if not self.appliance:
            self.appliance = appliance_label(self.label)

    @property
    def center(self) -> tuple[float, float]:
        x0, y0, x1, y1 = self.xyxy
        return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)

    @property
    def hud_label(self) -> str:
        return display_label(self.label, self.conf)


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0, ax1 - ax0) * max(0, ay1 - ay0)
    area_b = max(0, bx1 - bx0) * max(0, by1 - by0)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


class ObjectDetector:
    """Thin YOLO wrapper with IoU-stable IDs across frames."""

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        conf: float = 0.30,
        target_classes: set[str] | None = None,
        every_n_frames: int = 3,
        iou_match: float = 0.3,
        imgsz: int = 320,
    ):
        self.conf = conf
        self.target_classes = target_classes or DEFAULT_TARGET_CLASSES
        self.every_n_frames = max(1, every_n_frames)
        self.iou_match = iou_match
        self.imgsz = imgsz
        self._frame_i = 0
        self._last: list[DetectedObject] = []
        self._next_id = 1
        self.available = False
        self.model = None
        try:
            from ultralytics import YOLO

            self.model = YOLO(model_name)
            self.available = True
        except Exception as exc:  # noqa: BLE001
            print(f"[detector] YOLO unavailable ({exc}). Using virtual slots only.")

    def detect(self, frame_bgr: np.ndarray) -> list[DetectedObject]:
        if not self.available or self.model is None:
            return []

        self._frame_i += 1
        if self._frame_i % self.every_n_frames != 1 and self._last:
            return self._last

        results = self.model.predict(
            frame_bgr,
            conf=self.conf,
            imgsz=self.imgsz,
            verbose=False,
        )
        raw: list[tuple[str, float, tuple[int, int, int, int]]] = []
        if results and results[0].boxes is not None:
            r0 = results[0]
            names = r0.names
            for box in r0.boxes:
                cls_id = int(box.cls.item())
                label = names.get(cls_id, str(cls_id))
                if label not in self.target_classes:
                    continue
                conf = float(box.conf.item())
                xyxy = tuple(int(v) for v in box.xyxy[0].tolist())
                raw.append((label, conf, xyxy))  # type: ignore[arg-type]

        objects = self._match_ids(raw)
        self._last = objects
        return objects

    def _match_ids(
        self, raw: list[tuple[str, float, tuple[int, int, int, int]]]
    ) -> list[DetectedObject]:
        used_prev: set[str] = set()
        out: list[DetectedObject] = []
        for label, conf, xyxy in raw:
            best_id = None
            best_iou = 0.0
            for prev in self._last:
                if prev.label != label or prev.obj_id in used_prev:
                    continue
                iou = _iou(xyxy, prev.xyxy)
                if iou > best_iou:
                    best_iou = iou
                    best_id = prev.obj_id
            if best_id is not None and best_iou >= self.iou_match:
                obj_id = best_id
                used_prev.add(best_id)
            else:
                obj_id = f"{label}_{self._next_id}"
                self._next_id += 1
            out.append(
                DetectedObject(
                    obj_id=obj_id,
                    label=label,
                    conf=conf,
                    xyxy=xyxy,
                    appliance=appliance_label(label),
                )
            )
        return out
