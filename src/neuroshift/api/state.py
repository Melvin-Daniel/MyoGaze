"""In-memory product runtime for the Control App."""

from __future__ import annotations

import asyncio
import base64
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

import cv2

from ..appliances import ApplianceHub
from ..camera import Camera
from ..config import Config, apply_overrides, load_config
from ..detector import ObjectDetector
from ..engine import IntentionEngine
from ..gaze import FaceGazeEstimator
from ..logger import DecisionLogger
from ..metrics import SessionMetrics
from ..mock_scene import DEFAULT_SCENARIO, iter_scenario, render_mock_frame
from ..mqtt_bridge import DecisionPublisher, MqttConfig
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
        self.last_decision: DecisionOut | None = None
        self.decisions: list[DecisionOut] = []
        self.demo_running = False
        self._demo_task: asyncio.Task | None = None
        self._subscribers: set[Callable[[dict[str, Any]], Awaitable[None]]] = set()
        self.mode = "live"  # live | mock
        self.detect_mode = "objects"  # objects | slots
        self.camera_ok: bool | None = None
        self.camera_message = "Camera not probed yet"
        self._emg_pulse_until = 0.0
        self._ensure_seed_devices()

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
        return {"ok": True, "message": "Confirm pulse sent"}

    def current_emg(self) -> float:
        return 1.0 if time.time() < self._emg_pulse_until else 0.0

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

    def settings_out(self) -> SettingsOut:
        return SettingsOut(
            product_name=self.cfg.product_name,
            dwell_seconds=self.cfg.dwell_seconds,
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
        self.cfg = apply_overrides(self.cfg, overrides)
        return self.settings_out()

    def devices_out(self) -> list[DeviceOut]:
        self._ensure_seed_devices()
        return [
            DeviceOut(
                id=d.device_id,
                label=d.label,
                is_on=d.is_on,
                toggle_count=d.toggle_count,
            )
            for d in self.hub.snapshot()
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
        return StatusOut(
            version=version,
            mode=self.mode,
            principle="Looking selects. Muscle confirms. Unsure → Abstain.",
            devices=self.devices_out(),
            last_decision=self.last_decision,
            session=self.session_out(),
            demo_running=self.demo_running,
            camera_ok=self.camera_ok,
            camera_message=self.camera_message,
            detect_mode=self.detect_mode,
        )

    def set_detect_mode(self, mode: str) -> dict[str, Any]:
        if mode not in {"objects", "slots"}:
            return {"ok": False, "detect_mode": self.detect_mode, "message": "Use objects or slots"}
        self.detect_mode = mode
        return {"ok": True, "detect_mode": self.detect_mode, "message": f"Detect mode → {mode}"}

    def reset_session(self) -> None:
        self.hub = ApplianceHub()
        self._ensure_seed_devices()
        self.metrics = SessionMetrics()
        self.last_decision = None
        self.decisions = []
        self._emg_pulse_until = 0.0

    def manual_toggle(self, device_id: str) -> DeviceOut | None:
        state = self.hub.devices.get(device_id)
        if state is None:
            return None
        state.is_on = not state.is_on
        state.toggle_count += 1
        return DeviceOut(
            id=state.device_id,
            label=state.label,
            is_on=state.is_on,
            toggle_count=state.toggle_count,
        )

    async def start_demo(self, prefer: str | None = None) -> dict[str, Any]:
        if self.demo_running:
            return {"started": False, "message": "Session already running"}

        mode = prefer or self.mode
        if mode == "live":
            probe = self.probe_camera()
            if not probe["ok"]:
                # Auto-fallback so the product still demos
                self.mode = "mock"
                mode = "mock"
                msg_prefix = f"Camera unavailable ({probe['message']}). Falling back to mock. "
            else:
                self.mode = "live"
                msg_prefix = ""
        else:
            self.mode = "mock"
            msg_prefix = ""

        self.reset_session()
        self.demo_running = True
        if mode == "live":
            self._demo_task = asyncio.create_task(self._run_live())
            message = msg_prefix + "Live camera session started — look at a target, then Confirm"
        else:
            self._demo_task = asyncio.create_task(self._run_mock())
            message = msg_prefix + "Mock session started"
        await self.broadcast({"type": "demo_started", "mode": self.mode})
        return {"started": True, "message": message, "mode": self.mode}

    async def stop_demo(self) -> dict[str, Any]:
        if self._demo_task and not self._demo_task.done():
            self._demo_task.cancel()
            try:
                await self._demo_task
            except asyncio.CancelledError:
                pass
        self.demo_running = False
        await self.broadcast({"type": "demo_stopped"})
        return {"stopped": True}

    def _encode_preview(self, frame) -> str | None:
        max_w = max(160, int(self.cfg.live_preview_max_width))
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
    ) -> None:
        payload: dict[str, Any] = {
            "type": "tick",
            "t": t,
            "note": note,
            "mode": self.mode,
            "detect_mode": self.detect_mode,
            "decision": decision.model_dump(),
            "dwell": round(dwell, 2),
            "devices": [d.model_dump() for d in self.devices_out()],
            "targets": targets or [],
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
        publisher = DecisionPublisher(
            MqttConfig(
                enabled=self.cfg.mqtt_enabled,
                host=self.cfg.mqtt_host,
                port=self.cfg.mqtt_port,
            )
        )
        # Wider center zone so facing the camera = Fan, not Plug/Lamp
        live_cfg = apply_overrides(
            self.cfg,
            {
                "frame_width": self.cfg.live_frame_width,
                "frame_height": self.cfg.live_frame_height,
                "yaw_side_threshold": self.cfg.live_yaw_side_threshold,
                "gaze_smooth_alpha": 0.40,
                "dwell_seconds": max(0.35, min(self.cfg.dwell_seconds, 0.55)),
            },
        )
        engine = IntentionEngine(
            cfg=live_cfg,
            logger=logger,
            metrics=self.metrics,
            publisher=publisher,
            hub=self.hub,
        )
        cam = Camera(live_cfg)
        gaze_est = FaceGazeEstimator(smooth_alpha=live_cfg.gaze_smooth_alpha)
        prefer_detections = self.detect_mode == "objects" and self.cfg.live_use_yolo
        detector = None
        if prefer_detections:
            detector = ObjectDetector(
                model_name=self.cfg.yolo_model,
                conf=0.18,
                every_n_frames=2,
                imgsz=480,
                iou_match=0.22,
            )
            prefer_detections = detector.available
            if not prefer_detections:
                self.detect_mode = "slots"

        sticky_note = (
            "Hold a bottle/phone/cup in view — look at it, then Confirm"
            if prefer_detections
            else "Look LEFT=Lamp · STRAIGHT=Fan · RIGHT=Plug, then Confirm"
        )
        last_preview: str | None = None
        calibrate_left = int(self.cfg.live_auto_calibrate_frames)
        calib_samples: list[float] = []
        target_dt = 1.0 / max(6.0, float(self.cfg.live_target_fps))

        try:
            cam.open()
            self.camera_ok = True
            self.camera_message = f"Camera {self.cfg.camera_index} streaming"
            await self.broadcast(
                {"type": "status", "payload": self.status("0.5.2").model_dump()}
            )

            frame_i = 0
            while self.demo_running:
                loop_t0 = time.perf_counter()
                # Allow mid-session mode switches
                use_objects = self.detect_mode == "objects" and detector is not None and detector.available

                frame = await asyncio.to_thread(cam.read)
                if self.cfg.mirror_preview:
                    frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]

                g = await asyncio.to_thread(gaze_est.estimate, frame)

                if calibrate_left > 0 and g.face_found:
                    calib_samples.append(g.raw_yaw)
                    calibrate_left -= 1
                    if calibrate_left == 0 and calib_samples:
                        gaze_est.yaw_offset = float(sum(calib_samples) / len(calib_samples))
                        gaze_est._yaw_s = 0.0
                        sticky_note = "Calibrated — look at an object (or use slots)"

                detections = []
                if use_objects and detector is not None:
                    detections = await asyncio.to_thread(detector.detect, frame)
                    # Register seen objects so Home/device list updates live
                    for det in detections:
                        self.hub.ensure(det.obj_id, det.appliance or det.label)

                emg = self.current_emg()
                result = engine.tick(
                    g,
                    detections,
                    prefer_detections=use_objects and bool(detections),
                    frame_w=w,
                    frame_h=h,
                    emg_score_override=emg,
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

                targets = [
                    {
                        "id": d.obj_id,
                        "label": d.appliance or d.label,
                        "conf": round(d.conf, 2),
                        "selected": bool(
                            result.selected and result.selected.target_id == d.obj_id
                        ),
                        "candidate": bool(
                            result.candidate and result.candidate.target_id == d.obj_id
                        ),
                    }
                    for d in detections
                ]

                send_preview = frame_i % max(1, int(self.cfg.live_preview_every_n)) == 0
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
                        nose_xy=g.nose_xy,
                        candidate=result.candidate,
                        selected=result.selected,
                        dwell_progress=result.dwell_progress,
                        emg_score=result.emg_score,
                        action=result.decision.action,
                        hub_states=hub_states,
                        prefer_slots=not (use_objects and detections),
                        detections_xyxy=det_draw,
                    )
                    preview = self._encode_preview(annotated)
                    last_preview = preview

                n_det = len(detections)
                if calibrate_left > 0:
                    sticky_note = "Hold still — calibrating center…"
                elif result.selected:
                    sticky_note = f"Ready: {result.selected.label} — press Confirm"
                elif result.candidate:
                    sticky_note = f"Dwelling on {result.candidate.label}…"
                elif not g.face_found:
                    sticky_note = "Face not found — face the camera"
                elif use_objects:
                    sticky_note = (
                        f"Objects seen: {n_det} — look toward one (phone/bottle/cup…)"
                        if n_det
                        else "No objects yet — hold a phone/bottle/cup in view"
                    )
                else:
                    sticky_note = "Slots mode — look LEFT / STRAIGHT / RIGHT"

                await self._emit_tick(
                    note=sticky_note,
                    decision=decision,
                    dwell=result.dwell_progress,
                    preview=preview if send_preview else None,
                    actuation=result.actuation,
                    t=frame_i / max(1.0, self.cfg.live_target_fps),
                    targets=targets,
                )
                frame_i += 1
                elapsed = time.perf_counter() - loop_t0
                await asyncio.sleep(max(0.0, target_dt - elapsed))

            session_path = self.metrics.save(logs / "session_live_latest.json")
            await self.broadcast(
                {
                    "type": "demo_complete",
                    "session_path": str(session_path),
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
                {"type": "error", "message": f"Live camera failed: {exc}"}
            )
        finally:
            try:
                gaze_est.close()
            except Exception:  # noqa: BLE001
                pass
            cam.release()
            publisher.close()
            engine.emg.close()
            self.demo_running = False

    async def _run_mock(self) -> None:
        root = Path(__file__).resolve().parents[3]
        logs = root / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        decisions_path = logs / "decisions_app_latest.jsonl"
        if decisions_path.exists():
            decisions_path.unlink()

        logger = DecisionLogger(decisions_path)
        publisher = DecisionPublisher(
            MqttConfig(
                enabled=self.cfg.mqtt_enabled,
                host=self.cfg.mqtt_host,
                port=self.cfg.mqtt_port,
            )
        )
        engine = IntentionEngine(
            cfg=self.cfg,
            logger=logger,
            metrics=self.metrics,
            publisher=publisher,
            hub=self.hub,
        )

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
            await self.broadcast(
                {
                    "type": "demo_complete",
                    "session_path": str(session_path),
                    "session": self.session_out().model_dump(),
                    "devices": [d.model_dump() for d in self.devices_out()],
                }
            )
        except asyncio.CancelledError:
            raise
        finally:
            publisher.close()
            engine.emg.close()
            self.demo_running = False


runtime = AppRuntime()
