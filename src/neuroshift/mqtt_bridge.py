"""MQTT publisher stub — prints locally if broker/library unavailable."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class MqttConfig:
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 1883
    topic_decision: str = "neuroshift/decision"
    topic_actuate: str = "neuroshift/actuate"
    client_id: str = "neuroshift-phase0"


class DecisionPublisher:
    def __init__(self, cfg: MqttConfig | None = None):
        self.cfg = cfg or MqttConfig()
        self._client = None
        self.mode = "print"

        if not self.cfg.enabled:
            return

        try:
            import paho.mqtt.client as mqtt

            self._client = mqtt.Client(client_id=self.cfg.client_id)
            self._client.connect(self.cfg.host, self.cfg.port, keepalive=30)
            self._client.loop_start()
            self.mode = "mqtt"
            print(f"[mqtt] connected {self.cfg.host}:{self.cfg.port}")
        except Exception as exc:  # noqa: BLE001
            print(f"[mqtt] unavailable ({exc}) — using print publisher")
            self._client = None
            self.mode = "print"

    def publish_decision(self, payload: dict) -> None:
        body = {"ts": datetime.now(timezone.utc).isoformat(), **payload}
        self._send(self.cfg.topic_decision, body)

    def publish_actuate(self, payload: dict) -> None:
        body = {"ts": datetime.now(timezone.utc).isoformat(), **payload}
        self._send(self.cfg.topic_actuate, body)

    def _send(self, topic: str, body: dict) -> None:
        text = json.dumps(body)
        if self._client is not None:
            self._client.publish(topic, text, qos=0)
        else:
            # Quiet local stub — only actuate lines are noisy enough to print
            if topic.endswith("actuate"):
                print(f"[actuate] {text}")

    def close(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
