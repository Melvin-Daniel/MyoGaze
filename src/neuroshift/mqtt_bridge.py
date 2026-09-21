"""MQTT publisher — reconnects; falls back to print if broker/library missing."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class MqttConfig:
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 1883
    topic_decision: str = "neuroshift/decision"
    topic_actuate: str = "neuroshift/actuate"
    client_id: str = "neuroshift-phase1"
    hub_serial_port: str = ""
    hub_serial_baud: int = 115200


class DecisionPublisher:
    def __init__(self, cfg: MqttConfig | None = None):
        self.cfg = cfg or MqttConfig()
        self._client = None
        self._serial = None
        self.mode = "print"
        self.connected = False
        self._open_hub_serial()

        if not self.cfg.enabled:
            return

        try:
            import paho.mqtt.client as mqtt

            kwargs = {"client_id": self.cfg.client_id}
            if hasattr(mqtt, "CallbackAPIVersion"):
                kwargs["callback_api_version"] = mqtt.CallbackAPIVersion.VERSION2
            self._client = mqtt.Client(**kwargs)
            self._client.reconnect_delay_set(min_delay=1, max_delay=15)
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.connect_async(self.cfg.host, self.cfg.port, keepalive=30)
            self._client.loop_start()
            self.mode = "mqtt"
            print(f"[mqtt] connecting {self.cfg.host}:{self.cfg.port}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[mqtt] unavailable ({exc}) — using print publisher", flush=True)
            self._client = None
            self.mode = "print"

    def _open_hub_serial(self) -> None:
        port = (self.cfg.hub_serial_port or "").strip()
        if not port:
            return
        try:
            import serial

            if self._serial is not None:
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None

            ser = serial.Serial()
            ser.port = port
            ser.baudrate = int(self.cfg.hub_serial_baud or 115200)
            ser.timeout = 0.05
            ser.write_timeout = 0.4
            ser.dsrdtr = False
            ser.rtscts = False
            ser.open()
            time.sleep(1.6)
            try:
                ser.reset_input_buffer()
            except Exception:
                pass
            self._serial = ser
            print(f"[hub] serial {port} @ {ser.baudrate}", flush=True)
        except Exception as exc:  # noqa: BLE001
            self._serial = None
            print(f"[hub] serial unavailable ({exc})", flush=True)

    def _write_hub_command(self, command: str) -> bool:
        """Send ON/OFF to the USB hub. Re-open COM port once if the handle went stale."""
        line = f"{command}\n".encode("utf-8")
        for attempt in range(2):
            if self._serial is None:
                self._open_hub_serial()
            if self._serial is None:
                return False
            try:
                self._serial.write(line)
                self._serial.flush()
                print(f"[hub] serial actuate {command}", flush=True)
                return True
            except Exception as exc:  # noqa: BLE001
                print(f"[hub] serial write failed ({exc})", flush=True)
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None
                if attempt == 0:
                    time.sleep(0.4)
        return False

    def _on_connect(self, *args) -> None:  # noqa: ANN002
        rc = args[3] if len(args) >= 4 else (args[0] if args else None)
        ok = rc == 0 or getattr(rc, "value", rc) == 0
        self.connected = bool(ok)
        if ok:
            print(f"[mqtt] connected {self.cfg.host}:{self.cfg.port}", flush=True)
        else:
            print(f"[mqtt] connect failed rc={rc} host={self.cfg.host}:{self.cfg.port}", flush=True)

    def _on_disconnect(self, *args) -> None:  # noqa: ANN002
        self.connected = False
        print("[mqtt] disconnected — will retry", flush=True)

    def publish_decision(self, payload: dict) -> None:
        body = {"ts": datetime.now(timezone.utc).isoformat(), **payload}
        self._send(self.cfg.topic_decision, body)

    def publish_actuate(self, payload: dict) -> None:
        body = {"ts": datetime.now(timezone.utc).isoformat(), **payload}
        self._send(self.cfg.topic_actuate, body)

    def _send(self, topic: str, body: dict) -> None:
        text = json.dumps(body)
        if topic.endswith("actuate"):
            command = str(body.get("command") or "").upper()
            if command not in {"ON", "OFF"}:
                command = "ON" if body.get("state") else "OFF"
            wrote = self._write_hub_command(command)
            if not wrote and self._serial is None and self._client is None:
                print(f"[actuate] {text}", flush=True)
        if self._client is not None:
            info = self._client.publish(topic, text, qos=1, retain=False)
            if not self.connected:
                print(
                    f"[mqtt] not connected; queued {topic} {text}",
                    flush=True,
                )
            elif getattr(info, "rc", 0) != 0:
                print(f"[mqtt] publish rc={info.rc} {topic} {text}", flush=True)
            elif topic.endswith("actuate"):
                print(f"[mqtt] actuate {text}", flush=True)

    def close(self) -> None:
        self.connected = False
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
