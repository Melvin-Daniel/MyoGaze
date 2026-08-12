"""Map COCO labels → clear on-screen names (honest stand-ins, not fake Plug)."""

from __future__ import annotations

# Friendly names keep the real object identity. We do NOT rename a phone to "Plug"
# anymore — that confused live demos. Detected items are selectable appliances
# under their own names until a custom lamp/fan model is trained.
COCO_FRIENDLY: dict[str, str] = {
    "cell phone": "Phone",
    "bottle": "Bottle",
    "cup": "Cup",
    "wine glass": "Glass",
    "remote": "Remote",
    "book": "Book",
    "laptop": "Laptop",
    "tv": "TV",
    "clock": "Clock",
    "vase": "Vase",
    "potted plant": "Plant",
    "keyboard": "Keyboard",
    "mouse": "Mouse",
    "bowl": "Bowl",
    "chair": "Chair",
    "toothbrush": "Brush",
    "scissors": "Scissors",
    "teddy bear": "Toy",
    "sports ball": "Ball",
    "backpack": "Bag",
    "handbag": "Bag",
    "umbrella": "Umbrella",
}


def appliance_label(coco_label: str) -> str:
    """Return a clear display name for a detected object."""
    return COCO_FRIENDLY.get(coco_label, coco_label.title())


def display_label(coco_label: str, conf: float | None = None) -> str:
    """HUD text like 'Phone 0.85'."""
    base = appliance_label(coco_label)
    if conf is None:
        return base
    return f"{base} {conf:.2f}"
