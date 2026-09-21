"""Map COCO labels → clear on-screen names (honest stand-ins, not fake Plug)."""

from __future__ import annotations

# Friendly names keep the real object identity. We do NOT rename a phone to "Plug"
# anymore — that confused live demos. Detected items are selectable appliances
# under their own names until a custom lamp/fan model is trained.
COCO_FRIENDLY: dict[str, str] = {
    "cell phone": "Phone",
    "bottle": "Bottle",
    "cup": "Lamp",
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
    "fan": "Fan",
    "cooling fan": "Fan",
    "lamp": "Lamp",
    "light bulb": "Lamp",
    "led bulb": "Lamp",
    "bulb": "Lamp",
}


# Phase-1 ESP32 hub only has three relays. UI keeps honest names;
# actuation maps stand-in objects onto lamp / fan / plug.
_RELAY_KEYWORDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("lamp", "bulb", "light", "bottle", "vase", "plant", "cup"), "lamp"),
    (("fan", "glass", "bowl"), "fan"),
    (("plug", "phone", "remote", "keyboard", "mouse", "laptop", "tv"), "plug"),
)


def appliance_label(coco_label: str) -> str:
    """Return a clear display name for a detected object."""
    return COCO_FRIENDLY.get(coco_label, coco_label.title())


def relay_id_for(device_id: str, label: str | None = None) -> str:
    """Map a selected target onto lamp | fan | plug for MQTT/ESP32."""
    if device_id in {"lamp", "fan", "plug"}:
        return device_id
    blob = f"{device_id} {label or ''}".lower()
    for keys, relay in _RELAY_KEYWORDS:
        if any(k in blob for k in keys):
            return relay
    return "plug"


def display_label(coco_label: str, conf: float | None = None) -> str:
    """HUD text like 'Phone 0.85'."""
    base = appliance_label(coco_label)
    if conf is None:
        return base
    return f"{base} {conf:.2f}"
