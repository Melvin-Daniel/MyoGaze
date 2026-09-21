"""FastAPI application — NeuroShift Control App backend."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..accounts import login as account_login
from ..accounts import logout as account_logout
from ..accounts import register as account_register
from ..accounts import user_for_token
from .schemas import (
    CameraStatusOut,
    DemoStartIn,
    DemoStartOut,
    DeviceOut,
    HealthOut,
    SettingsIn,
    SettingsOut,
    StatusOut,
)
from .state import runtime


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    asyncio.get_running_loop().run_in_executor(None, runtime.warmup_models)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="NeuroShift Control App",
        version=__version__,
        description="Gaze-selected, EMG-confirmed smart-home intention — product API",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthOut)
    def health() -> HealthOut:
        return HealthOut(version=__version__)

    @app.post("/api/auth/register")
    def auth_register(body: dict) -> dict:
        from fastapi import HTTPException

        try:
            return account_register(str(body.get("identifier", "")), str(body.get("password", "")))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/auth/login")
    def auth_login(body: dict) -> dict:
        from fastapi import HTTPException

        try:
            return account_login(str(body.get("identifier", "")), str(body.get("password", "")))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/auth/me")
    def auth_me(authorization: str = Header(default="")) -> dict:
        from fastapi import HTTPException

        token = authorization.removeprefix("Bearer ").strip()
        user = user_for_token(token)
        if user is None:
            raise HTTPException(status_code=401, detail="Sign in required")
        return {"user": user}

    @app.post("/api/auth/logout")
    def auth_logout(body: dict) -> dict:
        account_logout(str(body.get("token", "")))
        return {"ok": True}

    @app.get("/api/camera", response_model=CameraStatusOut)
    def camera_status() -> CameraStatusOut:
        result = runtime.probe_camera()
        return CameraStatusOut(
            ok=bool(result["ok"]),
            message=str(result["message"]),
            index=int(result.get("index", 0)),
        )

    @app.get("/api/status", response_model=StatusOut)
    def status() -> StatusOut:
        return runtime.status(__version__)

    @app.get("/api/devices", response_model=list[DeviceOut])
    def devices() -> list[DeviceOut]:
        return runtime.devices_out()

    @app.post("/api/devices/{device_id}/toggle", response_model=DeviceOut)
    async def toggle_device(device_id: str) -> DeviceOut:
        out = runtime.manual_toggle(device_id)
        if out is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Device not found")
        await runtime.broadcast(
            {
                "type": "device_toggled",
                "device": out.model_dump(),
                "devices": [d.model_dump() for d in runtime.devices_out()],
            }
        )
        return out

    @app.get("/api/decisions")
    def decisions(limit: int = 100) -> list[dict]:
        return [d.model_dump() for d in runtime.decisions[-limit:]]

    @app.get("/api/session")
    def session() -> dict:
        return runtime.session_out().model_dump()

    @app.post("/api/session/reset")
    async def reset_session() -> dict:
        runtime.reset_session()
        await runtime.broadcast(
            {
                "type": "session_reset",
                "payload": runtime.status(__version__).model_dump(),
            }
        )
        return {"ok": True}

    @app.get("/api/settings", response_model=SettingsOut)
    def get_settings() -> SettingsOut:
        return runtime.settings_out()

    @app.put("/api/settings", response_model=SettingsOut)
    def put_settings(body: SettingsIn) -> SettingsOut:
        return runtime.update_settings(body)

    @app.post("/api/demo/start", response_model=DemoStartOut)
    async def demo_start(body: DemoStartIn | None = None) -> DemoStartOut:
        prefer = body.mode if body else None
        camera = body.camera if body else None
        result = await runtime.start_demo(prefer=prefer, camera=camera)
        return DemoStartOut(
            started=result["started"],
            message=result["message"],
            mode=result.get("mode"),
            camera=result.get("camera"),
        )

    @app.post("/api/demo/stop")
    async def demo_stop() -> dict:
        return await runtime.stop_demo()

    @app.post("/api/confirm")
    async def confirm_intent() -> dict:
        result = runtime.pulse_confirm()
        await runtime.broadcast({"type": "confirm_pulse"})
        return result

    @app.post("/api/detect_mode")
    async def detect_mode(body: dict) -> dict:
        mode = str(body.get("mode", "objects"))
        result = runtime.set_detect_mode(mode)
        await runtime.broadcast({"type": "detect_mode", **result})
        return result

    @app.post("/api/dwell_mode")
    async def dwell_mode(body: dict) -> dict:
        required = bool(body.get("dwell_required", True))
        result = runtime.set_dwell_required(required)
        await runtime.broadcast({"type": "dwell_mode", **result})
        return result

    @app.get("/api/trials")
    def trials() -> dict:
        return runtime.trials_out()

    @app.get("/api/trials/export.json")
    def trials_json() -> Response:
        return Response(
            content=runtime.trials.to_json(),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="neuroshift_trials.json"'},
        )

    @app.get("/api/trials/export.csv")
    def trials_csv() -> Response:
        return Response(
            content=runtime.trials.to_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="neuroshift_trials.csv"'},
        )

    @app.post("/api/trials/mark")
    async def trials_mark(body: dict) -> dict:
        label = str(body.get("label") or body.get("note") or "pilot_block")
        result = runtime.mark_trial_block(label)
        await runtime.broadcast({"type": "trial_mark", **result})
        return result

    @app.get("/api/report.html")
    def session_report() -> Response:
        path = runtime.build_session_report()
        return FileResponse(
            path,
            media_type="text/html",
            filename="neuroshift_session_report.html",
        )

    @app.post("/api/calibrate")
    async def calibrate() -> dict:
        result = runtime.calibrate_gaze()
        await runtime.broadcast({"type": "calibrated", **result})
        return result

    @app.get("/api/eval")
    def eval_state() -> dict:
        return runtime.cued_out()

    @app.post("/api/eval/start")
    async def eval_start(body: dict | None = None) -> dict:
        device_id = (body or {}).get("device_id")
        result = runtime.start_cued_trial(device_id)
        await runtime.broadcast({"type": "cue_started", **result})
        return result

    @app.post("/api/eval/skip")
    async def eval_skip() -> dict:
        result = runtime.skip_cued_trial()
        await runtime.broadcast({"type": "cue_skipped", **result})
        return result

    @app.post("/api/eval/reset")
    async def eval_reset() -> dict:
        result = runtime.reset_cued_trials()
        await runtime.broadcast({"type": "cue_reset", **result})
        return result

    @app.get("/api/eval/export.csv")
    def eval_csv() -> Response:
        return Response(
            content=runtime.cued.to_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="neuroshift_cued_trials.csv"'},
        )

    @app.get("/api/eval/export.json")
    def eval_json() -> Response:
        return Response(
            content=runtime.cued.to_json(),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="neuroshift_cued_trials.json"'},
        )

    @app.get("/app.apk")
    def android_apk() -> Response:
        """Sideload target: open this URL on the phone to install the app."""
        apk = Path(__file__).resolve().parents[3] / "dist-mobile" / "MyoGaze.apk"
        if not apk.exists():
            from fastapi import HTTPException

            raise HTTPException(
                status_code=404,
                detail="No APK built yet — run 'npm run android:apk' in web/",
            )
        return FileResponse(
            apk,
            media_type="application/vnd.android.package-archive",
            filename="MyoGaze.apk",
        )

    @app.get("/iphone")
    def iphone_setup() -> FileResponse:
        page = Path(__file__).resolve().parent / "iphone.html"
        return FileResponse(page, media_type="text/html")

    def _lamp_raw_dir() -> Path:
        return Path(__file__).resolve().parents[3] / "datasets" / "lamp" / "raw"

    def _safe_raw_image(name: str) -> Path | None:
        raw = _lamp_raw_dir()
        path = (raw / Path(name).name).resolve()
        try:
            path.relative_to(raw.resolve())
        except ValueError:
            return None
        if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            return None
        return path

    def _yolo_to_box(txt: Path, width: int, height: int) -> dict | None:
        if not txt.exists():
            return None
        line = txt.read_text(encoding="utf-8").strip().splitlines()
        if not line:
            return None
        parts = line[0].split()
        if len(parts) < 5:
            return None
        _, cx, cy, bw, bh = (float(p) for p in parts[:5])
        return {
            "x0": (cx - bw / 2.0) * width,
            "y0": (cy - bh / 2.0) * height,
            "x1": (cx + bw / 2.0) * width,
            "y1": (cy + bh / 2.0) * height,
        }

    def _box_to_yolo(box: dict | None, width: int, height: int) -> str:
        if not box or width < 1 or height < 1:
            return ""
        x0, y0, x1, y1 = (float(box[k]) for k in ("x0", "y0", "x1", "y1"))
        if x1 - x0 < 4 or y1 - y0 < 4:
            return ""
        cx = ((x0 + x1) / 2.0) / width
        cy = ((y0 + y1) / 2.0) / height
        bw = (x1 - x0) / width
        bh = (y1 - y0) / height
        return f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n"

    @app.get("/label")
    def label_lamp_page() -> FileResponse:
        page = Path(__file__).resolve().parent / "label.html"
        return FileResponse(page, media_type="text/html")

    @app.get("/api/label/list")
    def label_list() -> dict:
        raw = _lamp_raw_dir()
        raw.mkdir(parents=True, exist_ok=True)
        names = sorted(
            p.name
            for p in raw.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        )
        start = 0
        for idx, name in enumerate(names):
            txt = (raw / name).with_suffix(".txt")
            if not txt.is_file() or not txt.read_text(encoding="utf-8").strip():
                start = idx
                break
        return {"images": names, "start": start}

    @app.get("/api/label/image/{name}")
    def label_image(name: str) -> FileResponse:
        path = _safe_raw_image(name)
        if path is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Image not found")
        media = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        return FileResponse(path, media_type=media)

    @app.get("/api/label/box/{name}")
    def label_box_get(name: str) -> dict:
        path = _safe_raw_image(name)
        if path is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Image not found")
        import cv2

        im = cv2.imread(str(path))
        if im is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Image not found")
        h, w = im.shape[:2]
        box = _yolo_to_box(path.with_suffix(".txt"), w, h)
        return {"name": path.name, "width": w, "height": h, "box": box}

    @app.put("/api/label/box/{name}")
    def label_box_put(name: str, body: dict) -> dict:
        path = _safe_raw_image(name)
        if path is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Image not found")
        import cv2

        im = cv2.imread(str(path))
        if im is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Image not found")
        h, w = im.shape[:2]
        txt = path.with_suffix(".txt")
        txt.write_text(_box_to_yolo(body.get("box"), w, h), encoding="utf-8")
        return {"ok": True, "name": path.name}

    @app.get("/myogaze.cer")
    def iphone_cert() -> Response:
        from ..devcert import ca_cer_path

        cer = ca_cer_path()
        if not cer.exists():
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Certificate not generated yet")
        return FileResponse(
            cer,
            media_type="application/x-x509-ca-cert",
            filename="myogaze.cer",
            headers={"Content-Disposition": "attachment; filename=myogaze.cer"},
        )

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()

        async def send_event(event: dict) -> None:
            await ws.send_text(json.dumps(event))

        runtime.subscribe(send_event)
        try:
            await ws.send_text(
                json.dumps(
                    {
                        "type": "hello",
                        "payload": runtime.status(__version__).model_dump(),
                    }
                )
            )
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                cmd = msg.get("cmd")
                if cmd == "camera_frame":
                    runtime.push_remote_frame(str(msg.get("jpeg_b64") or ""))
                elif cmd == "start_demo":
                    await runtime.start_demo(
                        prefer=msg.get("mode"),
                        camera=msg.get("camera"),
                    )
                elif cmd == "stop_demo":
                    await runtime.stop_demo()
                elif cmd == "confirm":
                    runtime.pulse_confirm()
                    await runtime.broadcast({"type": "confirm_pulse"})
                elif cmd == "detect_mode":
                    result = runtime.set_detect_mode(str(msg.get("mode", "objects")))
                    await runtime.broadcast({"type": "detect_mode", **result})
                elif cmd == "reset":
                    runtime.reset_session()
                    await runtime.broadcast(
                        {
                            "type": "session_reset",
                            "payload": runtime.status(__version__).model_dump(),
                        }
                    )
                elif cmd == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
        except WebSocketDisconnect:
            pass
        finally:
            runtime.unsubscribe(send_event)

    # Serve built PWA if present (after API routes)
    web_dist = Path(__file__).resolve().parents[3] / "web" / "dist"
    if web_dist.exists():
        assets = web_dist / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(web_dist / "index.html")

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str) -> FileResponse:
            blocked = ("api/", "docs", "openapi.json", "redoc", "ws", "iphone", "label", "myogaze.cer")
            if full_path.startswith(blocked) or full_path in {
                "docs",
                "redoc",
                "openapi.json",
            }:
                from fastapi import HTTPException

                raise HTTPException(status_code=404)
            candidate = web_dist / full_path
            if candidate.exists() and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(web_dist / "index.html")

    return app


app = create_app()
