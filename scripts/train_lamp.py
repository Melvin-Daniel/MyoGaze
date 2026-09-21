"""Fine-tune YOLOv8n on datasets/lamp (one class: lamp)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets" / "lamp" / "data.yaml"
WEIGHTS = ROOT / "yolov8n.pt"
PREV = ROOT / "runs" / "lamp" / "v1" / "weights" / "best.pt"
RUN_NAME = "v2"


def main() -> int:
    from ultralytics import YOLO

    if not DATA.exists():
        print(f"Missing {DATA}")
        return 1
    train_imgs = list((ROOT / "datasets" / "lamp" / "images" / "train").glob("*.*"))
    if len(train_imgs) < 10:
        print("Not enough train images. Label raw frames, then:")
        print("  python scripts/prepare_lamp_dataset.py")
        return 1
    import torch

    device = 0 if torch.cuda.is_available() else "cpu"
    print(f"Training on: {device}" + (f" ({torch.cuda.get_device_name(0)})" if device == 0 else " (install CUDA torch to use the RTX 4050)"))
    start = PREV if PREV.exists() else (WEIGHTS if WEIGHTS.exists() else Path("yolov8n.pt"))
    print(f"Starting from: {start}")
    model = YOLO(str(start))
    model.train(
        data=str(DATA),
        epochs=80,
        imgsz=640,
        batch=8,
        device=device,
        project=str(ROOT / "runs" / "lamp"),
        name=RUN_NAME,
        exist_ok=True,
        patience=20,
        workers=0,
    )
    best = ROOT / "runs" / "lamp" / RUN_NAME / "weights" / "best.pt"
    print()
    print("Training done.")
    print(f"Weights: {best}")
    print("In config/default.yaml set:")
    print(f"  yolo_model: {best.as_posix()}")
    print("Then restart: python -m src.neuroshift serve --host 0.0.0.0 --port 8000")
    return 0


if __name__ == "__main__":
    sys.exit(main())
