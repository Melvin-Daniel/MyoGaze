"""Split labeled raw frames into train/val YOLO folders (80/20).

Expects datasets/lamp/raw/*.jpg with matching *.txt YOLO labels
(from LabelImg in YOLO mode, class 0 = lamp). Empty txt = negative (no lamp).
"""

from __future__ import annotations

import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "datasets" / "lamp" / "raw"
IMG_TRAIN = ROOT / "datasets" / "lamp" / "images" / "train"
IMG_VAL = ROOT / "datasets" / "lamp" / "images" / "val"
LBL_TRAIN = ROOT / "datasets" / "lamp" / "labels" / "train"
LBL_VAL = ROOT / "datasets" / "lamp" / "labels" / "val"


def main() -> int:
    images = sorted(
        p
        for p in RAW.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    if not images:
        print(f"No images in {RAW}. Run: python scripts/capture_lamp.py")
        return 1
    labeled = 0
    empty = 0
    missing = 0
    keep: list[Path] = []
    for img in images:
        txt = img.with_suffix(".txt")
        if not txt.exists():
            missing += 1
            continue
        keep.append(img)
        text = txt.read_text(encoding="utf-8").strip()
        if text:
            labeled += 1
        else:
            empty += 1
    if missing:
        print(f"{missing} images have no .txt — label them in LabelImg, then re-run.")
    if len(keep) < 20:
        print(f"Only {len(keep)} labeled images. Aim for hundreds before training.")
    rng = random.Random(7)
    rng.shuffle(keep)
    n_val = max(1, int(round(0.2 * len(keep)))) if len(keep) >= 5 else 0
    val = set(keep[:n_val])
    for folder in (IMG_TRAIN, IMG_VAL, LBL_TRAIN, LBL_VAL):
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
    for img in keep:
        dest_img = IMG_VAL if img in val else IMG_TRAIN
        dest_lbl = LBL_VAL if img in val else LBL_TRAIN
        shutil.copy2(img, dest_img / img.name)
        shutil.copy2(img.with_suffix(".txt"), dest_lbl / f"{img.stem}.txt")
    print(
        f"train={len(keep) - n_val}  val={n_val}  "
        f"boxes={labeled}  negatives={empty}  unlabeled_skipped={missing}"
    )
    print("Next: python scripts/train_lamp.py")
    return 0 if keep else 1


if __name__ == "__main__":
    sys.exit(main())
