"""Headless / windowed mock product demo — no webcam required."""

from __future__ import annotations

from pathlib import Path

import cv2

from .config import Config, DEFAULT
from .engine import IntentionEngine
from .logger import DecisionLogger
from .metrics import SessionMetrics
from .mock_scene import DEFAULT_SCENARIO, iter_scenario, render_mock_frame
from .mqtt_bridge import DecisionPublisher, MqttConfig


def run_mock_demo(
    cfg: Config = DEFAULT,
    *,
    show_window: bool = False,
    write_video: bool | None = None,
    out_dir: Path | None = None,
) -> dict:
    """
    Run the scripted Act/Abstain product scenario offline.

    Returns paths + metrics summary for the CLI / report step.
    """
    root = Path(__file__).resolve().parents[2]
    out_dir = Path(out_dir) if out_dir else (root / "logs")
    out_dir.mkdir(parents=True, exist_ok=True)

    decisions_path = out_dir / "decisions_mock_latest.jsonl"
    if decisions_path.exists():
        decisions_path.unlink()

    logger = DecisionLogger(decisions_path)
    metrics = SessionMetrics()
    publisher = DecisionPublisher(
        MqttConfig(enabled=cfg.mqtt_enabled, host=cfg.mqtt_host, port=cfg.mqtt_port)
    )
    engine = IntentionEngine(
        cfg=cfg,
        logger=logger,
        metrics=metrics,
        publisher=publisher,
    )

    w, h = cfg.frame_width, cfg.frame_height
    fps = cfg.mock_fps
    write_video = cfg.mock_write_video if write_video is None else write_video
    video_path = out_dir / "neuroshift_mock_demo.mp4"
    writer = None
    if write_video:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(video_path), fourcc, fps, (w, h))

    win = "NeuroShift Mock Demo"
    if show_window:
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    # Use deterministic time so dwell thresholds work without wall clock jumps
    sim_t0 = 0.0
    last_print = ""

    try:
        for t, step in iter_scenario(DEFAULT_SCENARIO, fps=fps):
            hub_states = {d.device_id: d.is_on for d in engine.hub.snapshot()}
            # Pre-render gaze input for engine
            frame, gaze, detections = render_mock_frame(
                w,
                h,
                yaw=step.yaw,
                emg=step.emg,
                note=step.note,
                hub_states=hub_states,
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
                now=sim_t0 + t,
            )

            # Re-render with decision overlays
            hub_states = {d.device_id: d.is_on for d in engine.hub.snapshot()}
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
            cv2.putText(
                frame,
                metrics.summary(),
                (16, h - 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (180, 220, 180),
                1,
            )

            if result.changed or result.actuation is not None:
                line = (
                    f"t={t:5.2f}s [{result.decision.action}] "
                    f"{result.decision.selected_device or '-':8} "
                    f"emg={result.emg_score:.1f} | {step.note}"
                )
                if line != last_print:
                    print(line)
                    last_print = line
                if result.actuation is not None:
                    print(
                        f"         >> TOGGLED {result.actuation.label} "
                        f"-> {result.actuation.command}"
                    )

            if writer is not None:
                writer.write(frame)
            if show_window:
                cv2.imshow(win, frame)
                if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
                    break
    finally:
        if writer is not None:
            writer.release()
        publisher.close()
        engine.emg.close()
        if show_window:
            cv2.destroyAllWindows()

    session_path = metrics.save(out_dir / "session_mock_latest.json")
    return {
        "decisions": str(logger.path),
        "session": str(session_path),
        "video": str(video_path) if write_video else None,
        "summary": metrics.summary(),
        "metrics": metrics.to_dict(),
        "devices": [
            {"id": d.device_id, "label": d.label, "on": d.is_on, "toggles": d.toggle_count}
            for d in engine.hub.snapshot()
        ],
    }
