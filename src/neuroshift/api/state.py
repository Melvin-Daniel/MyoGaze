"""In-memory product runtime for the Control App."""

from __future__ import annotations

import asyncio
import base64
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

import cv2
import numpy as np

from ..appliances import ApplianceHub
from ..camera import Camera
from ..config import Config, apply_overrides, load_config
from ..detector import ObjectDetector
from ..engine import IntentionEngine
from ..evaluation import CuedTrialRunner
from ..gaze import FaceGazeEstimator
from ..logger import DecisionLogger
from ..metrics import SessionMetrics
from ..mock_scene import DEFAULT_SCENARIO, iter_scenario, render_mock_frame
from ..mqtt_bridge import DecisionPublisher, MqttConfig
from ..aliases import relay_id_for
from ..trials import TrialLog
from ..selector import drop_boxes_on_face, drop_lamps_on_people, keep_lamp_detections
from ..types import GazeEstimate
from .live_overlay import draw_live_frame
from .schemas import (
    DecisionOut,
    DeviceOut,
    SessionOut,
    SettingsIn,
    SettingsOut,
    StatusOut,
)


class AppRuntime:
    """Shared state between REST + WebSocket clients."""

    def __init__(self) -> None:
        self.cfg: Config = load_config()
        self.hub = ApplianceHub()
        self.metrics = SessionMetrics()
        self.trials = TrialLog()
        self.cued = CuedTrialRunner()
        self.last_decision: DecisionOut | None = None
        self.decisions: list[DecisionOut] = []
        self.demo_running = False
        self._demo_task: asyncio.Task | None = None
        self._subscribers: set[Callable[[dict[str, Any]], Awaitable[None]]] = set()
        self.mode = "live"  # live | mock
        self.detect_mode = "objects"  # objects | slots
        self.camera_ok: bool | None = None
        self.camera_message = "Camera not probed yet"
        self._camera_source = "local"  # local = laptop OpenCV, remote = phone/browser
        self._remote_frame: np.ndarray | None = None
        self._remote_frame_ts = 0.0
        self._emg_pulse_until = 0.0
        self._engine: IntentionEngine | None = None
        self._gaze_est: FaceGazeEstimator | None = None
        self._shared_detector: ObjectDetector | None = None
        self._shared_gaze: FaceGazeEstimator | None = None
        self._warmup_lock = threading.Lock()
        self._warmup_done = threading.Event()
        self._warmup_started = False
        self._recalibrate = False
        self._look_wizard: dict[str, Any] | None = None
        self._gaze_show: tuple[float, float] | None = None
        self.publisher = self._make_publisher()
        self._ensure_seed_devices()

    def _make_publisher(self) -> DecisionPublisher:
        return DecisionPublisher(
            MqttConfig(
                enabled=self.cfg.mqtt_enabled,
                host=self.cfg.mqtt_host,
                port=self.cfg.mqtt_port,
                hub_serial_port=getattr(self.cfg, "hub_serial_port", ""),
                hub_serial_baud=getattr(self.cfg, "hub_serial_baud", 115200),
            )
        )

    def _hot_patch_cfg(self, **overrides: Any) -> None:
        """Mutate runtime cfg and the live engine cfg in place (same object fusion uses)."""
        for key, value in overrides.items():
            if hasattr(self.cfg, key):
                setattr(self.cfg, key, value)
            if self._engine is not None and hasattr(self._engine.cfg, key):
                setattr(self._engine.cfg, key, value)

    def _ensure_seed_devices(self) -> None:
        for device_id, label in (("lamp", "Lamp"), ("fan", "Fan"), ("plug", "Plug")):
            self.hub.ensure(device_id, label)

    def subscribe(self, cb: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        self._subscribers.add(cb)

    def unsubscribe(self, cb: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        self._subscribers.discard(cb)

    async def broadcast(self, event: dict[str, Any]) -> None:
        dead: list[Callable] = []
        for cb in list(self._subscribers):
            try:
                await cb(event)
            except Exception:
                dead.append(cb)
        for cb in dead:
            self._subscribers.discard(cb)

    def pulse_confirm(self) -> dict[str, Any]:
        """Web Confirm button → short EMG pulse (MyoWare stand-in)."""
        self._emg_pulse_until = time.time() + (self.cfg.emg_pulse_ms / 1000.0)
        self.trials.log_confirm(
            dwell_required=self.cfg.dwell_required,
            detect_mode=self.detect_mode,
        )
        return {"ok": True, "message": "Confirm pulse sent"}

    def current_emg(self) -> float:
        return 1.0 if time.time() < self._emg_pulse_until else 0.0

    def warmup_models(self) -> None:
        """Load YOLO + gaze once at serve start so Start camera is not a cold load."""
        with self._warmup_lock:
            if self._warmup_done.is_set():
                return
            self._warmup_started = True
            t0 = time.perf_counter()
            try:
                detector = ObjectDetector(
                    model_name=self.cfg.yolo_model,
                    conf=self.cfg.yolo_conf,
                    every_n_frames=self.cfg.yolo_every_n_frames,
                    imgsz=self.cfg.yolo_imgsz,
                    iou_match=0.22,
                )
                detector.warmup(self.cfg.yolo_imgsz)
                self._shared_detector = detector
                try:
                    self._shared_gaze = FaceGazeEstimator(
                        smooth_alpha=0.40,
                        eye_weight=self.cfg.gaze_eye_weight,
                    )
                except Exception as exc:  # noqa: BLE001
                    print(f"[live] gaze warmup skipped ({exc})")
                    self._shared_gaze = None
                print(f"[live] models ready in {time.perf_counter() - t0:.1f}s", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[live] model warmup failed ({exc})", flush=True)
            finally:
                self._warmup_done.set()

    def _live_detector(self, *, remote: bool) -> ObjectDetector | None:
        if self._warmup_started and not self._warmup_done.is_set():
            self._warmup_done.wait(timeout=90)
        detector = self._shared_detector
        if detector is None and self.cfg.live_use_yolo:
            detector = ObjectDetector(
                model_name=self.cfg.yolo_model,
                conf=self.cfg.yolo_conf,
                every_n_frames=self.cfg.yolo_every_n_frames,
                imgsz=self.cfg.yolo_imgsz,
                iou_match=0.22,
            )
            self._shared_detector = detector
        if detector is None:
            return None
        detector.every_n_frames = (
            max(5, int(self.cfg.yolo_every_n_frames)) if remote else max(3, int(self.cfg.yolo_every_n_frames))
        )
        detector.imgsz = 416
        detector.match_fans = False
        detector.reset_tracking()
        return detector

    def probe_camera(self) -> dict[str, Any]:
        cam = Camera(self.cfg)
        try:
            cam.open()
            _ = cam.read()
            self.camera_ok = True
            self.camera_message = f"Camera {self.cfg.camera_index} ready"
            return {"ok": True, "message": self.camera_message, "index": self.cfg.camera_index}
        except Exception as exc:  # noqa: BLE001
            self.camera_ok = False
            self.camera_message = str(exc)
            return {"ok": False, "message": self.camera_message, "index": self.cfg.camera_index}
        finally:
            cam.release()

    def push_remote_frame(self, jpeg_b64: str) -> bool:
        """Decode a JPEG sent by the phone/browser and keep the latest frame."""
        if not jpeg_b64 or len(jpeg_b64) > 800_000:
            return False
        try:
            raw = base64.b64decode(jpeg_b64, validate=False)
        except Exception:
            return False
        if not raw:
            return False
        arr = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None or frame.size == 0:
            return False
        self._remote_frame = frame
        self._remote_frame_ts = time.time()
        return True

    def _take_remote_frame(self) -> np.ndarray:
        frame = self._remote_frame
        ts = self._remote_frame_ts
        if frame is None or frame.size == 0:
            raise RuntimeError("No phone camera frame yet")
        if time.time() - ts > 2.5:
            raise RuntimeError("Phone camera stalled")
        return frame.copy()

    def settings_out(self) -> SettingsOut:
        return SettingsOut(
            product_name=self.cfg.product_name,
            dwell_seconds=self.cfg.dwell_seconds,
            dwell_required=self.cfg.dwell_required,
            dwell_actuates=self.cfg.dwell_actuates,
            yaw_side_threshold=self.cfg.yaw_side_threshold,
            emg_confirm_threshold=self.cfg.emg_confirm_threshold,
            act_cooldown_seconds=self.cfg.act_cooldown_seconds,
            mqtt_enabled=self.cfg.mqtt_enabled,
            mqtt_host=self.cfg.mqtt_host,
            emg_mode=self.cfg.emg_mode,
            emg_serial_port=self.cfg.emg_serial_port,
            pipeline_mode=self.mode,
            camera_index=self.cfg.camera_index,
            camera_ok=self.camera_ok,
        )

    def update_settings(self, body: SettingsIn) -> SettingsOut:
        overrides = {k: v for k, v in body.model_dump().items() if v is not None}
        if "pipeline_mode" in overrides:
            mode = overrides.pop("pipeline_mode")
            if mode in {"live", "mock"}:
                self.mode = mode
        # Prefer in-place patch so a running IntentionEngine / fusion see changes
        mqtt_keys = {"mqtt_enabled", "mqtt_host", "mqtt_port"}
        mqtt_changed = any(key in overrides for key in mqtt_keys)
        self._hot_patch_cfg(**overrides)
        if mqtt_changed:
            if self.publisher is not None:
                self.publisher.close()
            self.publisher = self._make_publisher()
        return self.settings_out()

    def devices_out(self) -> list[DeviceOut]:
        self._ensure_seed_devices()
        seed = {"lamp", "fan", "plug"}
        return [
            DeviceOut(
                id=d.device_id,
                label=d.label,
                is_on=d.is_on,
                toggle_count=d.toggle_count,
            )
            for d in self.hub.snapshot()
            if d.device_id in seed
        ]

    def session_out(self) -> SessionOut:
        data = self.metrics.to_dict()
        return SessionOut(
            acts=data.get("acts", 0),
            abstains=data.get("abstains", 0),
            actuations=data.get("actuations", 0),
            emg_without_gaze=data.get("emg_without_gaze", 0),
            gaze_without_emg=data.get("gaze_without_emg", 0),
            far_proxy=data.get("far_proxy", 0.0),
            act_rate=data.get("act_rate", 0.0),
            abstain_rate=data.get("abstain_rate", 0.0),
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
            note=data.get("note"),
        )

    def status(self, version: str) -> StatusOut:
        from ..cli import _lan_ips

        lan = _lan_ips()
        base = f"http://{lan[0]}:8000" if lan else None
        apk = Path(__file__).resolve().parents[3] / "dist-mobile" / "MyoGaze.apk"
        return StatusOut(
            version=version,
            mode=self.mode,
            principle="Look at a device for two seconds to toggle it. Unsure → Abstain.",
            devices=self.devices_out(),
            last_decision=self.last_decision,
            session=self.session_out(),
            demo_running=self.demo_running,
            camera_ok=self.camera_ok,
            camera_message=self.camera_message,
            detect_mode=self.detect_mode,
            dwell_required=self.cfg.dwell_required,
            dwell_actuates=self.cfg.dwell_actuates,
            iphone_setup_url=f"{base}/iphone" if base else None,
            android_apk_url=f"{base}/app.apk" if base and apk.exists() else None,
        )

    def set_dwell_required(self, required: bool) -> dict[str, Any]:
        self._hot_patch_cfg(dwell_required=required)
        if self._engine is not None:
            self._engine.reset_gaze_state()
        mode = "dwell-gated" if required else "instant-gaze"
        return {
            "ok": True,
            "dwell_required": self.cfg.dwell_required,
            "message": f"Selection mode → {mode}",
        }

    def mark_trial_block(self, label: str) -> dict[str, Any]:
        note = (label or "").strip() or "pilot_block"
        self.trials.log_marker(
            note=note,
            dwell_required=self.cfg.dwell_required,
            detect_mode=self.detect_mode,
        )
        return {
            "ok": True,
            "message": f"Marked trial block: {note}",
            "summary": self.trials.summary(),
        }

    def build_session_report(self) -> Path:
        """Write HTML report from current TrialLog + session metrics."""
        from ..report import build_trials_report

        root = Path(__file__).resolve().parents[3]
        logs = root / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        return build_trials_report(
            trials=self.trials,
            session=self.metrics.to_dict(),
            cued=self.cued.summary(),
            cued_rows=self.cued.to_dicts(),
            out_path=logs / "neuroshift_session_report.html",
            title="MyoGaze Phase-I Session Report",
            dwell_required=self.cfg.dwell_required,
            detect_mode=self.detect_mode,
        )

    def trials_out(self) -> dict[str, Any]:
        return {"summary": self.trials.summary(), "trials": self.trials.to_dicts()}

    def _record_tick_result(self, result, decision: DecisionOut) -> None:
        if result.changed:
            self.trials.log_decision(
                action=decision.action,
                device_id=decision.selected_device,
                label=decision.selected_label,
                reason=decision.reason,
                dwell_progress=result.dwell_progress,
                dwell_required=self.cfg.dwell_required,
                detect_mode=self.detect_mode,
                yaw=decision.yaw,
                emg=decision.emg,
            )
        if result.actuation is not None:
            self.trials.log_actuation(
                device_id=result.actuation.device_id,
                label=result.actuation.label,
                command=result.actuation.command,
                dwell_required=self.cfg.dwell_required,
                detect_mode=self.detect_mode,
            )
            # Score against the cue when a cued trial is open.
            # YOLO stand-ins (bottle/phone) map onto lamp/fan/plug.
            scored_id = relay_id_for(result.actuation.device_id, result.actuation.label)
            self.cued.on_actuation(
                device_id=scored_id,
                label=result.actuation.label,
                now=time.monotonic(),
            )
        else:
            self.cued.check_timeout(now=time.monotonic())

    def _targets_payload(
        self,
        result,
        detections: list,
        frame_w: int = 0,
        frame_h: int = 0,
    ) -> list[dict[str, Any]]:
        """Targets for the live boxes. Boxes are 0–1 of the camera frame."""
        out: list[dict[str, Any]] = []
        seen: set[str] = set()

        def box_of(xyxy) -> list[float] | None:
            if not xyxy or frame_w <= 0 or frame_h <= 0:
                return None
            x0, y0, x1, y1 = xyxy
            return [
                round(max(0.0, min(1.0, x0 / frame_w)), 4),
                round(max(0.0, min(1.0, y0 / frame_h)), 4),
                round(max(0.0, min(1.0, x1 / frame_w)), 4),
                round(max(0.0, min(1.0, y1 / frame_h)), 4),
            ]

        def overlay_label(raw: str | None) -> str | None:
            text = (raw or "").strip()
            if not text or text.lower() == "cup":
                return None
            return text

        for det in detections:
            label = overlay_label(det.appliance or det.label)
            if label is None:
                continue
            relay = relay_id_for(det.obj_id, label)
            out.append(
                {
                    "id": det.obj_id,
                    "label": label,
                    "conf": round(det.conf, 2),
                    "selected": bool(result.selected and result.selected.target_id == det.obj_id),
                    "candidate": bool(result.candidate and result.candidate.target_id == det.obj_id),
                    "relay": relay,
                    "ambiguous": bool(
                        result.candidate
                        and result.candidate.ambiguous
                        and result.candidate.target_id == det.obj_id
                    ),
                    "box": box_of(det.xyxy),
                }
            )
            seen.add(det.obj_id)
        for t in (result.selected, result.candidate):
            if t is None or t.target_id in seen:
                continue
            label = overlay_label(t.label)
            if label is None:
                continue
            relay = relay_id_for(t.target_id, label)
            out.append(
                {
                    "id": t.target_id,
                    "label": label,
                    "conf": round(t.score, 2),
                    "selected": bool(result.selected and result.selected.target_id == t.target_id),
                    "candidate": bool(result.candidate and result.candidate.target_id == t.target_id),
                    "relay": relay,
                    "ambiguous": bool(t.ambiguous),
                    "box": box_of(getattr(t, "xyxy", None)),
                }
            )
            seen.add(t.target_id)
        return out

    # -- cued-trial protocol ----------------------------------------------

    def start_cued_trial(self, device_id: str | None = None) -> dict[str, Any]:
        trial = self.cued.start(
            device_id=device_id,
            dwell_required=self.cfg.dwell_required,
            detect_mode=self.detect_mode,
            now=time.monotonic(),
        )
        return {
            "ok": True,
            "message": f"Look at the {trial.cued_label}, then confirm",
            "active": asdict(trial),
            "summary": self.cued.summary(),
        }

    def skip_cued_trial(self) -> dict[str, Any]:
        trial = self.cued.skip(now=time.monotonic())
        return {
            "ok": trial is not None,
            "message": "Trial skipped" if trial else "No trial running",
            "summary": self.cued.summary(),
        }

    def reset_cued_trials(self) -> dict[str, Any]:
        self.cued.reset()
        return {"ok": True, "message": "Cued trials cleared", "summary": self.cued.summary()}

    def cued_out(self) -> dict[str, Any]:
        return {
            "summary": self.cued.summary(),
            "active": asdict(self.cued.active) if self.cued.active else None,
            "last_resolved": asdict(self.cued.last_resolved) if self.cued.last_resolved else None,
            "trials": self.cued.to_dicts(),
        }

    def calibrate_gaze(self) -> dict[str, Any]:
        """Teach center, then the look for each visible Fan / Lamp."""
        if not self.demo_running or self._gaze_est is None:
            return {"ok": False, "message": "Start a live camera session first"}
        self._recalibrate = False
        self._look_wizard = {
            "phase": "center",
            "t0": time.time(),
            "samples": [],
            "queue": [],
        }
        if self._gaze_est is not None:
            self._gaze_est.look_templates = {}
        if self._engine is not None:
            self._engine.reset_gaze_state()
        return {"ok": True, "message": "Look at the camera — not this screen"}

    def _step_look_wizard(
        self,
        g: GazeEstimate,
        detections: list[Any],
        gaze_est: FaceGazeEstimator,
        now: float,
    ) -> str | None:
        """Drive Recalibrate. Returns a status line while the wizard is open."""
        wizard = self._look_wizard
        if wizard is None:
            return None
        if now - float(wizard["t0"]) >= 12.0:
            self._look_wizard = None
            return "Calibration timed out — tap Recalibrate to try again"
        if not g.face_found:
            return "Face the camera to continue calibration"

        def _mean(samples: list[tuple[float, float]]) -> tuple[float, float]:
            ys = [item[0] for item in samples]
            ps = [item[1] for item in samples]
            return (sum(ys) / len(ys), sum(ps) / len(ps))

        def _visible_keys() -> list[str]:
            seen: list[str] = []
            for det in detections:
                key = (getattr(det, "appliance", None) or getattr(det, "label", "") or "").strip().lower()
                if key in {"fan", "lamp"} and key not in seen:
                    seen.append(key)
            return seen

        phase = str(wizard["phase"])
        if phase == "center":
            if g.has_iris:
                wizard["samples"].append((g.eye_yaw, g.eye_pitch))
            elif g.face_found:
                wizard["samples"].append((g.yaw, g.pitch))
            wizard["samples"] = wizard["samples"][-40:]
            if now - float(wizard["t0"]) >= 1.0 and wizard["samples"]:
                gaze_est.calibrate_center()
                wizard["queue"] = _visible_keys()
                wizard["samples"] = []
                if wizard["queue"]:
                    wizard["phase"] = wizard["queue"][0]
                    wizard["t0"] = now
                else:
                    self._look_wizard = None
                    return "Center saved. Hold the fan or lamp in view, then Recalibrate again."
            return "Look at the camera — not this screen"

        if g.has_iris:
            wizard["samples"].append((g.eye_yaw, g.eye_pitch))
        else:
            wizard["samples"].append((g.yaw, g.pitch))
        wizard["samples"] = wizard["samples"][-40:]
        ready = now - float(wizard["t0"]) >= 2.0 and len(wizard["samples"]) >= 4
        if ready:
            yaw, pitch = _mean(wizard["samples"])
            gaze_est.set_look_template(phase, yaw, pitch)
            wizard["queue"] = [key for key in wizard["queue"] if key != phase]
            wizard["samples"] = []
            if wizard["queue"]:
                wizard["phase"] = wizard["queue"][0]
                wizard["t0"] = now
            else:
                self._look_wizard = None
                return "Look templates saved. Look at the real object to lock."
        if phase == "fan":
            return "Look at the real fan — not this screen"
        if phase == "lamp":
            return "Look at the real lamp — not this screen"
        return f"Look at the real {phase} — not this screen"

    def set_detect_mode(self, mode: str) -> dict[str, Any]:
        if mode not in {"objects", "slots"}:
            return {"ok": False, "detect_mode": self.detect_mode, "message": "Use objects or slots"}
        self.detect_mode = mode
        return {"ok": True, "detect_mode": self.detect_mode, "message": f"Detect mode → {mode}"}

    def reset_session(self) -> None:
        self.hub = ApplianceHub()
        self._ensure_seed_devices()
        self.metrics = SessionMetrics()
        self.trials.reset()
        self.cued.reset()
        self.last_decision = None
        self.decisions = []
        self._emg_pulse_until = 0.0

    def manual_toggle(self, device_id: str) -> DeviceOut | None:
        if device_id not in self.hub.devices:
            return None
        event = self.hub.toggle(device_id)
        relay = relay_id_for(device_id, event.label)
        mqtt_event = event
        if relay != device_id:
            names = {"lamp": "Lamp", "fan": "Fan", "plug": "Plug"}
            mqtt_event = self.hub.toggle(relay, names.get(relay, relay))
        if self.publisher is not None:
            self.publisher.publish_actuate(
                {
                    "device_id": mqtt_event.device_id if relay == device_id else relay,
                    "label": mqtt_event.label,
                    "command": mqtt_event.command,
                    "state": mqtt_event.new_state,
                }
            )
        state = self.hub.devices[device_id]
        return DeviceOut(
            id=state.device_id,
            label=state.label,
            is_on=state.is_on,
            toggle_count=state.toggle_count,
        )

    async def start_demo(
        self,
        prefer: str | None = None,
        camera: str | None = None,
    ) -> dict[str, Any]:
        if self.demo_running:
            # A stale loop (hung webcam, leftover from an earlier Start) made
            # Live look dead. Pressing Live must reopen the camera.
            await self.stop_demo()

        mode = prefer or self.mode
        source = (camera or "local").strip().lower()
        if source not in {"local", "remote"}:
            source = "local"
        if mode == "live":
            # Do not open+release the webcam here. On Windows DirectShow that
            # race is why the first Start often shows no picture until Stop/Start.
            self.mode = "live"
            self._camera_source = source
        else:
            self.mode = "mock"
            self._camera_source = "local"

        self.reset_session()
        self.demo_running = True
        if mode == "live":
            self._demo_task = asyncio.create_task(self._run_live())
            cam_note = "phone camera" if self._camera_source == "remote" else "laptop camera"
            message = f"Live session started — using {cam_note}. Look at a target, then Confirm"
        else:
            self._demo_task = asyncio.create_task(self._run_mock())
            message = "Mock session started"
        await self.broadcast(
            {
                "type": "demo_started",
                "mode": self.mode,
                "camera": self._camera_source,
            }
        )
        return {
            "started": True,
            "message": message,
            "mode": self.mode,
            "camera": self._camera_source,
        }

    async def stop_demo(self) -> dict[str, Any]:
        self.demo_running = False
        if self._demo_task and not self._demo_task.done():
            self._demo_task.cancel()
            try:
                await asyncio.wait_for(self._demo_task, timeout=4.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception:
                pass
        self.demo_running = False
        await self.broadcast({"type": "demo_stopped"})
        return {"stopped": True}

    def _encode_preview(self, frame, max_w: int | None = None) -> str | None:
        max_w = max(160, int(max_w if max_w is not None else self.cfg.live_preview_max_width))
        h, w = frame.shape[:2]
        if w > max_w:
            scale = max_w / w
            frame = cv2.resize(frame, (max_w, int(h * scale)), interpolation=cv2.INTER_AREA)
        q = int(self.cfg.live_jpeg_quality)
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), q])
        if not ok:
            return None
        return base64.b64encode(buf.tobytes()).decode("ascii")

    async def _emit_tick(
        self,
        *,
        note: str,
        decision: DecisionOut,
        dwell: float,
        preview: str | None,
        actuation,
        t: float | None = None,
        targets: list[dict[str, Any]] | None = None,
        gaze_xy: list[float] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "type": "tick",
            "t": t,
            "note": note,
            "mode": self.mode,
            "detect_mode": self.detect_mode,
            "dwell_required": self.cfg.dwell_required,
            "decision": decision.model_dump(),
            "dwell": round(dwell, 2),
            "devices": [d.model_dump() for d in self.devices_out()],
            "targets": targets or [],
            "gaze_xy": gaze_xy,
            "session": self.session_out().model_dump(),
            "actuation": (
                {
                    "device_id": actuation.device_id,
                    "label": actuation.label,
                    "command": actuation.command,
                }
                if actuation
                else None
            ),
            # Summary + active cue only; the full trial list is fetched on demand
            # so the tick stays small at frame rate.
            "cued": {
                "summary": self.cued.summary(),
                "active": asdict(self.cued.active) if self.cued.active else None,
                "last_resolved": asdict(self.cued.last_resolved) if self.cued.last_resolved else None,
            },
        }
        if preview is not None:
            payload["preview_jpeg_b64"] = preview
        await self.broadcast(payload)

    async def _run_live(self) -> None:
        root = Path(__file__).resolve().parents[3]
        logs = root / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        decisions_path = logs / "decisions_live_latest.jsonl"
        if decisions_path.exists():
            decisions_path.unlink()

        logger = DecisionLogger(decisions_path)
        publisher = self.publisher
        # Wider center zone so facing the camera = Fan, not Plug/Lamp
        live_cfg = apply_overrides(
            self.cfg,
            {
                "frame_width": self.cfg.live_frame_width,
                "frame_height": self.cfg.live_frame_height,
                "yaw_side_threshold": self.cfg.live_yaw_side_threshold,
                "gaze_smooth_alpha": min(max(self.cfg.gaze_smooth_alpha, 0.14), 0.22),
                "dwell_seconds": float(self.cfg.dwell_seconds),
                "dwell_actuates": self.cfg.dwell_actuates,
            },
        )
        engine = IntentionEngine(
            cfg=live_cfg,
            logger=logger,
            metrics=self.metrics,
            publisher=publisher,
            hub=self.hub,
        )
        self._engine = engine
        cam = Camera(live_cfg)
        remote = self._camera_source == "remote"
        cam_label = "phone camera" if remote else "laptop camera"

        async def _wait_models() -> None:
            if self._warmup_started and not self._warmup_done.is_set():
                await asyncio.to_thread(self._warmup_done.wait, 90)

        try:
            if remote:
                await _wait_models()
            else:
                await asyncio.gather(_wait_models(), asyncio.to_thread(cam.open))
        except Exception as exc:  # noqa: BLE001
            if remote:
                raise
            self.camera_ok = False
            self.camera_message = str(exc)
            self.demo_running = False
            self._engine = None
            await self.broadcast(
                {
                    "type": "error",
                    "message": f"Camera failed to start: {exc}. Try Start again.",
                }
            )
            await self.broadcast({"type": "demo_stopped"})
            return

        prefer_detections = self.detect_mode == "objects" and self.cfg.live_use_yolo
        detector = self._live_detector(remote=remote) if prefer_detections else None
        if detector is not None and not detector.available:
            print("[live] YOLO missing — PC-fan shape detector still active")

        gaze_est: FaceGazeEstimator | None = None
        if not remote:
            gaze_est = self._shared_gaze
            if gaze_est is None:
                gaze_est = FaceGazeEstimator(
                    smooth_alpha=live_cfg.gaze_smooth_alpha,
                    eye_weight=live_cfg.gaze_eye_weight,
                )
                self._shared_gaze = gaze_est
            else:
                gaze_est.smooth_alpha = live_cfg.gaze_smooth_alpha
                gaze_est.eye_weight = live_cfg.gaze_eye_weight
                gaze_est.reset_session()
            self._gaze_est = gaze_est
        else:
            self._gaze_est = None
        self._recalibrate = False
        self._look_wizard = None

        sticky_note = (
            (
                "Point the back camera at the lamp or the black PC fan, hold, then Confirm"
                if remote
                else f"Hold a lamp, the black PC fan, or a bottle in view of the {cam_label} — look at it, then Confirm"
            )
            if detector is not None
            else "Look LEFT=Lamp · STRAIGHT=Fan · RIGHT=Plug, then Confirm"
        )
        last_preview: str | None = None
        # Do not treat the opening glance as "center". Recalibrate still does that on purpose.
        calibrate_left = 0
        calib_samples: list[float] = []
        target_dt = 1.0 / (8.0 if remote else max(12.0, float(self.cfg.live_target_fps)))
        preview_every = 3 if remote else max(1, int(self.cfg.live_preview_every_n))
        preview_w = 320 if remote else None
        detect_task: asyncio.Task | None = None
        cached_dets: list = []

        try:
            if remote:
                deadline = time.time() + 12.0
                while time.time() < deadline:
                    if (
                        self._remote_frame is not None
                        and time.time() - self._remote_frame_ts < 2.0
                    ):
                        break
                    await asyncio.sleep(0.05)
                else:
                    self.camera_ok = False
                    self.camera_message = "No phone camera frames yet"
                    self.demo_running = False
                    await self.broadcast(
                        {
                            "type": "error",
                            "message": (
                                "Phone camera hasn't sent a frame yet. Allow camera access. "
                                "On iPhone, open the HTTPS address (port 8443) shown on the laptop."
                            ),
                        }
                    )
                    await self.broadcast({"type": "demo_stopped"})
                    return

            self.camera_ok = True
            self.camera_message = (
                "Phone camera streaming"
                if remote
                else f"Camera {cam.opened_index} ({cam.opened_backend}) streaming"
            )
            await self.broadcast(
                {"type": "status", "payload": self.status("0.5.2").model_dump()}
            )

            frame_i = 0
            miss_reads = 0
            miss_limit = 40 if remote else 12
            while self.demo_running:
                loop_t0 = time.perf_counter()
                # Allow mid-session mode switches
                use_objects = self.detect_mode == "objects" and detector is not None

                try:
                    if remote:
                        frame = self._take_remote_frame()
                    else:
                        frame = await asyncio.wait_for(asyncio.to_thread(cam.read), timeout=2.5)
                    miss_reads = 0
                except Exception:  # noqa: BLE001
                    miss_reads += 1
                    if miss_reads >= miss_limit:
                        raise RuntimeError(
                            "Phone camera stopped sending frames"
                            if remote
                            else "Camera stopped delivering frames"
                        )
                    await asyncio.sleep(0.05)
                    continue
                if not remote and self.cfg.mirror_preview:
                    frame = cv2.flip(frame, 1)
                max_w = int(self.cfg.live_frame_width) if not remote else min(int(frame.shape[1]), 640)
                if max_w > 0 and frame.shape[1] > max_w:
                    scale = max_w / float(frame.shape[1])
                    frame = cv2.resize(
                        frame,
                        (max_w, max(1, int(round(frame.shape[0] * scale)))),
                        interpolation=cv2.INTER_AREA,
                    )
                h, w = frame.shape[:2]

                detections = cached_dets
                if use_objects and detector is not None:
                    if detect_task is not None and detect_task.done():
                        try:
                            cached_dets = detect_task.result() or []
                        except Exception:
                            cached_dets = []
                        detect_task = None
                        detections = cached_dets
                    if detect_task is None:
                        detect_task = asyncio.create_task(
                            asyncio.to_thread(detector.detect, frame.copy())
                        )
                else:
                    detections = []
                    cached_dets = []

                if remote:
                    if detections:
                        cx, cy = w / 2.0, h / 2.0
                        g = GazeEstimate(
                            face_found=True,
                            nose_xy=(cx, cy),
                            yaw=0.0,
                            pitch=0.0,
                            confidence=0.9,
                            iris_xy=(cx, cy),
                        )
                    else:
                        g = GazeEstimate(
                            face_found=False,
                            nose_xy=None,
                            yaw=0.0,
                            pitch=0.0,
                            confidence=0.0,
                        )
                else:
                    assert gaze_est is not None
                    g = await asyncio.to_thread(gaze_est.estimate, frame)

                    if self._recalibrate and g.face_found and self._look_wizard is None:
                        gaze_est.calibrate_center()
                        self._recalibrate = False
                        sticky_note = "Recalibrated — look straight is now center"
                        engine.reset_gaze_state()

                    if calibrate_left > 0 and g.face_found:
                        calib_samples.append(g.raw_yaw)
                        calibrate_left -= 1
                        if calibrate_left == 0 and calib_samples:
                            gaze_est.yaw_offset = float(sum(calib_samples) / len(calib_samples))
                            gaze_est._yaw_s = 0.0
                            sticky_note = "Calibrated — look at an object (or use slots)"

                if use_objects:
                    people = getattr(detector, "last_people", None) if detector is not None else None
                    detections = drop_lamps_on_people(detections, people, w, h)
                    if g.face_oval:
                        detections = drop_boxes_on_face(detections, g.face_oval)
                    detections = keep_lamp_detections(detections)

                if not remote and gaze_est is not None:
                    wizard_note = self._step_look_wizard(g, detections, gaze_est, time.time())
                    if wizard_note:
                        sticky_note = wizard_note
                        engine.reset_gaze_state()

                emg = self.current_emg()
                use_slots = self.detect_mode == "slots" and not remote
                lock_dets = [] if self._look_wizard is not None else detections
                result = engine.tick(
                    g,
                    lock_dets,
                    prefer_detections=use_objects,
                    frame_w=w,
                    frame_h=h,
                    emg_score_override=emg,
                    allow_slots=use_slots and self._look_wizard is None,
                    look_templates=getattr(self._gaze_est, "look_templates", None),
                )

                decision = DecisionOut(
                    ts=datetime.now(timezone.utc).isoformat(),
                    action=result.decision.action,
                    selected_device=result.decision.selected_device,
                    selected_label=result.selected.label if result.selected else None,
                    reason=result.decision.reason,
                    yaw=round(g.yaw, 3),
                    emg=round(result.emg_score, 3),
                )
                if result.changed:
                    self.last_decision = decision
                    self.decisions.append(decision)
                self._record_tick_result(result, decision)

                targets = self._targets_payload(result, detections, w, h)

                send_preview = frame_i % preview_every == 0
                preview = last_preview
                if send_preview:
                    hub_states = {d.device_id: d.is_on for d in self.hub.snapshot()}
                    det_draw = None
                    if use_objects and detections:
                        det_draw = [
                            (d.xyxy, d.appliance or d.label, d.obj_id, d.conf)
                            for d in detections
                        ]
                    annotated = draw_live_frame(
                        frame,
                        yaw=g.yaw,
                        pitch=g.pitch,
                        nose_xy=g.iris_xy or g.nose_xy,
                        candidate=result.candidate,
                        selected=result.selected,
                        dwell_progress=result.dwell_progress,
                        emg_score=result.emg_score,
                        action=result.decision.action,
                        hub_states=hub_states,
                        prefer_slots=use_slots,
                        detections_xyxy=det_draw,
                    )
                    preview = self._encode_preview(annotated, max_w=preview_w)
                    last_preview = preview

                n_det = len(detections)
                if self._look_wizard is not None:
                    pass
                elif calibrate_left > 0:
                    sticky_note = "Hold still — calibrating center…"
                elif result.selected and engine.cfg.dwell_actuates:
                    sticky_note = f"Toggling {result.selected.label}"
                elif result.selected:
                    sticky_note = f"Ready: {result.selected.label} — press Confirm"
                elif result.candidate and engine.cfg.dwell_required:
                    hold = max(0.1, float(engine.cfg.dwell_seconds))
                    sticky_note = f"Looking at {result.candidate.label} — hold {hold:.0f}s"
                elif result.candidate:
                    sticky_note = f"Looking at {result.candidate.label} — press Confirm"
                elif not g.face_found:
                    sticky_note = (
                        "Point the back camera at the lamp or the black PC fan"
                        if remote
                        else f"Face not found — face the {cam_label}"
                    )
                elif use_objects:
                    sticky_note = (
                        f"Objects seen: {n_det} — look toward the lamp or the black PC fan"
                        if n_det
                        else f"No objects yet — face the black PC fan or a lamp at the {cam_label}"
                    )
                else:
                    sticky_note = "Slots mode — look LEFT / STRAIGHT / RIGHT"

                gaze_xy = None
                look = result.candidate or result.selected
                if look is not None and look.xyxy and w > 0 and h > 0:
                    lx0, ly0, lx1, ly1 = look.xyxy
                    gaze_xy = [
                        round(max(0.0, min(1.0, ((lx0 + lx1) / 2.0) / w)), 4),
                        round(max(0.0, min(1.0, ((ly0 + ly1) / 2.0) / h)), 4),
                    ]
                elif g.aim_xy is not None and w > 0 and h > 0:
                    gaze_xy = [
                        round(max(0.0, min(1.0, g.aim_xy[0] / w)), 4),
                        round(max(0.0, min(1.0, g.aim_xy[1] / h)), 4),
                    ]
                elif g.eye_xy is not None and w > 0 and h > 0:
                    gaze_xy = [
                        round(max(0.0, min(1.0, g.eye_xy[0] / w)), 4),
                        round(max(0.0, min(1.0, g.eye_xy[1] / h)), 4),
                    ]
                self._gaze_show = (gaze_xy[0], gaze_xy[1]) if gaze_xy else None
                await self._emit_tick(
                    note=sticky_note,
                    decision=decision,
                    dwell=result.dwell_progress,
                    preview=preview if send_preview else None,
                    actuation=result.actuation,
                    t=frame_i / max(1.0, self.cfg.live_target_fps),
                    targets=targets,
                    gaze_xy=gaze_xy,
                )
                frame_i += 1
                elapsed = time.perf_counter() - loop_t0
                await asyncio.sleep(max(0.0, target_dt - elapsed))

            session_path = self.metrics.save(logs / "session_live_latest.json")
            trials_path = self.trials.save(logs / "trials_live_latest.json")
            await self.broadcast(
                {
                    "type": "demo_complete",
                    "session_path": str(session_path),
                    "trials_path": str(trials_path),
                    "session": self.session_out().model_dump(),
                    "devices": [d.model_dump() for d in self.devices_out()],
                }
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            self.camera_ok = False
            self.camera_message = str(exc)
            await self.broadcast(
                {
                    "type": "error",
                    "message": f"Live camera failed: {exc}",
                }
            )
            await self.broadcast({"type": "demo_stopped"})
        finally:
            if detect_task is not None and not detect_task.done():
                detect_task.cancel()
            # Keep warmed models loaded — closing them made the next Start wait again.
            cam.release()
            # Keep shared MQTT publisher alive across sessions
            engine.emg.close()
            self._engine = None
            self._gaze_est = None
            self._recalibrate = False
            self._look_wizard = None
            self.demo_running = False

    async def _run_mock(self) -> None:
        root = Path(__file__).resolve().parents[3]
        logs = root / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        decisions_path = logs / "decisions_app_latest.jsonl"
        if decisions_path.exists():
            decisions_path.unlink()

        logger = DecisionLogger(decisions_path)
        publisher = self.publisher
        engine = IntentionEngine(
            cfg=self.cfg,
            logger=logger,
            metrics=self.metrics,
            publisher=publisher,
            hub=self.hub,
        )
        self._engine = engine

        w, h = 960, 540
        fps = max(8.0, min(self.cfg.mock_fps, 20.0))
        delay = 1.0 / fps

        try:
            await self.broadcast(
                {"type": "status", "payload": self.status("0.5.0").model_dump()}
            )
            for t, step in iter_scenario(DEFAULT_SCENARIO, fps=fps):
                if not self.demo_running:
                    break
                frame, gaze, detections = render_mock_frame(
                    w, h, yaw=step.yaw, emg=step.emg, note=step.note
                )
                if not step.face_found:
                    gaze.face_found = False
                    gaze.confidence = 0.0

                result = engine.tick(
                    gaze,
                    detections,
                    prefer_detections=False,
                    frame_w=w,
                    frame_h=h,
                    emg_score_override=step.emg,
                    now=t,
                )

                decision = DecisionOut(
                    ts=datetime.now(timezone.utc).isoformat(),
                    action=result.decision.action,
                    selected_device=result.decision.selected_device,
                    selected_label=result.selected.label if result.selected else None,
                    reason=result.decision.reason,
                    yaw=round(gaze.yaw, 3),
                    emg=round(result.emg_score, 3),
                )
                if result.changed:
                    self.last_decision = decision
                    self.decisions.append(decision)
                self._record_tick_result(result, decision)

                hub_states = {d.device_id: d.is_on for d in self.hub.snapshot()}
                frame, _, _ = render_mock_frame(
                    w,
                    h,
                    yaw=step.yaw,
                    emg=result.emg_score,
                    note=step.note,
                    hub_states=hub_states,
                    selected_id=result.selected.target_id if result.selected else None,
                    candidate_id=result.candidate.target_id if result.candidate else None,
                    dwell_progress=result.dwell_progress,
                    action=result.decision.action,
                )
                preview = self._encode_preview(frame)

                await self._emit_tick(
                    note=step.note,
                    decision=decision,
                    dwell=result.dwell_progress,
                    preview=preview,
                    actuation=result.actuation,
                    t=t,
                )
                await asyncio.sleep(delay)

            session_path = self.metrics.save(logs / "session_app_latest.json")
            trials_path = self.trials.save(logs / "trials_app_latest.json")
            await self.broadcast(
                {
                    "type": "demo_complete",
                    "session_path": str(session_path),
                    "trials_path": str(trials_path),
                    "session": self.session_out().model_dump(),
                    "devices": [d.model_dump() for d in self.devices_out()],
                }
            )
        except asyncio.CancelledError:
            raise
        finally:
            engine.emg.close()
            self._engine = None
            self.demo_running = False


runtime = AppRuntime()
