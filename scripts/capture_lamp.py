"""Grab laptop-webcam frames for Stage B lamp training.

SPACE  save a frame into datasets/lamp/raw/
Q      quit

Hold the LUKER in different places. Mix close/far, left/right, ON/OFF.
Also save some frames with NO bulb (ceiling lights only) — leave those unlabeled.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "datasets" / "lamp" / "raw"


def main() -> int:
    import cv2

    RAW.mkdir(parents=True, exist_ok=True)
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cam.isOpened():
        cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("Could not open webcam 0")
        return 1
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    print(f"Saving to {RAW}")
    print("SPACE = save   Q = quit")
    n = len(list(RAW.glob("*.jpg")))
    while True:
        ok, frame = cam.read()
        if not ok:
            print("camera read failed")
            break
        frame = cv2.flip(frame, 1)
        view = frame.copy()
        cv2.putText(
            view,
            f"saved {n}   SPACE=save  Q=quit",
            (16, 36),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (40, 180, 80),
            2,
        )
        cv2.imshow("lamp capture", view)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q"), 27):
            break
        if key == 32:
            name = RAW / f"lamp_{int(time.time() * 1000)}.jpg"
            cv2.imwrite(str(name), frame)
            n += 1
            print(f"saved {name.name}  ({n})")
    cam.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
