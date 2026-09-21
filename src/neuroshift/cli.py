"""NeuroShift product CLI."""

from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path


def _lan_ips() -> list[str]:
    """Candidate addresses the phone app can be pointed at.

    The default-route address comes first, but it is only a guess: on a laptop
    with both Ethernet and Wi-Fi it names the wrong adapter when the phone is on
    Wi-Fi, so every local IPv4 is listed and the user picks the matching subnet.
    """
    found: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            found.append(str(s.getsockname()[0]))
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.append(str(info[4][0]))
    except OSError:
        pass
    return [
        ip
        for i, ip in enumerate(found)
        if ip not in found[:i] and not ip.startswith(("127.", "169.254."))
    ]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="neuroshift",
        description="NeuroShift — gaze-selected, EMG-confirmed smart-home intention",
    )
    p.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional YAML/JSON config (default: config/default.yaml)",
    )
    sub = p.add_subparsers(dest="cmd", required=False)

    live = sub.add_parser("live", help="Run live webcam demo (needs camera)")
    live.add_argument("--camera", type=int, default=None)

    mock = sub.add_parser("mock", help="Run offline product demo (no camera)")
    mock.add_argument("--show", action="store_true", help="Show OpenCV window")
    mock.add_argument("--no-video", action="store_true", help="Skip writing mp4")

    rep = sub.add_parser("report", help="Build HTML report from latest logs")
    rep.add_argument("--session", type=Path, default=None)
    rep.add_argument("--decisions", type=Path, default=None)
    rep.add_argument("--out", type=Path, default=None)

    sub.add_parser("doctor", help="Print environment / product status")

    serve = sub.add_parser("serve", help="Run Control App API + PWA (phone/desktop)")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--ssl-port", type=int, default=8443, help="HTTPS port for iPhone camera")
    serve.add_argument("--no-ssl", action="store_true", help="Do not start the HTTPS listener")
    serve.add_argument("--reload", action="store_true")

    return p


def main(argv: list[str] | None = None) -> int:
    # Product default: Control App server when no subcommand given
    if argv is None:
        import sys

        argv = sys.argv[1:]
    if not argv:
        argv = ["serve"]

    args = _build_parser().parse_args(argv)
    if not args.cmd:
        args.cmd = "serve"

    from .config import load_config, apply_overrides
    from . import __version__

    cfg = load_config(args.config)

    if args.cmd == "doctor":
        root = Path(__file__).resolve().parents[2]
        print(f"NeuroShift v{__version__}")
        print(f"Root: {root}")
        print(f"Config emg_mode={cfg.emg_mode} dwell={cfg.dwell_seconds}s")
        print(f"Face model: {(root / 'models' / 'face_landmarker.task').exists()}")
        print(f"YOLO weights: {cfg.yolo_model}")
        try:
            import cv2  # noqa: F401
            import mediapipe  # noqa: F401
            import numpy  # noqa: F401

            print("Core deps: OK (cv2, mediapipe, numpy)")
        except Exception as exc:  # noqa: BLE001
            print(f"Core deps: MISSING ({exc})")
        try:
            from ultralytics import YOLO  # noqa: F401

            print("YOLO: OK")
        except Exception:
            print("YOLO: optional / not installed")
        print("Commands: neuroshift serve | mock | live | report | doctor")
        return 0

    if args.cmd == "serve":
        import threading

        import uvicorn

        from .devcert import ensure_dev_certs

        candidates = _lan_ips() or ["<your-lan-ip>"]
        ssl_pair = None if getattr(args, "no_ssl", False) else ensure_dev_certs(
            [ip for ip in candidates if ip != "<your-lan-ip>"]
        )
        ssl_port = int(getattr(args, "ssl_port", 8443))
        banner = [
            f"NeuroShift Control App v{__version__}",
            f"Open on this PC:  http://127.0.0.1:{args.port}",
            f"API docs:         http://127.0.0.1:{args.port}/docs",
            "",
            "Laptop / Android app — HTTP:",
        ]
        banner += [f"    http://{ip}:{args.port}" for ip in candidates]
        if ssl_pair:
            banner += [
                "",
                "iPhone (no Mac / no App Store): open this HTTP page in Safari,",
                "install the certificate, then Add to Home Screen. Do not use Visit Website:",
            ]
            banner += [f"    http://{ip}:{args.port}/iphone" for ip in candidates]
            banner += ["Then open:"]
            banner += [f"    https://{ip}:{ssl_port}" for ip in candidates]
        else:
            banner += [
                "",
                "HTTPS is off — iPhone Safari will block the camera on HTTP.",
                "Install the 'cryptography' package and restart serve, or use the Android app.",
            ]
        banner += [
            "",
            f"Install the Android app: http://{candidates[0]}:{args.port}/app.apk",
        ]
        # uvicorn logs to stderr; flush so this banner is not stuck in the buffer
        print("\n".join(banner), flush=True)

        if ssl_pair:
            cert_path, key_path = ssl_pair

            def _run_https() -> None:
                config = uvicorn.Config(
                    "src.neuroshift.api.app:app",
                    host=args.host,
                    port=ssl_port,
                    ssl_certfile=str(cert_path),
                    ssl_keyfile=str(key_path),
                    log_level="warning",
                )
                server = uvicorn.Server(config)
                server.install_signal_handlers = lambda: None  # type: ignore[method-assign]
                server.run()

            threading.Thread(target=_run_https, daemon=True, name="https").start()

        uvicorn.run(
            "src.neuroshift.api.app:app",
            host=args.host,
            port=args.port,
            reload=bool(args.reload),
        )
        return 0

    if args.cmd == "mock":
        from .demo import run_mock_demo
        from .report import build_report

        result = run_mock_demo(
            cfg,
            show_window=bool(args.show),
            write_video=not args.no_video,
        )
        report = build_report(
            session_path=Path(result["session"]),
            decisions_path=Path(result["decisions"]),
        )
        print("---")
        print("MOCK DEMO COMPLETE")
        print(f"Summary : {result['summary']}")
        print(f"Session : {result['session']}")
        print(f"Decisions: {result['decisions']}")
        if result.get("video"):
            print(f"Video   : {result['video']}")
        print(f"Report  : {report}")
        print("Devices :", json.dumps(result["devices"], indent=2))
        return 0

    if args.cmd == "report":
        from .report import build_report

        out = build_report(
            session_path=args.session,
            decisions_path=args.decisions,
            out_path=args.out,
        )
        print(f"Report written: {out}")
        return 0

    if args.cmd == "live":
        if args.camera is not None:
            cfg = apply_overrides(cfg, {"camera_index": args.camera})
        # Keep DEFAULT in sync for modules that import DEFAULT at call time
        from . import config as config_mod
        from . import app_phase0

        config_mod.DEFAULT = cfg
        app_phase0.main()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
