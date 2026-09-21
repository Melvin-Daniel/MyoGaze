"""API schemas for the NeuroShift Control App."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DeviceOut(BaseModel):
    id: str
    label: str
    is_on: bool = False
    toggle_count: int = 0


class DecisionOut(BaseModel):
    ts: str | None = None
    action: str
    selected_device: str | None = None
    selected_label: str | None = None
    reason: str
    yaw: float | None = None
    emg: float | None = None


class SessionOut(BaseModel):
    acts: int = 0
    abstains: int = 0
    actuations: int = 0
    emg_without_gaze: int = 0
    gaze_without_emg: int = 0
    far_proxy: float = 0.0
    act_rate: float = 0.0
    abstain_rate: float = 0.0
    started_at: str | None = None
    ended_at: str | None = None
    note: str | None = None


class SettingsIn(BaseModel):
    dwell_seconds: float | None = Field(default=None, ge=0.2, le=3.0)
    yaw_side_threshold: float | None = Field(default=None, ge=0.05, le=0.6)
    emg_confirm_threshold: float | None = Field(default=None, ge=0.1, le=0.95)
    act_cooldown_seconds: float | None = Field(default=None, ge=0.2, le=3.0)
    mqtt_enabled: bool | None = None
    mqtt_host: str | None = None
    emg_mode: Literal["keyboard", "mouse", "hardware", "script"] | None = None
    emg_serial_port: str | None = None
    pipeline_mode: Literal["live", "mock"] | None = None
    camera_index: int | None = Field(default=None, ge=0, le=10)
    dwell_required: bool | None = None


class SettingsOut(BaseModel):
    product_name: str = "NeuroShift"
    dwell_seconds: float
    dwell_required: bool = True
    dwell_actuates: bool = True
    yaw_side_threshold: float
    emg_confirm_threshold: float
    act_cooldown_seconds: float
    mqtt_enabled: bool
    mqtt_host: str
    emg_mode: str
    emg_serial_port: str
    pipeline_mode: str = "live"
    camera_index: int = 0
    camera_ok: bool | None = None
    principle: str = "Look at a device for two seconds to toggle it. Unsure → Abstain."


class StatusOut(BaseModel):
    ok: bool = True
    version: str
    mode: str = "live"
    principle: str
    devices: list[DeviceOut]
    last_decision: DecisionOut | None = None
    session: SessionOut
    demo_running: bool = False
    camera_ok: bool | None = None
    camera_message: str | None = None
    detect_mode: str = "objects"
    dwell_required: bool = True
    dwell_actuates: bool = True
    iphone_setup_url: str | None = None
    android_apk_url: str | None = None


class DemoStartOut(BaseModel):
    started: bool
    message: str
    mode: str | None = None
    camera: str | None = None


class DemoStartIn(BaseModel):
    mode: Literal["live", "mock"] | None = None
    camera: Literal["local", "remote"] | None = None


class HealthOut(BaseModel):
    status: str = "ok"
    service: str = "neuroshift"
    version: str


class CameraStatusOut(BaseModel):
    ok: bool
    message: str
    index: int = 0
