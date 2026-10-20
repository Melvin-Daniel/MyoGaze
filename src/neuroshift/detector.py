"""Live object detection for targeting.

COCO and open-vocab YOLOE do not know this demo PC cooler or a handheld
LED bulb. The fan matcher uses the white hub / impeller. The bulb matcher
looks for a solid white globe. Cup is not a target — YOLO used to call
the globe a cup, and the B22 metal cap a fan. A found fan or bulb
replaces overlapping lookalikes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .aliases import appliance_label, display_label

# Held near the webcam. Tiny far ceiling lights stay under this frame share.
_NEAR_LAMP_AREA = 0.012
# Bigger than shirt print / chest glare. Only then skip the body filter.
_HELD_OVER_PRINT = 0.035
# Face-sized white blobs at the top of the frame are not a held bulb.
_FACE_FALSE_LAMP_AREA = 0.11

# COCO classes we treat as selectable stand-in "appliances"
DEFAULT_TARGET_CLASSES = {
    "tv",
    "laptop",
    "cell phone",
    "bottle",
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
    "frisbee",
    "fan",
    "lamp",
}

# Tiny prompt list — open-vocab models get worse if you dump all of COCO in.
PROMPT_CLASSES = [
    "led bulb",
    "light bulb",
    "handheld LED bulb",
    "B22 bulb",
    "desk lamp",
    "table lamp",
    "person",
]

LABEL_ALIASES = {
    "cooling fan": "fan",
    "pc cooling fan": "fan",
    "computer fan": "fan",
    "computer cooling fan": "fan",
    "pc fan": "fan",
    "case fan": "fan",
    "axial fan": "fan",
    "fan": "fan",
    "cell phone": "cell phone",
    "phone": "cell phone",
    "mobile phone": "cell phone",
    "smartphone": "cell phone",
    "desk lamp": "lamp",
    "table lamp": "lamp",
    "lamp": "lamp",
    "light bulb": "lamp",
    "led bulb": "lamp",
    "handheld led bulb": "lamp",
    "b22 bulb": "lamp",
    "led light": "lamp",
    "bulb": "lamp",
}

# Closed-set leftovers that YOLO may still emit for this square fan.
# Do not include lamp — the B22 cap is circular metal and must stay a lamp.
FAN_LOOKALIKE_CLASSES = {"clock", "sports ball", "bottle", "cell phone"}
# YOLO leftovers for a held LED globe. Cup is never shown; it promotes to lamp.
BULB_LOOKALIKE_CLASSES = {"cup", "bottle", "bowl", "vase", "wine glass", "sports ball"}
DROPPED_CLASSES = {"cup"}
HIDDEN_CLASSES = {"person"}


def canonicalize_label(raw: str) -> str:
    key = " ".join(str(raw).lower().replace("_", " ").split())
    return LABEL_ALIASES.get(key, key)


def _name_of(names: dict | list | tuple, cls_id: int) -> str:
    if isinstance(names, dict):
        return str(names.get(cls_id, cls_id))
    if isinstance(names, (list, tuple)) and 0 <= cls_id < len(names):
        return str(names[cls_id])
    return str(cls_id)


def _is_open_vocab(model_name: str) -> bool:
    stem = Path(model_name).stem.lower()
    return "yoloe" in stem or "world" in stem


def _model_class_keys(model: object) -> set[str]:
    names = getattr(model, "names", None)
    if not names:
        return set()
    values = names.values() if isinstance(names, dict) else names
    return {canonicalize_label(str(v)) for v in values}


def _model_is_custom_lamp(model: object) -> bool:
    """True for a one-class lamp detector (Stage B fine-tune), not YOLOE prompts."""
    return _model_class_keys(model) == {"lamp"}


def _model_is_custom_fan(model: object) -> bool:
    return _model_class_keys(model) == {"fan"}


def _fan_on_person(
    xyxy: tuple[int, int, int, int],
    people: list[tuple[int, int, int, int]],
) -> bool:
    """True when a 'fan' box is really a face / torso."""
    cx = (xyxy[0] + xyxy[2]) / 2.0
    cy = (xyxy[1] + xyxy[3]) / 2.0
    for person in people:
        if _iou(xyxy, person) >= 0.25:
            return True
        x0, y0, x1, y1 = person
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            return True
    return False


def _person_column(
    person: tuple[int, int, int, int],
) -> tuple[float, float, float, float]:
    """Head-only person boxes miss the chest. Extend a column for lanyard false lamps."""
    px0, py0, px1, py1 = person
    pw, ph = max(px1 - px0, 1.0), max(py1 - py0, 1.0)
    if ph / pw < 1.85:
        py1 = py0 + 3.4 * ph
    return px0 - 0.20 * pw, py0 - 0.08 * ph, px1 + 0.20 * pw, py1


def _on_any_head(
    xyxy: tuple[int, int, int, int],
    people: list[tuple[int, int, int, int]],
    frame_w: int = 0,
    frame_h: int = 0,
) -> bool:
    """True when the box sits on a face / head, including a second person in frame."""
    if not people:
        return False
    bw = max(xyxy[2] - xyxy[0], 1)
    bh = max(xyxy[3] - xyxy[1], 1)
    cx = (xyxy[0] + xyxy[2]) / 2.0
    cy = (xyxy[1] + xyxy[3]) / 2.0
    for px0, py0, px1, py1 in people:
        pw, ph = max(px1 - px0, 1.0), max(py1 - py0, 1.0)
        person_frac = (bw * bh) / (pw * ph)
        frame_frac = (bw * bh) / max(frame_w * frame_h, 1) if frame_w and frame_h else 0.0
        # Held globe vs a face box (tests use a head crop) vs a full-body YOLO box.
        if person_frac >= 0.40 or (person_frac >= 0.14 and frame_frac >= 0.030):
            continue
        # Hands live on the outer edge. Heads sit in the middle-top.
        hx0 = px0 + 0.16 * pw
        hx1 = px1 - 0.16 * pw
        hy0 = py0 - 0.05 * ph
        hy1 = py0 + min(0.48 * ph, 1.15 * pw)
        if hx0 <= cx <= hx1 and hy0 <= cy <= hy1:
            return True
    return False


def _on_torso(
    xyxy: tuple[int, int, int, int],
    people: list[tuple[int, int, int, int]],
) -> bool:
    """True for a small badge / shirt speck on the body — not a shown bulb."""
    if not people:
        return False
    cx = (xyxy[0] + xyxy[2]) / 2.0
    cy = (xyxy[1] + xyxy[3]) / 2.0
    bw = max(xyxy[2] - xyxy[0], 1)
    bh = max(xyxy[3] - xyxy[1], 1)
    for px0, py0, px1, py1 in people:
        pw, ph = max(px1 - px0, 1), max(py1 - py0, 1)
        bx0, by0, bx1, by1 = _person_column((px0, py0, px1, py1))
        col_w = max(bx1 - bx0, 1.0)
        col_h = max(by1 - by0, 1.0)
        # A held / close-up globe is bigger than a lanyard badge.
        if bw > 0.45 * pw or bh > 0.42 * max(ph, 0.45 * col_h):
            continue
        ix0 = px0 + 0.16 * pw
        ix1 = px1 - 0.16 * pw
        iy0 = py0 + 0.06 * ph
        iy1 = py1 + 0.90 * ph
        if ix0 <= cx <= ix1 and iy0 <= cy <= iy1:
            return True
        if _iou(xyxy, (px0, py0, px1, py1)) >= 0.24:
            return True
        if bx0 + 0.02 * col_w <= cx <= bx1 - 0.02 * col_w and by0 <= cy <= by1:
            if bw <= 0.72 * pw and bh <= 0.85 * col_h:
                return True
        col_box = (int(bx0), int(by0), int(bx1), int(by1))
        if _iou(xyxy, col_box) >= 0.22 and bw <= 0.72 * pw:
            return True
    return False


def _lamp_on_chest(
    xyxy: tuple[int, int, int, int],
    people: list[tuple[int, int, int, int]],
) -> bool:
    """True for a lanyard / shirt print on the body, not a bulb held to the side."""
    if not people or not _on_torso(xyxy, people):
        return False
    x0, y0, x1, y1 = xyxy
    px0, py0, px1, py1 = max(people, key=lambda p: (p[2] - p[0]) * (p[3] - p[1]))
    pcx = (px0 + px1) / 2.0
    cx = (x0 + x1) / 2.0
    # Floral prints sit on the left or right chest, not only the sternum.
    return abs(cx - pcx) <= 0.38 * max(px1 - px0, 1)


def _clothing_or_face_lamp(
    xyxy: tuple[int, int, int, int],
    people: list[tuple[int, int, int, int]],
    frame_w: int = 0,
    frame_h: int = 0,
) -> bool:
    """Shirt, lanyard, or face highlight — not a close held lamp."""
    if frame_w > 0 and frame_h > 0 and _oversized_face_lamp(xyxy, people, frame_w, frame_h):
        return True
    if frame_w > 0 and frame_h > 0:
        bw = max(xyxy[2] - xyxy[0], 1)
        bh = max(xyxy[3] - xyxy[1], 1)
        if (bw * bh) / max(frame_w * frame_h, 1) >= _HELD_OVER_PRINT:
            return False
    return _on_any_head(xyxy, people, frame_w, frame_h) or _lamp_on_body(
        xyxy, people, frame_w, frame_h
    )


def _oversized_face_lamp(
    xyxy: tuple[int, int, int, int],
    people: list[tuple[int, int, int, int]],
    frame_w: int,
    frame_h: int,
) -> bool:
    """Huge white blob on the face / top of frame — not a porcelain bulb."""
    x0, y0, x1, y1 = xyxy
    bw, bh = max(x1 - x0, 1), max(y1 - y0, 1)
    area = (bw * bh) / max(frame_w * frame_h, 1)
    cy = (y0 + y1) / 2.0 / max(frame_h, 1)
    # A true close-up globe can sit high in the frame — only reject when it
    # swallows a detected head / person, not a bare close-up photo.
    if area >= _FACE_FALSE_LAMP_AREA and people and _on_any_head(xyxy, people, frame_w, frame_h):
        return True
    if area >= _FACE_FALSE_LAMP_AREA and y0 <= frame_h * 0.10 and cy < 0.42 and people:
        if any(_iou(xyxy, person) >= 0.20 for person in people):
            return True
    if people and area >= 0.16:
        for px0, py0, px1, py1 in people:
            head = (px0, py0, px1, int(py0 + 0.55 * max(py1 - py0, 1)))
            if _iou(xyxy, head) >= 0.28:
                return True
    return False


def _lamp_on_body(
    xyxy: tuple[int, int, int, int],
    people: list[tuple[int, int, int, int]],
    frame_w: int = 0,
    frame_h: int = 0,
) -> bool:
    """Small print on the torso. A held globe may overlap the person anywhere."""
    if not people:
        return False
    cx = (xyxy[0] + xyxy[2]) / 2.0
    cy = (xyxy[1] + xyxy[3]) / 2.0
    bw = max(xyxy[2] - xyxy[0], 1)
    bh = max(xyxy[3] - xyxy[1], 1)
    frame_area = max(frame_w * frame_h, 1)
    # Shirt print is small. A close held globe is larger.
    if frame_w > 0 and frame_h > 0 and (bw * bh) / frame_area >= _HELD_OVER_PRINT:
        return False
    for px0, py0, px1, py1 in people:
        pw, ph = max(px1 - px0, 1.0), max(py1 - py0, 1.0)
        if bw * bh >= 0.14 * pw * ph:
            continue
        if not (px0 + 0.10 * pw <= cx <= px1 - 0.10 * pw):
            continue
        if not (py0 + 0.18 * ph <= cy <= py1 - 0.02 * ph):
            continue
        if bw > 0.50 * pw or bh > 0.50 * ph:
            continue
        return True
    return False


def _handheld_score(
    xyxy: tuple[int, int, int, int],
    people: list[tuple[int, int, int, int]],
    frame_w: int,
    frame_h: int,
) -> float:
    """Higher for a compact object held to the side, not furniture behind the user."""
    x0, y0, x1, y1 = xyxy
    bw, bh = max(x1 - x0, 1), max(y1 - y0, 1)
    area = (bw * bh) / max(frame_w * frame_h, 1)
    cx = (x0 + x1) / 2.0
    score = 1.2 - min(area, 0.30) * 4.0
    if 0.008 <= area <= 0.14:
        score += 0.45
    if _on_torso(xyxy, people) or _background_slab(xyxy, frame_w, frame_h):
        return score - 3.0
    if people:
        px0, py0, px1, py1 = max(people, key=lambda p: (p[2] - p[0]) * (p[3] - p[1]))
        pcx = (px0 + px1) / 2.0
        score += min(0.70, abs(cx - pcx) / max(frame_w, 1) * 2.2)
        score -= _iou(xyxy, (px0, py0, px1, py1)) * 1.1
    return score


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


_FAN_TMPLS: list[tuple[np.ndarray, np.ndarray]] = []
_FAN_TMPL_READY = False


def _assets_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "assets"


def _prepare_template(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    import cv2

    tmpl = cv2.resize(gray, (96, 96))
    return tmpl, cv2.Canny(tmpl, 40, 120)


def _has_radial_blades(
    gray: np.ndarray,
    peak_min: float = 6.0,
    peak_max: int = 18,
) -> bool:
    """True when a ring around the hub has several intensity peaks (fan blades)."""
    import cv2

    ch, cw = gray.shape[:2]
    if min(ch, cw) < 18:
        return False
    small = gray
    if max(cw, ch) > 80:
        scale = 80 / max(cw, ch)
        small = cv2.resize(gray, (max(18, int(cw * scale)), max(18, int(ch * scale))))
    sh, sw = small.shape
    cy, cx = sh / 2.0, sw / 2.0
    r0, r1 = min(sh, sw) * 0.20, min(sh, sw) * 0.46
    n = 72
    yy, xx = np.ogrid[:sh, :sw]
    dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    ang = np.arctan2(yy - cy, xx - cx) + np.pi
    bins = np.clip((ang / (2 * np.pi) * n).astype(np.int32), 0, n - 1)
    mask = (dist >= r0) & (dist <= r1)
    ring = np.zeros(n, np.float32)
    counts = np.zeros(n, np.float32)
    np.add.at(ring, bins[mask], small[mask].astype(np.float32))
    np.add.at(counts, bins[mask], 1)
    ring = ring / np.maximum(counts, 1)
    ring = ring - float(ring.mean())
    peaks = 0
    for i in range(n):
        if ring[i] > ring[i - 1] and ring[i] >= ring[(i + 1) % n] and ring[i] > peak_min:
            peaks += 1
    return 4 <= peaks <= peak_max


def _has_bright_hub(gray: np.ndarray) -> bool:
    """The desk fan has a white sticker hub; the stock cooler does not."""
    sh, sw = gray.shape[:2]
    if min(sh, sw) < 16:
        return False
    cy, cx = sh / 2.0, sw / 2.0
    span = min(sh, sw)
    yy, xx = np.ogrid[:sh, :sw]
    dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    hub = gray[dist <= span * 0.16]
    ring = gray[(dist >= span * 0.28) & (dist <= span * 0.50)]
    if hub.size < 8 or ring.size < 8:
        return False
    hub_mean = float(hub.mean())
    ring_mean = float(ring.mean())
    # Blades are dark. A bright poster or shirt is not a hub.
    return hub_mean >= 155 and ring_mean <= 115 and hub_mean >= ring_mean + 40


def _white_hub_candidates(frame_bgr: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Boxes around a bright circular hub, expanded to the impeller."""
    import cv2

    h, w = frame_bgr.shape[:2]
    scale = min(1.0, 480 / max(w, 1))
    small = (
        cv2.resize(frame_bgr, (max(80, int(w * scale)), max(60, int(h * scale))))
        if scale < 1
        else frame_bgr
    )
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thr = int(max(160, min(210, float(blur.mean()) + 78)))
    _, bw = cv2.threshold(blur, thr, 255, cv2.THRESH_BINARY)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    inv = 1.0 / scale
    sh, sw = small.shape[:2]
    span = min(sw, sh)
    out: list[tuple[int, int, int, int]] = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < 20:
            continue
        (_cx, _cy), radius = cv2.minEnclosingCircle(contour)
        if radius < 5 or radius > span * 0.22:
            continue
        circ = area / max(np.pi * radius * radius, 1)
        if circ < 0.40:
            continue
        mask = np.zeros((sh, sw), np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, -1)
        if float(gray[mask > 0].mean()) < 155:
            continue
        hub_frac = (2.0 * radius) / span
        expand = 2.05 if hub_frac > 0.18 else 3.35
        side = 2.0 * radius * expand
        x0 = int((_cx - side / 2.0) * inv)
        y0 = int((_cy - side / 2.0) * inv)
        x1 = int((_cx + side / 2.0) * inv)
        y1 = int((_cy + side / 2.0) * inv)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        if x1 - x0 < 20 or y1 - y0 < 20:
            continue
        out.append((x0, y0, x1, y1))
    return out


def _crop_bright_hub_fan(bgr: np.ndarray) -> np.ndarray:
    boxes = _white_hub_candidates(bgr)
    if not boxes:
        return bgr
    x0, y0, x1, y1 = max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
    crop = bgr[y0:y1, x0:x1]
    return crop if crop.size else bgr


_FAN_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _fan_asset_files() -> list[Path]:
    """User desk shots first, extra angles next, stock cooler last."""
    assets = _assets_dir()
    if not assets.is_dir():
        return []
    files = [
        path
        for path in assets.iterdir()
        if path.is_file()
        and path.stem.lower().startswith("pc_fan")
        and path.suffix.lower() in _FAN_IMAGE_SUFFIXES
    ]

    def rank(path: Path) -> tuple[int, str]:
        name = path.stem.lower()
        if name == "pc_fan_user":
            return (0, name)
        if name == "pc_fan_ref":
            return (2, name)
        return (1, name)

    return sorted(files, key=rank)


def _crop_fan_for_template(bgr: np.ndarray, crop_hub: bool) -> np.ndarray | None:
    """Tight crop on the impeller so a selfie/UI screenshot is not the template."""
    if not crop_hub:
        return bgr
    crop = _crop_bright_hub_fan(bgr)
    if crop.shape[:2] != bgr.shape[:2]:
        return crop
    boxes = _dark_impeller_candidates(bgr) or _white_hub_candidates(bgr)
    if boxes:
        x0, y0, x1, y1 = max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
        cut = bgr[y0:y1, x0:x1]
        if cut.size and min(cut.shape[:2]) >= 22:
            return cut
    h, w = bgr.shape[:2]
    if h * w > 180 * 180:
        return None
    return bgr


def _load_fan_templates() -> list[tuple[np.ndarray, np.ndarray]]:
    """Every pc_fan* photo in assets/: user shots, extra angles, then the stock cooler."""
    global _FAN_TMPLS, _FAN_TMPL_READY
    if _FAN_TMPL_READY:
        return _FAN_TMPLS
    _FAN_TMPL_READY = True
    import cv2

    loaded: list[tuple[np.ndarray, np.ndarray]] = []
    for path in _fan_asset_files():
        img = cv2.imread(str(path))
        if img is None or img.size == 0:
            continue
        crop_hub = path.stem.lower() != "pc_fan_ref"
        cropped = _crop_fan_for_template(img, crop_hub)
        if cropped is None or cropped.size == 0:
            continue
        gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
        loaded.append(_prepare_template(gray))
    _FAN_TMPLS = loaded
    return _FAN_TMPLS


def _mostly_skin(crop_bgr: np.ndarray) -> bool:
    """A cheek or forehead, not a white globe or a dark impeller."""
    import cv2

    if crop_bgr.size == 0:
        return False
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    hue, sat, val = cv2.split(hsv)
    # A real bulb or hub has a white core. A cheek does not.
    white = (val >= 170) & (sat <= 70)
    if float(white.mean()) >= 0.10:
        return False
    skin = ((hue <= 25) | (hue >= 165)) & (sat >= 35) & (sat <= 175) & (val >= 50)
    return float(skin.mean()) >= 0.42


def looks_like_pc_fan(frame_bgr: np.ndarray, xyxy: tuple[int, int, int, int]) -> bool:
    """True for the demo axial PC fan: dark frame or white hub + blades."""
    import cv2

    h, w = frame_bgr.shape[:2]
    x0, y0, x1, y1 = xyxy
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(w, int(x1)), min(h, int(y1))
    bw, bh = x1 - x0, y1 - y0
    if bw < 22 or bh < 22:
        return False
    area = (bw * bh) / max(w * h, 1)
    if area < 0.002 or area > 0.28:
        return False
    aspect = bw / max(bh, 1)
    if not 0.72 <= aspect <= 1.38:
        return False
    crop = frame_bgr[y0:y1, x0:x1]
    if _mostly_skin(crop):
        return False
    # The B22 metal cap is a small circle under a white globe — not a hub.
    if _globe_in_or_above(frame_bgr, (x0, y0, x1, y1)):
        return False
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    bright_hub = _has_bright_hub(gray)
    if float(gray.mean()) > 145 and not bright_hub:
        return False
    mean = float(gray.mean())
    peak_min = 5.5 if mean < 95 else 6.0
    peak_max = 22 if mean < 95 else 18
    if bright_hub:
        return _has_radial_blades(gray, peak_min=peak_min, peak_max=peak_max)
    if mean > 140:
        return False
    return _has_radial_blades(gray, peak_min=peak_min, peak_max=peak_max)


def _custom_fan_trust_conf(custom_min: float) -> float:
    """Above this, trust the fine-tuned fan YOLO like the lamp model."""
    return max(0.52, float(custom_min) + 0.10)


def _soft_fan_shape_ok(frame_bgr: np.ndarray, xyxy: tuple[int, int, int, int]) -> bool:
    """Block hair / globes / bright blobs without requiring blade peaks every frame."""
    import cv2

    h, w = frame_bgr.shape[:2]
    x0, y0, x1, y1 = xyxy
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(w, int(x1)), min(h, int(y1))
    bw, bh = x1 - x0, y1 - y0
    if bw < 22 or bh < 22:
        return False
    aspect = bw / max(bh, 1)
    if not 0.68 <= aspect <= 1.42:
        return False
    crop = frame_bgr[y0:y1, x0:x1]
    if crop.size == 0 or _mostly_skin(crop):
        return False
    if _globe_in_or_above(frame_bgr, (x0, y0, x1, y1)):
        return False
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    if float(gray.mean()) > 158 and not _has_bright_hub(gray):
        return False
    if float(gray.std()) < 12 and float(gray.mean()) > 130:
        return False
    return True


def _fan_shape_accepted(
    frame_bgr: np.ndarray,
    xyxy: tuple[int, int, int, int],
    conf: float,
    custom_min: float,
    *,
    crop: bool = True,
) -> tuple[bool, tuple[int, int, int, int]]:
    """Tighten loose YOLO boxes; accept high-conf custom hits without blade gate."""
    box = (_fan_crop(frame_bgr, xyxy) if crop else None) or xyxy
    if looks_like_pc_fan(frame_bgr, box):
        return True, box
    if conf >= _custom_fan_trust_conf(custom_min) and _soft_fan_shape_ok(frame_bgr, box):
        return True, box
    return False, box


def _accept_custom_fan_yolo(
    frame_bgr: np.ndarray,
    xyxy: tuple[int, int, int, int],
    conf: float,
    custom_min: float,
) -> tuple[bool, tuple[int, int, int, int]]:
    """Trust one-class fan weights like the lamp model — lamp in frame must not zero fan."""
    box = _fan_crop(frame_bgr, xyxy) or xyxy
    h, w = frame_bgr.shape[:2]
    x0, y0, x1, y1 = box
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(w, int(x1)), min(h, int(y1))
    bw, bh = x1 - x0, y1 - y0
    if bw < 18 or bh < 18:
        return False, box
    area = (bw * bh) / max(w * h, 1)
    if area < 0.0015 or area > 0.55:
        return False, box
    crop = frame_bgr[y0:y1, x0:x1]
    if crop.size == 0 or _mostly_skin(crop):
        return False, box
    if conf < float(custom_min):
        return False, box
    return True, (x0, y0, x1, y1)


def match_pc_fan_template(
    frame_bgr: np.ndarray,
) -> tuple[tuple[int, int, int, int], float] | None:
    """Multi-scale match against the desk-fan photo and the stock cooler."""
    import cv2

    templates = _load_fan_templates()
    if not templates:
        return None
    h, w = frame_bgr.shape[:2]
    search_w = min(w, 420)
    scale = search_w / max(w, 1)
    small = cv2.resize(frame_bgr, (search_w, max(48, int(h * scale)))) if scale < 1 else frame_bgr
    g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(g, 40, 120)
    best_score = 0.0
    best_box: tuple[int, int, int, int] | None = None
    max_side = int(min(small.shape[:2]) * 0.62)
    for gray_t, edge_t in templates:
        for side in range(28, max_side + 1, 10):
            if side >= g.shape[0] or side >= g.shape[1]:
                continue
            t = cv2.resize(gray_t, (side, side))
            _mn, mx, _ml, loc = cv2.minMaxLoc(cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED))
            if mx > best_score:
                best_score = float(mx)
                best_box = (loc[0], loc[1], loc[0] + side, loc[1] + side)
            te = cv2.resize(edge_t, (side, side))
            _mn, mx, _ml, loc = cv2.minMaxLoc(cv2.matchTemplate(edges, te, cv2.TM_CCOEFF_NORMED))
            if mx > best_score:
                best_score = float(mx)
                best_box = (loc[0], loc[1], loc[0] + side, loc[1] + side)
    if best_box is None or best_score < 0.62:
        return None
    inv = 1.0 / scale
    x0, y0, x1, y1 = best_box
    xyxy = (int(x0 * inv), int(y0 * inv), int(x1 * inv), int(y1 * inv))
    if not looks_like_pc_fan(frame_bgr, xyxy):
        return None
    return xyxy, best_score


def _dark_impeller_candidates(frame_bgr: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Square boxes around a dark circular impeller. The hub need not be white."""
    import cv2

    h, w = frame_bgr.shape[:2]
    scale = min(1.0, 480 / max(w, 1))
    small = (
        cv2.resize(frame_bgr, (max(80, int(w * scale)), max(60, int(h * scale))))
        if scale < 1
        else frame_bgr
    )
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thr = int(max(70, min(105, float(blur.mean()) * 0.56)))
    _, bw = cv2.threshold(blur, thr, 255, cv2.THRESH_BINARY_INV)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    inv = 1.0 / scale
    sh, sw = small.shape[:2]
    span = min(sw, sh)
    out: list[tuple[int, int, int, int]] = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < 180:
            continue
        (_cx, _cy), radius = cv2.minEnclosingCircle(contour)
        if radius < 14 or radius > span * 0.28:
            continue
        circ = area / max(np.pi * radius * radius, 1.0)
        if circ < 0.45:
            continue
        _x, _y, cw, ch = cv2.boundingRect(contour)
        aspect = cw / max(ch, 1)
        if not 0.78 <= aspect <= 1.28:
            continue
        mask = np.zeros((sh, sw), np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, -1)
        if float(gray[mask > 0].std()) < 18:
            continue
        side = 2.15 * radius
        x0 = int((_cx - side / 2.0) * inv)
        y0 = int((_cy - side / 2.0) * inv)
        x1 = int((_cx + side / 2.0) * inv)
        y1 = int((_cy + side / 2.0) * inv)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        if x1 - x0 < 28 or y1 - y0 < 28:
            continue
        out.append((x0, y0, x1, y1))
    return out


def _fan_crop(frame_bgr: np.ndarray, xyxy: tuple[int, int, int, int]) -> tuple[int, int, int, int] | None:
    """Phone/lamp boxes on the held fan are often too tall. Slide a square through the box."""
    h, w = frame_bgr.shape[:2]
    x0, y0, x1, y1 = xyxy
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(w, int(x1)), min(h, int(y1))
    box = (x0, y0, x1, y1)
    if looks_like_pc_fan(frame_bgr, box):
        return box
    bw, bh = x1 - x0, y1 - y0
    side = min(bw, bh)
    if side < 22 or max(bw, bh) < side * 1.15:
        return None
    step = max(8, side // 4)
    if bh >= bw:
        stops = list(range(y0, max(y0 + 1, y1 - side + 1), step))
        if y1 - side not in stops:
            stops.append(max(y0, y1 - side))
        candidates = [(x0, y, x0 + side, y + side) for y in stops]
    else:
        stops = list(range(x0, max(x0 + 1, x1 - side + 1), step))
        if x1 - side not in stops:
            stops.append(max(x0, x1 - side))
        candidates = [(x, y0, x + side, y0 + side) for x in stops]
    for candidate in candidates:
        if looks_like_pc_fan(frame_bgr, candidate):
            return candidate
    return None


def _union_box(
    a: tuple[int, int, int, int], b: tuple[int, int, int, int]
) -> tuple[int, int, int, int]:
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _edge_strip(xyxy: tuple[int, int, int, int], frame_w: int, frame_h: int) -> bool:
    """A curtain or ceiling band, not a handheld fan or bulb."""
    x0, y0, x1, y1 = xyxy
    tall = (y1 - y0) >= frame_h * 0.40
    wide = (x1 - x0) >= frame_w * 0.40
    on_side = x0 <= frame_w * 0.03 or x1 >= frame_w * 0.97
    on_top = y0 <= frame_h * 0.03
    return (on_side and tall) or (on_top and wide)


def _background_slab(
    xyxy: tuple[int, int, int, int], frame_w: int, frame_h: int
) -> bool:
    """A box glued to the wall or the frame edge, not a handheld object."""
    x0, y0, x1, y1 = xyxy
    bw, bh = max(x1 - x0, 1), max(y1 - y0, 1)
    area = (bw * bh) / max(frame_w * frame_h, 1)
    left = x0 <= frame_w * 0.02
    top = y0 <= frame_h * 0.02
    right = x1 >= frame_w * 0.98
    bottom = y1 >= frame_h * 0.98
    touches = int(left) + int(top) + int(right) + int(bottom)
    if touches >= 3:
        return True
    if left and right:
        return True
    # Corner furniture — not a close-up globe that only hits the top and bottom.
    if (left or right) and (top or bottom) and area > 0.12:
        return True
    return area > 0.42 and (left or right)


# Held close to the webcam. Far ceiling lights / room fixtures stay under this.
def _near_held_lamp(xyxy: tuple[int, int, int, int], frame_w: int, frame_h: int) -> bool:
    """True only for a close shown globe — small = far away, ignore it."""
    x0, y0, x1, y1 = xyxy
    bw, bh = max(x1 - x0, 1), max(y1 - y0, 1)
    area = (bw * bh) / max(frame_w * frame_h, 1)
    if area < _NEAR_LAMP_AREA:
        return False
    if min(bw, bh) < 36:
        return False
    cy = (y0 + y1) / 2.0 / max(frame_h, 1)
    # High + small = ceiling fixture. A held bulb fills more of the frame.
    if cy < 0.30 and area < 0.028:
        return False
    aspect = bw / max(bh, 1)
    if not 0.38 <= aspect <= 1.60:
        return False
    return True


def _distant_glow(
    xyxy: tuple[int, int, int, int], frame_w: int, frame_h: int
) -> bool:
    """Ceiling fixtures, far room lights, tiny glare — not a close held globe."""
    if not _near_held_lamp(xyxy, frame_w, frame_h):
        return True
    x0, y0, x1, y1 = xyxy
    bw, bh = max(x1 - x0, 1), max(y1 - y0, 1)
    area = (bw * bh) / max(frame_w * frame_h, 1)
    aspect = bw / max(bh, 1)
    cy = (y0 + y1) / 2.0 / max(frame_h, 1)
    if y0 <= 2 and cy < 0.30 and area < 0.08:
        return True
    wide_strip = aspect >= 1.75 or bh < 0.08 * frame_h
    if y0 <= frame_h * 0.06 and cy < 0.22 and wide_strip:
        return True
    return False


def _shown_lamp_score(
    xyxy: tuple[int, int, int, int],
    people: list[tuple[int, int, int, int]],
    frame_w: int,
    frame_h: int,
) -> float:
    """Prefer the close shown globe over a distant ON light or a wall panel."""
    x0, y0, x1, y1 = xyxy
    bw, bh = max(x1 - x0, 1), max(y1 - y0, 1)
    area = (bw * bh) / max(frame_w * frame_h, 1)
    aspect = bw / max(bh, 1)
    cy = (y0 + y1) / 2.0 / max(frame_h, 1)
    score = area * 20.0
    if not _near_held_lamp(xyxy, frame_w, frame_h):
        return -20.0
    if area > 0.18 and (aspect < 0.55 or aspect > 1.45):
        score -= 10.0
    if _edge_strip(xyxy, frame_w, frame_h):
        score -= 8.0
    if _distant_glow(xyxy, frame_w, frame_h):
        score -= 8.0
    if _background_slab(xyxy, frame_w, frame_h):
        score -= 3.0
    return score


def _collapse_same_object(
    frame_bgr: np.ndarray,
    raw: list[tuple[str, float, tuple[int, int, int, int]]],
) -> list[tuple[str, float, tuple[int, int, int, int]]]:
    """Phone + lamp on the same held fan is one object, not two targets."""
    h, w = frame_bgr.shape[:2]
    unused = list(raw)
    out: list[tuple[str, float, tuple[int, int, int, int]]] = []
    while unused:
        label, conf, xyxy = unused.pop(0)
        group = [(label, conf, xyxy)]
        rest: list[tuple[str, float, tuple[int, int, int, int]]] = []
        for other in unused:
            if any(_same_held_object(item[2], other[2]) for item in group):
                group.append(other)
            else:
                rest.append(other)
        unused = rest
        boxes = [item[2] for item in group]
        union = boxes[0]
        for box in boxes[1:]:
            union = _union_box(union, box)
        best_conf = max(item[1] for item in group)
        fan_box = next((box for item in group if (box := _fan_crop(frame_bgr, item[2])) is not None), None)
        if fan_box is None and looks_like_pc_fan(frame_bgr, union):
            fan_box = union
        bulb_box = next((item[2] for item in group if looks_like_led_bulb(frame_bgr, item[2])), None)
        if bulb_box is None and looks_like_led_bulb(frame_bgr, union):
            bulb_box = union
        globe_ref = bulb_box or next((item[2] for item in group if item[0] == "lamp"), None)
        stacked_cap = False
        if globe_ref is not None:
            stacked_cap = any(
                _cap_under_globe(globe_ref, item[2]) for item in group if item[2] != globe_ref
            )
        # A globe plus its metal cap is one lamp, even if the cap looked like a fan.
        if stacked_cap:
            kept = ("lamp", max(best_conf, 0.8), union)
            if not looks_like_led_bulb(frame_bgr, union) and globe_ref is not None:
                kept = ("lamp", max(best_conf, 0.8), globe_ref)
        elif bulb_box is not None and fan_box is not None:
            lamps_in = [item for item in group if item[0] == "lamp"]
            fans_in = [item for item in group if item[0] == "fan"]
            split_lamp = max(lamps_in, key=lambda item: item[1])[2] if lamps_in else bulb_box
            split_fan = max(fans_in, key=lambda item: item[1])[2] if fans_in else fan_box
            # Lit lamp + fan in separate hands: keep both (ON globe used to drop fan).
            if _iou(split_lamp, split_fan) < 0.12:
                out.append(("lamp", max(best_conf, 0.8), split_lamp))
                out.append(("fan", max(best_conf, 0.8), split_fan))
                continue
            if looks_like_pc_fan(frame_bgr, fan_box) and not looks_like_led_bulb(frame_bgr, union):
                kept = ("fan", max(best_conf, 0.8), fan_box)
            else:
                kept = ("lamp", max(best_conf, 0.8), bulb_box)
        elif bulb_box is not None:
            kept = ("lamp", max(best_conf, 0.8), bulb_box)
        elif fan_box is not None:
            kept = ("fan", max(best_conf, 0.8), fan_box)
        else:
            kept = max(group, key=lambda item: item[1])
        if kept[0] == "cup":
            continue
        if kept[0] == "lamp" and not looks_like_led_bulb(frame_bgr, kept[2]):
            trust_yolo = kept[1] >= 0.34 and (
                _lit_globe_on(frame_bgr, kept[2]) or _globe_in_or_above(frame_bgr, kept[2])
            )
            if not trust_yolo and not (stacked_cap and globe_ref is not None):
                others = [item for item in group if item[0] != "lamp"]
                if not others:
                    continue
                kept = max(others, key=lambda item: item[1])
        if kept[0] == "fan" and not looks_like_pc_fan(frame_bgr, kept[2]):
            if _background_slab(kept[2], w, h) or _edge_strip(kept[2], w, h):
                continue
        out.append(kept)
    return out


def _keep_held_appliances(
    raw: list[tuple[str, float, tuple[int, int, int, int]]],
    people: list[tuple[int, int, int, int]],
    frame_w: int,
    frame_h: int,
) -> list[tuple[str, float, tuple[int, int, int, int]]]:
    """One lamp and one fan — drop a cap boxed as fan under the held bulb."""
    lamps = [item for item in raw if item[0] == "lamp"]
    fans = [item for item in raw if item[0] == "fan"]
    leftovers = [item for item in raw if item[0] in {"fan", "cup"}]
    others = [item for item in raw if item[0] not in {"lamp", "fan", "cup"}]
    kept: list[tuple[str, float, tuple[int, int, int, int]]] = []
    if lamps:
        lamps.sort(
            key=lambda item: (
                _shown_lamp_score(item[2], people, frame_w, frame_h),
                item[1],
            ),
            reverse=True,
        )
        for best in lamps:
            if not _near_held_lamp(best[2], frame_w, frame_h):
                continue
            if _clothing_or_face_lamp(best[2], people, frame_w, frame_h):
                continue
            cap_leftover = any(_same_held_object(best[2], item[2]) for item in leftovers)
            if _shown_lamp_score(best[2], people, frame_w, frame_h) > -1.5 or cap_leftover:
                kept.append(best)
                break
    if fans:
        lamp_refs = [item for item in kept if item[0] == "lamp"] or lamps
        fans = [
            item
            for item in fans
            if not any(_same_held_object(lamp[2], item[2]) for lamp in lamp_refs)
        ]
        fans.sort(
            key=lambda item: (
                _handheld_score(item[2], people, frame_w, frame_h),
                item[1],
            ),
            reverse=True,
        )
        if fans:
            kept.append(fans[0])
    kept.extend(others)
    return kept


def _cap_under_globe(
    globe: tuple[int, int, int, int], cap: tuple[int, int, int, int]
) -> bool:
    """True when `cap` is the B22 metal base sitting under a lamp globe."""
    gx0, gy0, gx1, gy1 = globe
    cx0, cy0, cx1, cy1 = cap
    gw, gh = max(gx1 - gx0, 1), max(gy1 - gy0, 1)
    cw, ch = max(cx1 - cx0, 1), max(cy1 - cy0, 1)
    gcx = (gx0 + gx1) / 2.0
    ccx = (cx0 + cx1) / 2.0
    if abs(gcx - ccx) > max(gw, cw) * 0.55:
        return False
    if cw > gw * 1.45:
        return False
    # Cap top near globe bottom — stacked, not a second object across the room.
    gap = cy0 - gy1
    if gap < -0.40 * min(gh, ch):
        return False
    if gap > 0.50 * max(gh, ch):
        return False
    return True


def _same_held_object(
    a: tuple[int, int, int, int], b: tuple[int, int, int, int]
) -> bool:
    """Overlap or a globe stacked on its metal cap."""
    return _box_covers(a, b) or _cap_under_globe(a, b) or _cap_under_globe(b, a)


def _box_covers(fan: tuple[int, int, int, int], other: tuple[int, int, int, int]) -> bool:
    """True when a YOLO bottle/lamp box is the same handheld fan."""
    if _iou(fan, other) >= 0.12:
        return True
    fx = (fan[0] + fan[2]) / 2.0
    fy = (fan[1] + fan[3]) / 2.0
    ox = (other[0] + other[2]) / 2.0
    oy = (other[1] + other[3]) / 2.0
    if fan[0] <= ox <= fan[2] and fan[1] <= oy <= fan[3]:
        return True
    return other[0] <= fx <= other[2] and other[1] <= fy <= other[3]


def _dark_square_candidates(frame_bgr: np.ndarray) -> list[tuple[int, int, int, int]]:
    import cv2

    h, w = frame_bgr.shape[:2]
    scale = min(1.0, 360 / max(w, 1))
    small = cv2.resize(frame_bgr, (max(80, int(w * scale)), max(60, int(h * scale)))) if scale < 1 else frame_bgr
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thr = int(max(50, min(125, float(blur.mean()) * 0.72)))
    _, bw = cv2.threshold(blur, thr, 255, cv2.THRESH_BINARY_INV)
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    inv = 1.0 / scale
    sh, sw = small.shape[:2]
    out: list[tuple[int, int, int, int]] = []
    for contour in contours:
        x, y, cw, ch = cv2.boundingRect(contour)
        if cw < 22 or ch < 22:
            continue
        aspect = cw / max(ch, 1)
        if not 0.72 <= aspect <= 1.38:
            continue
        area = (cw * ch) / max(sw * sh, 1)
        if area < 0.012 or area > 0.22:
            continue
        out.append((int(x * inv), int(y * inv), int((x + cw) * inv), int((y + ch) * inv)))
    return out


def find_cooling_fans(
    frame_bgr: np.ndarray,
    people: list[tuple[int, int, int, int]] | None = None,
) -> list[tuple[tuple[int, int, int, int], float]]:
    """Find the demo PC fan. YOLO cannot; white hub + photo match can."""
    people = people or []
    _remember_frame(frame_bgr)

    import cv2

    hub_hits: list[tuple[int, tuple[int, int, int, int]]] = []
    for xyxy in _white_hub_candidates(frame_bgr):
        x0, y0, x1, y1 = xyxy
        if min(x1 - x0, y1 - y0) < 36:
            continue
        crop = frame_bgr[max(0, y0) : y1, max(0, x0) : x1]
        if crop.size == 0:
            continue
        held = _fan_on_person(xyxy, people)
        bright = _has_bright_hub(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY))
        if held and not bright:
            continue
        if looks_like_pc_fan(frame_bgr, xyxy):
            hub_hits.append(((x1 - x0) * (y1 - y0), xyxy))
    if hub_hits:
        hub_hits.sort(reverse=True)
        return [(hub_hits[0][1], 0.84)]

    impeller_hits: list[tuple[int, tuple[int, int, int, int]]] = []
    for xyxy in _dark_impeller_candidates(frame_bgr):
        if looks_like_pc_fan(frame_bgr, xyxy):
            x0, y0, x1, y1 = xyxy
            impeller_hits.append(((x1 - x0) * (y1 - y0), xyxy))
    if impeller_hits:
        impeller_hits.sort(reverse=True)
        return [(impeller_hits[0][1], 0.86)]

    hit = match_pc_fan_template(frame_bgr)
    if hit is not None:
        xyxy, score = hit
        # A held fan sits on the person box — still accept a strong template / shape match.
        if score >= 0.62 or looks_like_pc_fan(frame_bgr, xyxy):
            if not _fan_on_person(xyxy, people) or score >= 0.55 or looks_like_pc_fan(frame_bgr, xyxy):
                return [(xyxy, min(0.92, 0.55 + 0.4 * score))]

    for xyxy in _dark_square_candidates(frame_bgr):
        if not looks_like_pc_fan(frame_bgr, xyxy):
            continue
        # Faces rarely pass looks_like_pc_fan; held fans do even when inside the person box.
        return [(xyxy, 0.78)]
    return []


_BULB_TMPLS: list[tuple[np.ndarray, np.ndarray]] = []
_BULB_TMPL_READY = False
_GLOBE_FRAME_ID = 0
_GLOBE_CANDS: list[tuple[int, int, int, int]] | None = None


def _remember_frame(frame_bgr: np.ndarray) -> None:
    """Drop stale globe cache. Webcam buffers reuse the same array id."""
    global _GLOBE_FRAME_ID, _GLOBE_CANDS
    _GLOBE_FRAME_ID = id(frame_bgr)
    _GLOBE_CANDS = None


def _white_globe_candidates(frame_bgr: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Boxes around a solid white circular globe (LED bulb, not a cup rim)."""
    import cv2

    global _GLOBE_CANDS
    fid = id(frame_bgr)
    if fid == _GLOBE_FRAME_ID and _GLOBE_CANDS is not None:
        return _GLOBE_CANDS

    h, w = frame_bgr.shape[:2]
    scale = min(1.0, 480 / max(w, 1))
    small = (
        cv2.resize(frame_bgr, (max(80, int(w * scale)), max(60, int(h * scale))))
        if scale < 1
        else frame_bgr
    )
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    white = ((hsv[:, :, 2] >= 165) & (hsv[:, :, 1] <= 80)).astype(np.uint8) * 255
    white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    inv = 1.0 / scale
    sh, sw = small.shape[:2]
    span = min(sw, sh)
    out: list[tuple[int, int, int, int]] = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < 220:
            continue
        (_cx, _cy), radius = cv2.minEnclosingCircle(contour)
        if radius < 12:
            continue
        circ = area / max(np.pi * radius * radius, 1.0)
        near_edge = (
            _cx < radius * 1.25
            or _cy < radius * 1.25
            or _cx > sw - radius * 1.25
            or _cy > sh - radius * 1.25
        )
        if circ < (0.28 if near_edge else 0.38):
            continue
        if radius > span * 0.72:
            continue
        # Face-sized flood fills are rejected later; keep large close-up globes.
        if radius > span * 0.55 and circ < 0.55:
            continue
        if radius > span * 0.48 and circ < 0.50:
            continue
        mask = np.zeros((sh, sw), np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, -1)
        interior = gray[mask > 0]
        if interior.size < 20 or float(interior.mean()) < 170:
            continue
        # A cup looking down has a dark well. A bulb globe is solid.
        r_in = max(3, int(radius * 0.35))
        yy, xx = np.ogrid[:sh, :sw]
        core = (np.sqrt((yy - _cy) ** 2 + (xx - _cx) ** 2) <= r_in)
        if core.any() and float(gray[core].mean()) < 155:
            continue
        pad_x = radius * 1.15
        pad_y_up = radius * 1.10
        pad_y_dn = radius * 1.85
        if radius / max(span, 1) > 0.30:
            pad_x = radius * 1.05
            pad_y_up = radius * 1.05
            pad_y_dn = radius * 1.28
        x0 = int((_cx - pad_x) * inv)
        y0 = int((_cy - pad_y_up) * inv)
        x1 = int((_cx + pad_x) * inv)
        y1 = int((_cy + pad_y_dn) * inv)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        if x1 - x0 >= 24 and y1 - y0 >= 28:
            out.append((x0, y0, x1, y1))
        # Close-up globe: a long holder tail makes the box fail the roundness check.
        gx0 = int((_cx - radius * 1.08) * inv)
        gy0 = int((_cy - radius * 1.08) * inv)
        gx1 = int((_cx + radius * 1.08) * inv)
        gy1 = int((_cy + radius * 1.08) * inv)
        gx0, gy0 = max(0, gx0), max(0, gy0)
        gx1, gy1 = min(w, gx1), min(h, gy1)
        if gx1 - gx0 >= 24 and gy1 - gy0 >= 28 and (gx0, gy0, gx1, gy1) != (x0, y0, x1, y1):
            out.append((gx0, gy0, gx1, gy1))
    if fid == _GLOBE_FRAME_ID:
        _GLOBE_CANDS = out
    return out


def _bright_globe_candidates(frame_bgr: np.ndarray) -> list[tuple[int, int, int, int]]:
    """ON bulb: saturation clip breaks HSV white mask — use luminance blobs."""
    import cv2

    h, w = frame_bgr.shape[:2]
    scale = min(1.0, 480 / max(w, 1))
    small = (
        cv2.resize(frame_bgr, (max(80, int(w * scale)), max(60, int(h * scale))))
        if scale < 1
        else frame_bgr
    )
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    inv = 1.0 / scale
    sh, sw = small.shape[:2]
    span = min(sw, sh)
    out: list[tuple[int, int, int, int]] = []
    p90 = float(np.percentile(gray, 90))
    thresholds = {
        int(max(168, p90 - 14)),
        int(max(172, p90 - 8)),
        int(max(176, p90 - 2)),
        int(max(180, p90 + 2)),
    }
    for thr in thresholds:
        mask = (gray >= thr).astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = float(cv2.contourArea(contour))
            if area < 180:
                continue
            (_cx, _cy), radius = cv2.minEnclosingCircle(contour)
            if radius < 10:
                continue
            circ = area / max(np.pi * radius * radius, 1.0)
            if circ < 0.20:
                continue
            if radius > span * 0.78:
                continue
            mask_i = np.zeros((sh, sw), np.uint8)
            cv2.drawContours(mask_i, [contour], -1, 255, -1)
            interior = gray[mask_i > 0]
            if interior.size < 16 or float(interior.mean()) < 178:
                continue
            pad = radius * 1.12
            x0 = int(max(0, (_cx - pad) * inv))
            y0 = int(max(0, (_cy - pad) * inv))
            x1 = int(min(w, (_cx + pad) * inv))
            y1 = int(min(h, (_cy + pad * 1.35) * inv))
            if x1 - x0 >= 22 and y1 - y0 >= 26:
                box = (x0, y0, x1, y1)
                if not any(_iou(box, other) >= 0.40 for other in out):
                    out.append(box)
    if scale < 1.0:
        gray_f = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        thr_f = max(175, int(float(np.percentile(gray_f, 88))))
        mask_f = (gray_f >= thr_f).astype(np.uint8) * 255
        mask_f = cv2.morphologyEx(mask_f, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
        contours_f, _ = cv2.findContours(mask_f, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        span_f = min(h, w)
        for contour in contours_f:
            area = float(cv2.contourArea(contour))
            if area < 320:
                continue
            (_cx, _cy), radius = cv2.minEnclosingCircle(contour)
            if radius < 14 or radius > span_f * 0.55:
                continue
            circ = area / max(np.pi * radius * radius, 1.0)
            if circ < 0.18:
                continue
            pad = radius * 1.10
            x0 = int(max(0, _cx - pad))
            y0 = int(max(0, _cy - pad))
            x1 = int(min(w, _cx + pad))
            y1 = int(min(h, _cy + pad * 1.32))
            if x1 - x0 >= 24 and y1 - y0 >= 28:
                box = (x0, y0, x1, y1)
                if not any(_iou(box, other) >= 0.40 for other in out):
                    out.append(box)
    return out


def _globe_lamp_candidates(frame_bgr: np.ndarray) -> list[tuple[int, int, int, int]]:
    white = _white_globe_candidates(frame_bgr)
    out = list(white)
    for box in _bright_globe_candidates(frame_bgr):
        if not _lit_globe_on(frame_bgr, box):
            continue
        if any(_iou(box, other) >= 0.45 for other in out):
            continue
        out.append(box)
    return out


def _crop_led_bulb(bgr: np.ndarray) -> np.ndarray | None:
    """Crop the porcelain globe. Never return the whole photo — that locks the pose."""
    boxes = _white_globe_candidates(bgr)
    h, w = bgr.shape[:2]
    liked = [box for box in boxes if looks_like_led_bulb(bgr, box)]
    use = liked or boxes
    if not use:
        return None

    def _crop_score(box: tuple[int, int, int, int]) -> float:
        area = (box[2] - box[0]) * (box[3] - box[1]) / max(w * h, 1)
        if _distant_glow(box, w, h) and area < 0.02:
            return -1.0
        score = min(area, 0.12)
        if area >= 0.008:
            score += 0.18
        return score

    x0, y0, x1, y1 = max(use, key=_crop_score)
    crop = bgr[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    # A failed crop of the whole scene would only match that photo's layout.
    if crop.shape[0] * crop.shape[1] > 0.48 * w * h:
        return None
    return crop


def _bulb_asset_files() -> list[Path]:
    """User LUKER shots first, then any other led_bulb reference photos."""
    assets = _assets_dir()
    if not assets.is_dir():
        return []
    files = [
        path
        for path in assets.iterdir()
        if path.is_file()
        and path.suffix.lower() in _FAN_IMAGE_SUFFIXES
        and (
            path.stem.lower().startswith("luker_held")
            or path.stem.lower().startswith("luker_webcam")
            or path.stem.lower().startswith("led_bulb")
        )
    ]

    def rank(path: Path) -> tuple[int, str]:
        name = path.stem.lower()
        if name.startswith("luker_webcam"):
            return (0, name)
        if name.startswith("luker_held"):
            return (1, name)
        return (2, name)

    return sorted(files, key=rank)


_MAX_BULB_TEMPLATES = 12


def _pick_bulb_templates(
    loaded: list[tuple[Path, tuple[np.ndarray, np.ndarray]]],
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Keep a spread of webcam poses. Matching every photo every frame is too slow."""
    if not loaded:
        return []
    webcam = [
        item
        for item in loaded
        if item[0].stem.lower().startswith("luker_webcam")
        and item[0].suffix.lower() in {".jpg", ".jpeg"}
    ]
    pool = webcam or loaded
    if len(pool) <= _MAX_BULB_TEMPLATES:
        return [tmpl for _path, tmpl in pool]
    n = len(pool)
    idxs = [int(i * (n - 1) / max(_MAX_BULB_TEMPLATES - 1, 1)) for i in range(_MAX_BULB_TEMPLATES)]
    seen: set[int] = set()
    out: list[tuple[np.ndarray, np.ndarray]] = []
    for i in idxs:
        if i in seen:
            continue
        seen.add(i)
        out.append(pool[i][1])
    return out


def _load_bulb_templates() -> list[tuple[np.ndarray, np.ndarray]]:
    """Webcam / LUKER photos in assets/ are visual references for this lamp."""
    global _BULB_TMPLS, _BULB_TMPL_READY
    if _BULB_TMPL_READY:
        return _BULB_TMPLS
    _BULB_TMPL_READY = True
    import cv2

    loaded: list[tuple[Path, tuple[np.ndarray, np.ndarray]]] = []
    for path in _bulb_asset_files():
        img = cv2.imread(str(path))
        if img is None or img.size == 0:
            continue
        crop = _crop_led_bulb(img)
        if crop is None or crop.size == 0:
            continue
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        loaded.append((path, _prepare_template(gray)))
    _BULB_TMPLS = _pick_bulb_templates(loaded)
    return _BULB_TMPLS


def _busy_print(crop: np.ndarray) -> bool:
    """True for a floral shirt or wallpaper: several similar bright patches."""
    import cv2

    if crop.size == 0:
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    white = ((hsv[:, :, 2] >= 155) & (hsv[:, :, 1] <= 90)).astype(np.uint8) * 255
    white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    areas = sorted((float(cv2.contourArea(c)) for c in contours if cv2.contourArea(c) >= 28), reverse=True)
    if len(areas) < 4:
        return False
    # A porcelain globe dominates its crop. Shirt flowers are similar sizes.
    if areas[0] >= 2.2 * areas[1]:
        return False
    return True


def _lit_globe_on(
    frame_bgr: np.ndarray, xyxy: tuple[int, int, int, int]
) -> bool:
    """ON bulb: blown-out white core — contour globe test often fails."""
    import cv2

    h, w = frame_bgr.shape[:2]
    if not _near_held_lamp(xyxy, w, h):
        return False
    x0, y0, x1, y1 = xyxy
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(w, int(x1)), min(h, int(y1))
    bw, bh = x1 - x0, y1 - y0
    if bw < 20 or bh < 22:
        return False
    aspect = bw / max(bh, 1)
    if not 0.32 <= aspect <= 1.45:
        return False
    crop = frame_bgr[y0:y1, x0:x1]
    if crop.size == 0 or _mostly_skin(crop):
        return False
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    mean = float(gray.mean())
    std = float(gray.std())
    if mean < 165:
        return False
    if std < 10 and mean < 198:
        return False
    hot = (gray >= min(200, mean - 8)).mean()
    if hot < 0.28 and mean < 185:
        return False
    if mean >= 185 or hot >= 0.42:
        return True
    return hot >= 0.34 and mean >= 172


def _solid_white_globe(frame_bgr: np.ndarray, xyxy: tuple[int, int, int, int]) -> bool:
    """True for a closed white LED globe in this box. No fan check (avoids cycles)."""
    import cv2

    h, w = frame_bgr.shape[:2]
    if _lit_globe_on(frame_bgr, xyxy):
        return True
    x0, y0, x1, y1 = xyxy
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(w, int(x1)), min(h, int(y1))
    bw, bh = x1 - x0, y1 - y0
    if bw < 20 or bh < 22:
        return False
    area = (bw * bh) / max(w * h, 1)
    if area < 0.004 or area > 0.82:
        return False
    aspect = bw / max(bh, 1)
    if not 0.32 <= aspect <= 1.35:
        return False
    crop = frame_bgr[y0:y1, x0:x1]
    if crop.size == 0 or _mostly_skin(crop):
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    white = ((hsv[:, :, 2] >= 160) & (hsv[:, :, 1] <= 85)).astype(np.uint8) * 255
    white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False
    contour = max(contours, key=cv2.contourArea)
    c_area = float(cv2.contourArea(contour))
    if c_area < 80:
        return False
    (_cx, _cy), radius = cv2.minEnclosingCircle(contour)
    if radius < 8:
        return False
    circ = c_area / max(np.pi * radius * radius, 1.0)
    near_edge = x0 <= 8 or y0 <= 8 or x1 >= w - 8 or y1 >= h - 8
    if circ < (0.28 if near_edge else 0.36):
        return False
    ch, cw = gray.shape[:2]
    if radius / max(min(ch, cw), 1) < 0.18:
        return False
    mask = np.zeros((ch, cw), np.uint8)
    cv2.drawContours(mask, [contour], -1, 255, -1)
    interior = gray[mask > 0]
    if interior.size < 16 or float(interior.mean()) < 160:
        return False
    globe_frac = float((mask > 0).mean())
    pad = max(8, int(0.30 * max(bw, bh)))
    ay0, ax0 = max(0, y0 - pad), max(0, x0 - pad)
    around = frame_bgr[ay0 : min(h, y1 + pad), ax0 : min(w, x1 + pad)]
    # Shirt flowers sit in more print. A real globe may sit beside a busy shirt.
    if globe_frac < 0.32 and around.size and _busy_print(around):
        return False
    x, y, rw2, rh2 = cv2.boundingRect(contour)
    extent = c_area / max(float(rw2 * rh2), 1.0)
    # A filled rectangle (ID badge) is not a globe.
    if extent >= 0.88:
        return False
    # ID badges are square-ish slabs that do not fill the crop like a porcelain globe.
    rect = cv2.minAreaRect(contour)
    rw, rh = rect[1]
    if (
        area < 0.10
        and globe_frac < 0.28
        and min(rw, rh) / max(rw, rh, 1.0) >= 0.82
        and circ < 0.68
    ):
        return False
    yy, xx = np.ogrid[:ch, :cw]
    core = np.sqrt((yy - _cy) ** 2 + (xx - _cx) ** 2) <= max(3, radius * 0.35)
    if core.any() and float(gray[core].mean()) < 150:
        return False
    # A PC-fan hub sticker is a small white disc with blades around it.
    # A porcelain globe fills the crop; holder vents must not count as blades.
    if float(gray.mean()) < 135 and globe_frac < 0.28 and _has_radial_blades(gray, peak_min=6.0):
        return False
    # Faces and palms are pink, not a porcelain globe.
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    skin = (((hue <= 22) | (hue >= 160)) & (sat >= 35) & (sat <= 175) & (val >= 50)).mean()
    if skin > 0.62 and globe_frac < 0.08:
        return False
    # A wardrobe-sized crop with a tiny highlight is not a held bulb.
    if area >= 0.12 and globe_frac < 0.10:
        return False
    # Tight white hub on a fan: expand and look for blades even if the crop is the disc.
    if area < 0.025:
        hub_pad = int(max(bw, bh) * 2.2)
        hx0, hy0 = max(0, x0 - hub_pad), max(0, y0 - hub_pad)
        hx1, hy1 = min(w, x1 + hub_pad), min(h, y1 + hub_pad)
        if (hx1 - hx0) > bw + 8 and (hy1 - hy0) > bh + 8:
            hub_exp = cv2.cvtColor(frame_bgr[hy0:hy1, hx0:hx1], cv2.COLOR_BGR2GRAY)
            if float(hub_exp.mean()) < 108 and _has_radial_blades(hub_exp, peak_min=6.0):
                return False
    pad = int(max(bw, bh) * 0.90)
    ex0, ey0 = max(0, x0 - pad), max(0, y0 - pad)
    ex1, ey1 = min(w, x1 + pad), min(h, y1 + pad)
    # A filled globe with a holder looks like blades when the expand crop hits the frame.
    expand_clipped = x0 < pad or y0 < pad or x1 + pad > w or y1 + pad > h
    holder_globe = circ < 0.70 and expand_clipped and area < 0.052
    if (
        area < 0.08
        and not holder_globe
        and (ex1 - ex0) > bw + 8
        and (ey1 - ey0) > bh + 8
    ):
        exp = cv2.cvtColor(frame_bgr[ey0:ey1, ex0:ex1], cv2.COLOR_BGR2GRAY)
        if float(exp.mean()) < 108 and _has_radial_blades(exp, peak_min=6.0):
            return False
    return True


def _globe_in_or_above(
    frame_bgr: np.ndarray, xyxy: tuple[int, int, int, int]
) -> bool:
    """True when this box is a bulb, contains a globe, or is the cap under one."""
    if _solid_white_globe(frame_bgr, xyxy):
        return True
    h, w = frame_bgr.shape[:2]
    x0, y0, x1, y1 = xyxy
    bw, bh = max(x1 - x0, 1), max(y1 - y0, 1)
    cx = (x0 + x1) / 2.0
    for gx0, gy0, gx1, gy1 in _white_globe_candidates(frame_bgr):
        gcx = (gx0 + gx1) / 2.0
        gcy = (gy0 + gy1) / 2.0
        inside = x0 - 6 <= gcx <= x1 + 6 and y0 - 6 <= gcy <= y1 + 6
        above = abs(gcx - cx) <= bw * 0.70 and gcy <= y0 + 0.55 * bh and gy1 >= y0 - 0.40 * bh
        if (inside or above) and _solid_white_globe(frame_bgr, (gx0, gy0, gx1, gy1)):
            return True
    up = (
        max(0, x0 - bw // 5),
        max(0, y0 - int(bh * 2.4)),
        min(w, x1 + bw // 5),
        min(h, y1),
    )
    return up != (x0, y0, x1, y1) and _solid_white_globe(frame_bgr, up)


def looks_like_led_bulb(frame_bgr: np.ndarray, xyxy: tuple[int, int, int, int]) -> bool:
    """True for a closed white LED globe — not a face or an open cup."""
    return _solid_white_globe(frame_bgr, xyxy)


def match_led_bulb_template(
    frame_bgr: np.ndarray,
) -> tuple[tuple[int, int, int, int], float] | None:
    import cv2

    templates = _load_bulb_templates()
    if not templates:
        return None
    h, w = frame_bgr.shape[:2]
    search_w = min(w, 320)
    scale = search_w / max(w, 1)
    small = cv2.resize(frame_bgr, (search_w, max(48, int(h * scale)))) if scale < 1 else frame_bgr
    g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    best_score = 0.0
    best_box: tuple[int, int, int, int] | None = None
    max_side = int(min(small.shape[:2]) * 0.62)
    for gray_t, _edge_t in templates:
        tw, th = gray_t.shape[1], gray_t.shape[0]
        ratio = tw / max(th, 1)
        for side in range(40, max_side + 1, 20):
            rw = side
            rh = max(28, int(side / max(ratio, 0.4)))
            if rh >= g.shape[0] or rw >= g.shape[1]:
                continue
            t = cv2.resize(gray_t, (rw, rh))
            _mn, mx, _ml, loc = cv2.minMaxLoc(cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED))
            if mx > best_score:
                best_score = float(mx)
                best_box = (loc[0], loc[1], loc[0] + rw, loc[1] + rh)
            if best_score >= 0.82:
                break
        if best_score >= 0.82:
            break
    if best_box is None or best_score < 0.80:
        return None
    inv = 1.0 / scale
    x0, y0, x1, y1 = best_box
    xyxy = (int(x0 * inv), int(y0 * inv), int(x1 * inv), int(y1 * inv))
    if not looks_like_led_bulb(frame_bgr, xyxy):
        return None
    return xyxy, best_score


def _globe_quality(frame_bgr: np.ndarray, xyxy: tuple[int, int, int, int]) -> float:
    """Closer compact globes win. Face-sized top blobs and far lights lose."""
    import cv2

    h, w = frame_bgr.shape[:2]
    x0, y0 = max(0, int(xyxy[0])), max(0, int(xyxy[1]))
    x1, y1 = min(w, int(xyxy[2])), min(h, int(xyxy[3]))
    crop = frame_bgr[y0:y1, x0:x1]
    if crop.size == 0:
        return -1.0
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    white = ((hsv[:, :, 2] >= 160) & (hsv[:, :, 1] <= 85)).mean()
    area = (x1 - x0) * (y1 - y0) / max(w * h, 1)
    cy = (y0 + y1) / 2.0 / max(h, 1)
    if not _near_held_lamp(xyxy, w, h):
        return -20.0
    if _oversized_face_lamp(xyxy, [], w, h):
        return -18.0
    # Compact mid-frame held globe beats a huge upper slab.
    score = min(area, 0.14) * 30.0 + float(white) * 0.7
    if 0.025 <= area <= 0.14 and 0.32 <= cy <= 0.88:
        score += 5.0
    if area >= 0.045 and cy >= 0.28:
        score += 2.5
    if y0 <= 2 and area > 0.10 and white < 0.40:
        score -= 14.0
    # Giant close-up porcelain is OK; a dull face-sized slab is not.
    if area > 0.22 and white < 0.38:
        score -= 12.0
    elif area > 0.30:
        score -= 2.0
    return score


def find_led_bulbs(
    frame_bgr: np.ndarray,
    people: list[tuple[int, int, int, int]] | None = None,
) -> list[tuple[tuple[int, int, int, int], float]]:
    """Find a close held white LED bulb. Far room lights never count."""
    people = people or []
    _remember_frame(frame_bgr)
    h, w = frame_bgr.shape[:2]
    hits: list[tuple[float, float, tuple[int, int, int, int]]] = []
    for xyxy in _globe_lamp_candidates(frame_bgr):
        if not (looks_like_led_bulb(frame_bgr, xyxy) or _lit_globe_on(frame_bgr, xyxy)):
            continue
        lit = _lit_globe_on(frame_bgr, xyxy)
        if not _near_held_lamp(xyxy, w, h):
            continue
        if not lit and _distant_glow(xyxy, w, h):
            continue
        if _clothing_or_face_lamp(xyxy, people, w, h):
            continue
        if _oversized_face_lamp(xyxy, people, w, h):
            continue
        area = (xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1]) / max(w * h, 1)
        hits.append((_globe_quality(frame_bgr, xyxy), area, xyxy))
    if hits:
        hits.sort(reverse=True)
        unique: list[tuple[float, float, tuple[int, int, int, int]]] = []
        for item in hits:
            floor = -18.0 if _lit_globe_on(frame_bgr, item[2]) else -12.0
            if item[0] < floor:
                continue
            if any(_iou(item[2], other[2]) >= 0.35 for other in unique):
                continue
            unique.append(item)
        # Closest / largest first. Shirt flowers are many similar mid discs.
        if not unique:
            pass
        elif (
            len(unique) >= 3
            and unique[0][1] < 1.8 * unique[1][1]
            and unique[0][1] < 0.06
            and not _lit_globe_on(frame_bgr, unique[0][2])
        ):
            return []
        else:
            conf = 0.91 if _lit_globe_on(frame_bgr, unique[0][2]) else 0.88
            return [(unique[0][2], conf)]
    hit = match_led_bulb_template(frame_bgr)
    if hit is not None:
        xyxy, score = hit
        if (
            _near_held_lamp(xyxy, w, h)
            and not _background_slab(xyxy, w, h)
            and not _distant_glow(xyxy, w, h)
            and not _clothing_or_face_lamp(xyxy, people, w, h)
            and not _oversized_face_lamp(xyxy, people, w, h)
        ):
            return [(xyxy, min(0.93, 0.55 + 0.4 * score))]
    return []


class ObjectDetector:
    """Open-vocabulary detector with IoU-stable IDs across frames."""

    def __init__(
        self,
        model_name: str = "yoloe-26s-seg.pt",
        fan_model_name: str = "",
        conf: float = 0.12,
        target_classes: set[str] | None = None,
        every_n_frames: int = 3,
        iou_match: float = 0.3,
        imgsz: int = 512,
    ):
        self.conf = conf
        self.target_classes = target_classes or DEFAULT_TARGET_CLASSES
        self.every_n_frames = max(1, every_n_frames)
        self.iou_match = iou_match
        self.imgsz = imgsz
        self.model_name = model_name
        self.fan_model_name = (fan_model_name or "").strip()
        self.lamp_weights_resolved: str | None = None
        self.fan_weights_resolved: str | None = None
        self.custom_min_conf = 0.35
        self._frame_i = 0
        self._last: list[DetectedObject] = []
        self._next_id = 1
        self.last_people: list[tuple[int, int, int, int]] = []
        self._people_misses = 0
        self._pending_lamps: list[tuple[tuple[int, int, int, int], float]] = []
        self._pending_fans: list[tuple[tuple[int, int, int, int], float]] = []
        self._fan_misses = 0
        self._lamp_misses = 0
        self._lit_lamp_xyxy: tuple[int, int, int, int] | None = None
        self._lit_lamp_miss = 0
        self.match_fans = True
        self.min_area_frac = 0.003
        self.max_area_frac = 0.45
        self.nms_iou = 0.55
        self.max_objects = 6
        self.available = False
        self.model = None
        self.fan_model = None
        self._custom_lamp = False
        self._custom_fan = False
        try:
            from ultralytics import YOLO

            root = Path(__file__).resolve().parents[2]
            lamp_resolved = Path(model_name)
            if not lamp_resolved.is_file():
                lamp_resolved = root / model_name
            if lamp_resolved.is_file():
                self.lamp_weights_resolved = str(lamp_resolved.resolve())
            print(f"[detector] loading {self.lamp_weights_resolved or model_name} …", flush=True)
            self.model = YOLO(str(lamp_resolved if lamp_resolved.is_file() else model_name))
            if _is_open_vocab(model_name) and hasattr(self.model, "set_classes"):
                self.model.set_classes(list(PROMPT_CLASSES))
                print(f"[detector] prompts: {', '.join(PROMPT_CLASSES)}", flush=True)
            self._custom_lamp = _model_is_custom_lamp(self.model)
            if self._custom_lamp:
                print("[detector] custom lamp weights — skipping YOLOE prompts", flush=True)
            if self.fan_model_name:
                fan_resolved = Path(self.fan_model_name)
                if not fan_resolved.is_file():
                    fan_resolved = root / self.fan_model_name
                if fan_resolved.is_file():
                    self.fan_weights_resolved = str(fan_resolved.resolve())
                    print(f"[detector] loading fan {self.fan_weights_resolved} …", flush=True)
                    self.fan_model = YOLO(self.fan_weights_resolved)
                    self._custom_fan = _model_is_custom_fan(self.fan_model)
                    if self._custom_fan:
                        print("[detector] custom fan weights loaded", flush=True)
                else:
                    print(f"[detector] fan weights missing ({self.fan_model_name})", flush=True)
            self.available = True
        except Exception as exc:  # noqa: BLE001
            print(f"[detector] YOLO unavailable ({exc}). Using virtual slots only.", flush=True)

    def reset_tracking(self) -> None:
        self._frame_i = 0
        self._last = []
        self._next_id = 1
        self.last_people = []
        self._people_misses = 0
        self._pending_lamps = []
        self._pending_fans = []

    def warmup(self, imgsz: int | None = None) -> None:
        """Run one dummy predict so the first live frame is not a cold start."""
        if not self.available or self.model is None:
            return
        import numpy as np

        size = int(imgsz or self.imgsz)
        dummy = np.zeros((size, size, 3), np.uint8)
        self.model.predict(dummy, conf=self.conf, imgsz=size, verbose=False, max_det=1)
        fan_model = getattr(self, "fan_model", None)
        if fan_model is not None:
            fan_model.predict(dummy, conf=self.conf, imgsz=size, verbose=False, max_det=1)
        self.reset_tracking()

    def info(self) -> dict[str, object]:
        return {
            "lamp_weights": self.lamp_weights_resolved or self.model_name,
            "fan_weights": self.fan_weights_resolved or self.fan_model_name or None,
            "custom_lamp": bool(self._custom_lamp),
            "custom_fan": bool(self._custom_fan),
            "fan_loaded": self.fan_model is not None,
            "heuristic_lamp": not self._custom_lamp,
            "heuristic_fan": getattr(self, "match_fans", True) and not self._custom_fan,
            "yolo_conf": self.conf,
            "custom_min_conf": self.custom_min_conf,
        }

    def detect(self, frame_bgr: np.ndarray) -> list[DetectedObject]:
        self._frame_i += 1
        if (self._frame_i - 1) % self.every_n_frames != 0:
            return self._refresh_lamp_between_yolo(frame_bgr)
        _remember_frame(frame_bgr)

        raw: list[tuple[str, float, tuple[int, int, int, int]]] = []
        people: list[tuple[int, int, int, int]] = []
        if self.available and self.model is not None:
            lamp_conf = min(self.conf, 0.18) if getattr(self, "_custom_lamp", False) else self.conf
            lamp_imgsz = max(int(self.imgsz), 480) if getattr(self, "_custom_lamp", False) else self.imgsz
            results = self.model.predict(
                frame_bgr,
                conf=lamp_conf,
                imgsz=lamp_imgsz,
                verbose=False,
                max_det=10,
            )
            parsed: list[tuple[str, float, tuple[int, int, int, int]]] = []
            if results and results[0].boxes is not None:
                r0 = results[0]
                names = r0.names
                for box in r0.boxes:
                    cls_id = int(box.cls.item())
                    label = canonicalize_label(_name_of(names, cls_id))
                    conf = float(box.conf.item())
                    xyxy = tuple(int(v) for v in box.xyxy[0].tolist())
                    if label in HIDDEN_CLASSES:
                        people.append(xyxy)  # type: ignore[arg-type]
                        continue
                    parsed.append((label, conf, xyxy))  # type: ignore[arg-type]
            if people:
                self.last_people = list(people)
                self._people_misses = 0
            else:
                self._people_misses = getattr(self, "_people_misses", 0) + 1
                if self._people_misses > 8:
                    self.last_people = []
                people = list(getattr(self, "last_people", []))
            fh, fw = frame_bgr.shape[:2]
            for label, conf, xyxy in parsed:
                shown_label, shown_box = label, xyxy
                if label in BULB_LOOKALIKE_CLASSES and looks_like_led_bulb(frame_bgr, xyxy):
                    shown_label = "lamp"
                else:
                    fan_box = None
                    if getattr(self, "match_fans", True) and label in FAN_LOOKALIKE_CLASSES:
                        fan_box = _fan_crop(frame_bgr, xyxy)
                    if fan_box is not None:
                        shown_label, shown_box = "fan", fan_box
                if shown_label in DROPPED_CLASSES:
                    continue
                shape_ok = (
                    (shown_label == "fan" and looks_like_pc_fan(frame_bgr, shown_box))
                    or (shown_label == "lamp" and looks_like_led_bulb(frame_bgr, shown_box))
                )
                # Fine-tuned lamp weights already know this globe — don't drop a real hit
                # because the geometric matcher is picky under classroom lighting.
                custom_min = float(getattr(self, "custom_min_conf", 0.35))
                if shown_label == "lamp" and getattr(self, "_custom_lamp", False):
                    lamp_floor = max(0.18, min(self.conf, 0.24))
                    if conf < lamp_floor:
                        continue
                    shape_ok = True
                if shown_label == "fan" and getattr(self, "fan_model", None) is not None:
                    continue
                if shown_label == "fan" and getattr(self, "_custom_fan", False):
                    if conf < max(self.conf, custom_min):
                        continue
                    ok_fan, shown_box = _accept_custom_fan_yolo(
                        frame_bgr, shown_box, conf, custom_min
                    )
                    if not ok_fan:
                        continue
                    shape_ok, shown_box = _fan_shape_accepted(
                        frame_bgr, shown_box, conf, custom_min, crop=False
                    )
                    if not shape_ok:
                        continue
                if shown_label == "lamp" and not shape_ok:
                    continue
                if shown_label == "lamp" and conf < max(self.conf, 0.22):
                    continue
                if shown_label == "lamp" and not getattr(self, "_custom_lamp", False):
                    if (
                        not _near_held_lamp(shown_box, fw, fh)
                        or _background_slab(shown_box, fw, fh)
                        or _edge_strip(shown_box, fw, fh)
                        or _distant_glow(shown_box, fw, fh)
                        or _clothing_or_face_lamp(shown_box, people, fw, fh)
                        or _oversized_face_lamp(shown_box, people, fw, fh)
                    ):
                        continue
                if shown_label == "fan" and not shape_ok:
                    if _background_slab(shown_box, fw, fh) or _edge_strip(shown_box, fw, fh):
                        continue
                if shown_label not in self.target_classes:
                    continue
                if shown_label == "fan" and not getattr(self, "match_fans", True):
                    continue
                # A torso YOLO called "fan" is not the cooler. A shape-confirmed fan in the hand is.
                if (
                    shown_label == "fan"
                    and not shape_ok
                    and _fan_on_person(shown_box, people)
                ):
                    continue
                if (
                    shown_label == "fan"
                    and shape_ok
                    and _fan_on_person(shown_box, people)
                    and conf < _custom_fan_trust_conf(custom_min)
                    and not looks_like_pc_fan(frame_bgr, shown_box)
                ):
                    continue
                raw.append((shown_label, conf, shown_box))
            if getattr(self, "fan_model", None) is not None:
                fan_results = self.fan_model.predict(
                    frame_bgr,
                    conf=self.conf,
                    imgsz=self.imgsz,
                    verbose=False,
                    max_det=4,
                )
                if fan_results and fan_results[0].boxes is not None:
                    r0 = fan_results[0]
                    names = r0.names
                    for box in r0.boxes:
                        cls_id = int(box.cls.item())
                        label = canonicalize_label(_name_of(names, cls_id))
                        if label != "fan":
                            continue
                        conf = float(box.conf.item())
                        xyxy = tuple(int(v) for v in box.xyxy[0].tolist())
                        custom_min = float(getattr(self, "custom_min_conf", 0.35))
                        if conf < max(self.conf, custom_min):
                            continue
                        ok, xyxy = _accept_custom_fan_yolo(
                            frame_bgr, xyxy, conf, custom_min
                        )
                        if not ok:
                            continue
                        shaped, xyxy = _fan_shape_accepted(
                            frame_bgr, xyxy, conf, custom_min, crop=False
                        )
                        if not shaped:
                            continue
                        if (
                            _fan_on_person(xyxy, people)
                            and conf < _custom_fan_trust_conf(custom_min)
                            and not looks_like_pc_fan(frame_bgr, xyxy)
                        ):
                            continue
                        if _background_slab(xyxy, fw, fh) or _edge_strip(xyxy, fw, fh):
                            continue
                        raw.append(("fan", conf, xyxy))
        elif getattr(self, "last_people", None):
            self._people_misses = getattr(self, "_people_misses", 0) + 1
            if self._people_misses > 8:
                self.last_people = []
            people = list(getattr(self, "last_people", []))

        h, w = frame_bgr.shape[:2]
        raw = self._merge_globe_lamps(frame_bgr, raw, people, w, h)
        raw = self._dedupe_fans(raw)
        raw = self._require_stable_lamp(raw)
        raw = self._require_stable_fan(raw)
        if not any(item[0] == "fan" for item in raw):
            prev_fans = [p for p in self._last if p.label == "fan"]
            if prev_fans:
                self._fan_misses += 1
                if self._fan_misses <= 3:
                    pf = max(prev_fans, key=lambda p: p.conf)
                    raw.append(("fan", float(pf.conf) * 0.97, pf.xyxy))
            else:
                self._fan_misses = 0
        else:
            self._fan_misses = 0

        if getattr(self, "match_fans", True) and (
            not getattr(self, "_custom_fan", False)
            or not any(item[0] == "fan" for item in raw)
        ):
            for xyxy, conf in find_cooling_fans(frame_bgr, people):
                if _background_slab(xyxy, w, h):
                    break
                overlapping = [item for item in raw if _same_held_object(xyxy, item[2])]
                globe_here = any(
                    item[0] == "lamp" and looks_like_led_bulb(frame_bgr, item[2]) for item in overlapping
                )
                if globe_here:
                    # Cap of a held bulb — keep the lamp, do not promote the cap to a fan.
                    raw = [item for item in raw if item[0] != "fan" or not _same_held_object(xyxy, item[2])]
                else:
                    raw = [
                        item
                        for item in raw
                        if item[0] == "fan" or not _same_held_object(xyxy, item[2])
                    ]
                    if not any(item[0] == "fan" and _same_held_object(xyxy, item[2]) for item in raw):
                        raw.append(("fan", conf, xyxy))
                break

        if not any(item[0] == "lamp" for item in raw):
            prev_lamps = [p for p in self._last if p.label == "lamp"]
            if prev_lamps:
                pl = max(prev_lamps, key=lambda p: p.conf)
                if _lit_globe_on(frame_bgr, pl.xyxy):
                    self._lamp_misses += 1
                    if self._lamp_misses <= 12:
                        raw.append(("lamp", float(pl.conf) * 0.96, pl.xyxy))
                else:
                    self._lamp_misses = 0
            else:
                self._lamp_misses = 0
        else:
            self._lamp_misses = 0

        raw = _collapse_same_object(frame_bgr, raw)
        raw = _keep_held_appliances(raw, people, w, h)
        raw = self._prune(raw, max(w * h, 1))
        objects = self._match_ids(raw)
        self._sync_lit_lamp_track(frame_bgr, objects)
        self._last = objects
        return objects

    def _refresh_lamp_between_yolo(self, frame_bgr: np.ndarray) -> list[DetectedObject]:
        """Globe scan on skipped frames — ON bulbs flicker less between YOLO passes."""
        if not getattr(self, "_lit_lamp_xyxy", None) and not hasattr(self, "_lit_lamp_miss"):
            self._lit_lamp_xyxy = None
            self._lit_lamp_miss = 0
        if not self._last:
            return self._last
        _remember_frame(frame_bgr)
        h, w = frame_bgr.shape[:2]
        people = list(getattr(self, "last_people", []) or [])
        hits = find_led_bulbs(frame_bgr, people)
        out = list(self._last)
        lamp_idx = next((i for i, o in enumerate(out) if o.label == "lamp"), None)
        if hits:
            xyxy, conf = hits[0]
            if lamp_idx is not None:
                prev = out[lamp_idx]
                xyxy = self._smooth_xyxy(prev.xyxy, xyxy, alpha=0.45)
                out[lamp_idx] = DetectedObject(
                    prev.obj_id,
                    prev.label,
                    max(float(prev.conf), float(conf)),
                    xyxy,
                    prev.appliance or appliance_label("lamp"),
                )
            else:
                oid = f"lamp_{self._next_id}"
                self._next_id += 1
                out.append(
                    DetectedObject(
                        oid, "lamp", float(conf), xyxy, appliance_label("lamp")
                    )
                )
            self._lit_lamp_xyxy = xyxy
            self._lit_lamp_miss = 0
        elif self._lit_lamp_xyxy is not None:
            self._lit_lamp_miss += 1
            if self._lit_lamp_miss <= 18 and _lit_globe_on(frame_bgr, self._lit_lamp_xyxy):
                xyxy = self._lit_lamp_xyxy
                for box in _globe_lamp_candidates(frame_bgr):
                    if _iou(box, xyxy) >= 0.10 and _lit_globe_on(frame_bgr, box):
                        xyxy = box
                        break
                self._lit_lamp_xyxy = xyxy
                if lamp_idx is not None:
                    prev = out[lamp_idx]
                    xyxy = self._smooth_xyxy(prev.xyxy, xyxy, alpha=0.38)
                    out[lamp_idx] = DetectedObject(
                        prev.obj_id,
                        prev.label,
                        prev.conf,
                        xyxy,
                        prev.appliance or appliance_label("lamp"),
                    )
                else:
                    oid = f"lamp_{self._next_id}"
                    self._next_id += 1
                    out.append(
                        DetectedObject(
                            oid, "lamp", 0.88, xyxy, appliance_label("lamp")
                        )
                    )
            else:
                self._lit_lamp_xyxy = None
        self._last = out
        return out

    def _sync_lit_lamp_track(
        self, frame_bgr: np.ndarray, objects: list[DetectedObject]
    ) -> None:
        if not hasattr(self, "_lit_lamp_xyxy"):
            self._lit_lamp_xyxy = None
            self._lit_lamp_miss = 0
        for obj in objects:
            if obj.label != "lamp":
                continue
            if _lit_globe_on(frame_bgr, obj.xyxy):
                self._lit_lamp_xyxy = obj.xyxy
                self._lit_lamp_miss = 0
                return
        if self._lit_lamp_xyxy is not None:
            self._lit_lamp_miss += 1
            if self._lit_lamp_miss > 18:
                self._lit_lamp_xyxy = None

    def _merge_globe_lamps(
        self,
        frame_bgr: np.ndarray,
        raw: list[tuple[str, float, tuple[int, int, int, int]]],
        people: list[tuple[int, int, int, int]],
        frame_w: int,
        frame_h: int,
    ) -> list[tuple[str, float, tuple[int, int, int, int]]]:
        """Vision fallback when YOLO misses an ON bulb (blown-out globe)."""
        for xyxy, conf in find_led_bulbs(frame_bgr, people):
            if _background_slab(xyxy, frame_w, frame_h):
                continue
            merged: list[tuple[str, float, tuple[int, int, int, int]]] = []
            have_lamp = False
            for item in raw:
                if item[0] != "lamp" or not _same_held_object(xyxy, item[2]):
                    merged.append(item)
                    continue
                merged.append(("lamp", max(item[1], conf), _union_box(item[2], xyxy)))
                have_lamp = True
            if not have_lamp:
                merged = list(raw)
                merged.append(("lamp", conf, xyxy))
            raw = merged
            break
        return raw

    def _require_stable_lamp(
        self, raw: list[tuple[str, float, tuple[int, int, int, int]]]
    ) -> list[tuple[str, float, tuple[int, int, int, int]]]:
        """One-frame YOLO lamp flashes (shirt, badge) must not lock. Globes at 0.70+ pass."""
        pending = getattr(self, "_pending_lamps", [])
        next_pending: list[tuple[tuple[int, int, int, int], float]] = []
        out: list[tuple[str, float, tuple[int, int, int, int]]] = []
        for label, conf, xyxy in raw:
            if label != "lamp" or conf >= 0.70:
                out.append((label, conf, xyxy))
                if label == "lamp":
                    next_pending.append((xyxy, conf))
                continue
            next_pending.append((xyxy, conf))
            if any(_iou(xyxy, prev[0]) >= 0.40 for prev in pending):
                out.append((label, conf, xyxy))
        self._pending_lamps = next_pending
        return out

    def _dedupe_fans(
        self, raw: list[tuple[str, float, tuple[int, int, int, int]]]
    ) -> list[tuple[str, float, tuple[int, int, int, int]]]:
        """One fan box per held object — lamp + fan models must not fight."""
        fans = [item for item in raw if item[0] == "fan"]
        if len(fans) <= 1:
            return raw
        rest = [item for item in raw if item[0] != "fan"]
        fans.sort(key=lambda item: item[1], reverse=True)
        kept: list[tuple[str, float, tuple[int, int, int, int]]] = []
        for item in fans:
            if any(_iou(item[2], other[2]) >= 0.22 for other in kept):
                continue
            kept.append(item)
        return rest + kept

    def _require_stable_fan(
        self, raw: list[tuple[str, float, tuple[int, int, int, int]]]
    ) -> list[tuple[str, float, tuple[int, int, int, int]]]:
        """Weak fan YOLO flashes (hair) need two frames; strong hits pass immediately."""
        pending = getattr(self, "_pending_fans", [])
        next_pending: list[tuple[tuple[int, int, int, int], float]] = []
        out: list[tuple[str, float, tuple[int, int, int, int]]] = []
        trust = _custom_fan_trust_conf(float(getattr(self, "custom_min_conf", 0.35)))
        instant = max(0.78, trust + 0.12)
        for label, conf, xyxy in raw:
            if label != "fan":
                out.append((label, conf, xyxy))
                continue
            if conf >= instant:
                out.append((label, conf, xyxy))
                next_pending.append((xyxy, conf))
                continue
            next_pending.append((xyxy, conf))
            if any(_iou(xyxy, prev[0]) >= 0.28 for prev in pending):
                out.append((label, conf, xyxy))
        self._pending_fans = next_pending
        return out

    def _prune(
        self, raw: list[tuple[str, float, tuple[int, int, int, int]]], frame_area: int
    ) -> list[tuple[str, float, tuple[int, int, int, int]]]:
        """Drop noise boxes and overlapping duplicates before ID matching."""
        sized: list[tuple[str, float, tuple[int, int, int, int]]] = []
        for label, conf, xyxy in raw:
            if label == "cup":
                continue
            x0, y0, x1, y1 = xyxy
            area = max(0, x1 - x0) * max(0, y1 - y0) / frame_area
            max_area = 0.82 if label == "lamp" else self.max_area_frac
            if area < self.min_area_frac or area > max_area:
                continue
            sized.append((label, conf, xyxy))
        sized.sort(key=lambda t: t[1], reverse=True)
        kept: list[tuple[str, float, tuple[int, int, int, int]]] = []
        fan_kept = False
        for item in sized:
            if item[0] == "fan":
                if fan_kept:
                    continue
                x0, y0, x1, y1 = item[2]
                fan_area = max(0, x1 - x0) * max(0, y1 - y0) / frame_area
                if fan_area > 0.32:
                    continue
                fan_kept = True
            if any(_iou(item[2], other[2]) >= self.nms_iou for other in kept):
                continue
            kept.append(item)
            if len(kept) >= self.max_objects:
                break
        return kept

    def _smooth_xyxy(
        self,
        prev: tuple[int, int, int, int],
        new: tuple[int, int, int, int],
        alpha: float = 0.34,
    ) -> tuple[int, int, int, int]:
        return tuple(int(round(alpha * n + (1.0 - alpha) * p)) for p, n in zip(prev, new))

    def _match_ids(
        self, raw: list[tuple[str, float, tuple[int, int, int, int]]]
    ) -> list[DetectedObject]:
        used_prev: set[str] = set()
        out: list[DetectedObject] = []
        for label, conf, xyxy in raw:
            best_id = None
            best_iou = 0.0
            best_prev: DetectedObject | None = None
            match_min = 0.16 if label == "fan" else self.iou_match
            for prev in self._last:
                if prev.label != label or prev.obj_id in used_prev:
                    continue
                iou = _iou(xyxy, prev.xyxy)
                if iou > best_iou:
                    best_iou = iou
                    best_id = prev.obj_id
                    best_prev = prev
            if best_id is not None and best_iou >= match_min:
                obj_id = best_id
                used_prev.add(best_id)
                if label == "fan" and best_prev is not None:
                    xyxy = self._smooth_xyxy(best_prev.xyxy, xyxy)
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
