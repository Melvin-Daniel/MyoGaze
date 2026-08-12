"""FastAPI application — NeuroShift Control App backend."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .. import __version__
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


def create_app() -> FastAPI:
    app = FastAPI(
        title="NeuroShift Control App",
        version=__version__,
        description="Gaze-selected, EMG-confirmed smart-home intention — product API",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthOut)
    def health() -> HealthOut:
        return HealthOut(version=__version__)

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
        result = await runtime.start_demo(prefer=prefer)
        return DemoStartOut(
            started=result["started"],
            message=result["message"],
            mode=result.get("mode"),
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
                if cmd == "start_demo":
                    await runtime.start_demo(prefer=msg.get("mode"))
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
            blocked = ("api/", "docs", "openapi.json", "redoc", "ws")
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
