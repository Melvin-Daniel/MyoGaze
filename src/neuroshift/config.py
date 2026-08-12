"""Runtime config — swap camera / EMG source without rewriting fusion."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any


@dataclass
class Config:
    # Camera: 0 = laptop cam; change when eMeet S600 is plugged in
    camera_index: int = 0
    frame_width: int = 1280
    frame_height: int = 720
    # Mirror like a selfie so your left = screen left
    mirror_preview: bool = True

    # Gaze selection (Phase-1 head/face proxy)
    dwell_seconds: float = 0.55
    gaze_select_threshold: float = 0.50
    # How far you must turn head to leave center (Fan)
    yaw_side_threshold: float = 0.20
    # Stick to current slot unless yaw crosses threshold by this extra margin
    yaw_hysteresis: float = 0.10
    # EMA on yaw/pitch (higher = snappier, lower = smoother)
    gaze_smooth_alpha: float = 0.28

    # YOLO appliance stand-ins (COCO classes until custom lamp/fan model)
    yolo_model: str = "yolov8n.pt"
    yolo_conf: float = 0.35
    yolo_every_n_frames: int = 2

    # Fake EMG until MyoWare + ESP32 arrive
    # keyboard = SPACE pulse | mouse = vertical effort | hardware = serial | script = mock
    emg_mode: str = "keyboard"
    emg_confirm_key: str = "space"
    emg_confirm_threshold: float = 0.5
    # SPACE = one-shot pulse (ms), not a held switch
    emg_pulse_ms: int = 380
    # Ignore another confirm shortly after an ACT (debounce)
    act_cooldown_seconds: float = 0.70
    # Serial MyoWare bridge (used when emg_mode=hardware)
    emg_serial_port: str = "COM3"
    emg_serial_baud: int = 115200

    # Decision
    abstain_label: str = "ABSTAIN"
    act_label: str = "ACT"

    # MQTT (off by default until broker/ESP32 ready)
    mqtt_enabled: bool = False
    mqtt_host: str = "127.0.0.1"
    mqtt_port: int = 1883

    # Product / mock / live stream
    product_name: str = "NeuroShift"
    mock_fps: float = 20.0
    mock_write_video: bool = True
    # Live web stream (lower = faster, less lag)
    live_frame_width: int = 640
    live_frame_height: int = 480
    live_preview_max_width: int = 480
    live_jpeg_quality: int = 45
    live_preview_every_n: int = 2
    live_target_fps: float = 12.0
    # Live Phase-1: YOLO object targeting on by default; slots if none found
    live_use_yolo: bool = True
    live_yaw_side_threshold: float = 0.28
    live_auto_calibrate_frames: int = 10


DEFAULT = Config()


def config_to_dict(cfg: Config) -> dict[str, Any]:
    return asdict(cfg)


def apply_overrides(cfg: Config, overrides: dict[str, Any]) -> Config:
    valid = {f.name for f in fields(Config)}
    data = asdict(cfg)
    for key, value in overrides.items():
        if key in valid:
            data[key] = value
    return Config(**data)


def load_config(path: Path | None = None) -> Config:
    """Load YAML/JSON config if present; otherwise defaults."""
    if path is None:
        root = Path(__file__).resolve().parents[2]
        for candidate in (
            root / "config" / "default.yaml",
            root / "config" / "default.yml",
            root / "config" / "default.json",
        ):
            if candidate.exists():
                path = candidate
                break
    if path is None or not Path(path).exists():
        return DEFAULT

    path = Path(path)
    text = path.read_text(encoding="utf-8")
    data: dict[str, Any]
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(text) or {}
        except Exception:
            # Minimal YAML subset: key: value lines only
            data = {}
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if v.lower() in {"true", "false"}:
                    data[k] = v.lower() == "true"
                else:
                    try:
                        data[k] = int(v)
                    except ValueError:
                        try:
                            data[k] = float(v)
                        except ValueError:
                            data[k] = v
    else:
        import json

        data = json.loads(text)
    if not isinstance(data, dict):
        return DEFAULT
    return apply_overrides(DEFAULT, data)
