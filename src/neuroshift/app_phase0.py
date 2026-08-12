"""
Phase-0 live loop: laptop cam + face gaze + YOLO targets + fake EMG.

Controls:
  SPACE  - one-shot EMG confirm (pulse)  [keyboard mode]
  X      - cancel EMG pulse
  C      - calibrate "looking straight" as center
  D      - toggle detection mode (YOLO objects <-> virtual slots)
  E      - cycle EMG mode: keyboard <-> mouse
  R      - reset all virtual appliance states to OFF
  Q      - quit

Mouse EMG mode:
  Move cursor UP in the window = stronger "muscle" effort.
  Cross the confirm threshold while dwelling on a green target → ACT.

Run from repo root:
  python -m src.neuroshift
"""

from __future__ import annotations

import time
from collections import deque

import cv2

from .appliances import ApplianceHub
from .camera import Camera
from .config import DEFAULT
from .detector import ObjectDetector
from .emg_source import EmgSource
from .fusion import IntentionFusion
from .gaze import FaceGazeEstimator
from .logger import DecisionLogger
from .metrics import SessionMetrics
from .mqtt_bridge import DecisionPublisher, MqttConfig
from .selector import select_target, slot_overlays


def _draw_dwell_bar(
    frame,
    xyxy: tuple[int, int, int, int],
    progress: float,
    selected: bool,
) -> None:
    """Thin progress bar under the target box while dwelling."""
    x0, y0, x1, y1 = xyxy
    p = max(0.0, min(1.0, progress))
    bar_y0 = min(y1 + 6, frame.shape[0] - 10)
    bar_y1 = bar_y0 + 8
    cv2.rectangle(frame, (x0, bar_y0), (x1, bar_y1), (40, 40, 40), -1)
    fill_x = int(x0 + (x1 - x0) * p)
    color = (0, 255, 120) if selected or p >= 1.0 else (0, 200, 255)
    if fill_x > x0:
        cv2.rectangle(frame, (x0, bar_y0), (fill_x, bar_y1), color, -1)


def _draw_emg_strip(
    frame,
    history: deque[float],
    threshold: float,
    x: int = 12,
    y: int = 130,
    width: int = 220,
    height: int = 48,
) -> None:
    """Mini EMG amplitude strip (research-demo look)."""
    cv2.rectangle(frame, (x, y), (x + width, y + height), (30, 30, 30), -1)
    cv2.rectangle(frame, (x, y), (x + width, y + height), (90, 90, 90), 1)
    thr_y = int(y + height * (1.0 - threshold))
    cv2.line(frame, (x, thr_y), (x + width, thr_y), (80, 80, 200), 1)
    if len(history) < 2:
        return
    pts = []
    n = max(len(history) - 1, 1)
    for i, v in enumerate(history):
        px = x + int(width * i / n)
        py = int(y + height * (1.0 - max(0.0, min(1.0, v))))
        pts.append((px, py))
    for a, b in zip(pts, pts[1:]):
        cv2.line(frame, a, b, (0, 255, 180), 2)
    cv2.putText(
        frame,
        "EMG",
        (x + 4, y + 14),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (180, 255, 200),
        1,
    )


def main() -> None:
    cfg = DEFAULT
    cam = Camera(cfg)
    gaze = FaceGazeEstimator(smooth_alpha=cfg.gaze_smooth_alpha)
    emg = EmgSource(cfg)
    fusion = IntentionFusion(cfg)
    logger = DecisionLogger()
    hub = ApplianceHub()
    metrics = SessionMetrics()
    publisher = DecisionPublisher(
        MqttConfig(
            enabled=cfg.mqtt_enabled,
            host=cfg.mqtt_host,
            port=cfg.mqtt_port,
        )
    )
    emg_history: deque[float] = deque(maxlen=80)
    mouse_xy = {"x": -1, "y": -1}

    print("Loading detector (YOLO if installed)...")
    detector = ObjectDetector(
        model_name=cfg.yolo_model,
        conf=cfg.yolo_conf,
        every_n_frames=cfg.yolo_every_n_frames,
    )
    prefer_detections = detector.available

    cam.open()
    win = "NeuroShift Phase-0"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    def on_mouse(event, x, y, flags, param) -> None:  # noqa: ARG001
        mouse_xy["x"] = x
        mouse_xy["y"] = y

    cv2.setMouseCallback(win, on_mouse)
    print("NeuroShift Phase-0 (software upgrades)")
    print(
        "SPACE=confirm | X=cancel | C=calibrate | E=EMG mode | "
        "D=YOLO/slots | R=reset | Q=quit"
    )
    print(f"EMG mode -> {cfg.emg_mode}")
    print(f"Logs -> {logger.path}")
    print(f"Publisher mode -> {publisher.mode}")
    if detector.available:
        print(
            "YOLO ready. Stand-ins: bottle=Lamp, cup=Fan, phone=Plug, "
            "remote=AC, book/laptop=TV"
        )
    else:
        print("YOLO not installed — using virtual Lamp/Fan/Plug slots.")

    dwell_id = None
    dwell_t0 = None
    sticky_id = None
    last_decision = None
    flash_until = 0.0
    flash_text = ""
    cooldown_until = 0.0
    tip_until = time.time() + 4.0

    try:
        while True:
            frame = cam.read()
            if cfg.mirror_preview:
                frame = cv2.flip(frame, 1)

            h, w = frame.shape[:2]
            g = gaze.estimate(frame)
            detections = detector.detect(frame) if prefer_detections else []

            candidate = None
            selected = None
            dwell_progress = 0.0
            if g.face_found and g.confidence >= cfg.gaze_select_threshold:
                candidate = select_target(
                    g,
                    detections,
                    w,
                    h,
                    side_threshold=cfg.yaw_side_threshold,
                    prefer_detections=prefer_detections,
                    hysteresis=cfg.yaw_hysteresis,
                    sticky_id=sticky_id,
                )
                if candidate is not None:
                    sticky_id = candidate.target_id
                    if dwell_id != candidate.target_id:
                        dwell_id = candidate.target_id
                        dwell_t0 = time.time()
                        dwell_progress = 0.0
                    elif dwell_t0 is not None:
                        dwell_progress = (time.time() - dwell_t0) / cfg.dwell_seconds
                        if dwell_progress >= 1.0:
                            selected = candidate
                            dwell_progress = 1.0
                else:
                    dwell_id = None
                    dwell_t0 = None
                    sticky_id = None
            else:
                dwell_id = None
                dwell_t0 = None
                sticky_id = None

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q")):
                break
            if key in (ord("d"), ord("D")):
                prefer_detections = not prefer_detections
                dwell_id = None
                dwell_t0 = None
                sticky_id = None
                mode = "YOLO objects" if prefer_detections else "virtual slots"
                print(f"Mode -> {mode}")
            if key in (ord("r"), ord("R")):
                hub.devices.clear()
                print("Virtual appliances reset to OFF")
            if key in (ord("e"), ord("E")):
                nxt = "mouse" if cfg.emg_mode == "keyboard" else "keyboard"
                emg.set_mode(nxt)
                flash_text = f"EMG mode -> {nxt.upper()}"
                flash_until = time.time() + 1.4
                print(flash_text)
            if key in (ord("c"), ord("C")):
                if g.face_found:
                    offset = gaze.calibrate_center()
                    dwell_id = None
                    dwell_t0 = None
                    sticky_id = None
                    flash_text = f"CALIBRATED center (offset={offset:+.2f})"
                    flash_until = time.time() + 1.5
                    print(flash_text)
                else:
                    flash_text = "Face not found — look at camera, press C"
                    flash_until = time.time() + 1.5

            mouse_y_norm = None
            if cfg.emg_mode == "mouse" and mouse_xy["y"] >= 0:
                mouse_y_norm = mouse_xy["y"] / max(h, 1)

            now = time.time()
            emg_score = emg.poll(key, mouse_y_norm=mouse_y_norm)
            if now < cooldown_until:
                emg_score = 0.0
            emg_ok = emg.confirmed(emg_score)
            emg_history.append(emg_score)

            decision = fusion.decide(
                selected_device=selected.target_id if selected else None,
                gaze_confidence=g.confidence if g.face_found else 0.0,
                emg_score=emg_score,
                emg_confirmed=emg_ok,
            )

            changed = (
                last_decision is None
                or decision.action != last_decision.action
                or decision.selected_device != last_decision.selected_device
            )
            if changed:
                metrics.on_decision(decision.action, decision.reason)
                logger.log(
                    {
                        "action": decision.action,
                        "selected_device": decision.selected_device,
                        "selected_label": selected.label if selected else None,
                        "reason": decision.reason,
                        "yaw": round(g.yaw, 3),
                        "emg": round(emg_score, 3),
                        "emg_mode": cfg.emg_mode,
                        "mode": "yolo" if prefer_detections else "slots",
                        "n_detections": len(detections),
                    }
                )
                publisher.publish_decision(
                    {
                        "action": decision.action,
                        "device": decision.selected_device,
                        "label": selected.label if selected else None,
                        "reason": decision.reason,
                        "yaw": round(g.yaw, 3),
                        "emg": round(emg_score, 3),
                    }
                )
                print(
                    f"[{decision.action}] {decision.selected_device} "
                    f"({selected.label if selected else '-'}) "
                    f"yaw={g.yaw:+.2f} emg={emg_score:.2f}"
                )
                last_decision = decision

            event = hub.on_decision(
                decision.action,
                decision.selected_device,
                selected.label if selected else None,
            )
            if event is not None:
                metrics.on_actuation()
                emg.clear()
                cooldown_until = now + cfg.act_cooldown_seconds
                publisher.publish_actuate(
                    {
                        "device_id": event.device_id,
                        "label": event.label,
                        "command": event.command,
                        "state": event.new_state,
                    }
                )
                flash_text = f"TOGGLED {event.label} -> {event.command}"
                flash_until = time.time() + 1.2
                print(flash_text)

            if not prefer_detections or not detections:
                for t in slot_overlays(w, h):
                    assert t.xyxy is not None
                    x0, y0, x1, y1 = t.xyxy
                    st = hub.devices.get(t.target_id)
                    on = st.is_on if st else False
                    is_sel = selected and selected.target_id == t.target_id
                    is_cand = candidate and candidate.target_id == t.target_id
                    color = (0, 255, 0) if is_sel else (0, 220, 255) if is_cand else (70, 70, 70)
                    thick = 3 if is_sel else 2 if is_cand else 1
                    cv2.rectangle(frame, (x0, y0), (x1, y1), color, thick)
                    tag = f"{t.label} [{'ON' if on else 'off'}]"
                    cv2.putText(
                        frame,
                        tag,
                        (x0 + 6, y0 + 22),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        color,
                        2,
                    )
                    if is_cand or is_sel:
                        _draw_dwell_bar(frame, t.xyxy, dwell_progress, bool(is_sel))
            else:
                for obj in detections:
                    x0, y0, x1, y1 = obj.xyxy
                    st = hub.devices.get(obj.obj_id)
                    on = st.is_on if st else False
                    is_sel = selected and selected.target_id == obj.obj_id
                    is_cand = candidate and candidate.target_id == obj.obj_id
                    color = (0, 255, 0) if is_sel else (0, 220, 255) if is_cand else (180, 180, 40)
                    thick = 3 if is_sel else 2
                    cv2.rectangle(frame, (x0, y0), (x1, y1), color, thick)
                    tag = f"{obj.hud_label} [{'ON' if on else 'off'}]"
                    cv2.putText(
                        frame,
                        tag,
                        (x0, max(20, y0 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        color,
                        2,
                    )
                    if is_cand or is_sel:
                        _draw_dwell_bar(frame, obj.xyxy, dwell_progress, bool(is_sel))

            if g.nose_xy is not None:
                nx, ny = int(g.nose_xy[0]), int(g.nose_xy[1])
                aim_target = selected or candidate
                if aim_target is not None and aim_target.xyxy is not None:
                    ax0, ay0, ax1, ay1 = aim_target.xyxy
                    aim_x = (ax0 + ax1) // 2
                    aim_y = (ay0 + ay1) // 2
                else:
                    aim_x = int(w * (0.5 + 0.42 * g.yaw))
                    aim_y = int(h * 0.35)
                ray_color = (0, 255, 120) if selected else (0, 200, 255)
                cv2.circle(frame, (nx, ny), 6, (255, 200, 0), -1)
                cv2.line(frame, (nx, ny), (aim_x, aim_y), ray_color, 2)
                cv2.circle(frame, (aim_x, aim_y), 7, ray_color, -1)

            mode = "YOLO" if prefer_detections else "SLOTS"
            cool = " COOLDOWN" if now < cooldown_until else ""
            status = (
                f"{decision.action} | EMG={emg_score:.2f}({'ON' if emg_ok else 'off'}) "
                f"| yaw={g.yaw:+.2f} | dwell={dwell_progress:.0%} | "
                f"{mode} n={len(detections)} | src={cfg.emg_mode}{cool}"
            )
            cv2.putText(frame, status, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2)
            cv2.putText(
                frame,
                "Yellow=dwell  Green=ready  E=mouse EMG  SPACE=pulse  C=calibrate  D/R/Q",
                (12, 56),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (200, 200, 200),
                1,
            )
            _draw_emg_strip(frame, emg_history, cfg.emg_confirm_threshold)
            cv2.putText(
                frame,
                metrics.summary(),
                (12, h - 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (180, 220, 180),
                1,
            )

            if time.time() < tip_until and g.face_found:
                cv2.putText(
                    frame,
                    "Tip: look STRAIGHT at cam, press C | press E for mouse-EMG practice",
                    (12, 84),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.50,
                    (180, 255, 220),
                    2,
                )

            if time.time() < flash_until:
                cv2.putText(
                    frame,
                    flash_text,
                    (12, 112 if time.time() < tip_until else 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 255, 120),
                    2,
                )

            cv2.imshow(win, frame)
    finally:
        gaze.close()
        emg.close()
        cam.release()
        publisher.close()
        cv2.destroyAllWindows()
        session_path = metrics.save()
        print(f"Saved decisions: {logger.path}")
        print(f"Saved session:   {session_path}")
        print(f"Session: {metrics.summary()}")


if __name__ == "__main__":
    main()
