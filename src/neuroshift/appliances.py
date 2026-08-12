"""Virtual appliance / relay state — toggles only on ACT rising edges."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ApplianceState:
    device_id: str
    label: str
    is_on: bool = False
    toggle_count: int = 0


@dataclass
class ActuationEvent:
    device_id: str
    label: str
    new_state: bool
    command: str  # "ON" | "OFF"


class ApplianceHub:
    """Simulates ESP32 relay hub until hardware arrives."""

    def __init__(self):
        self.devices: dict[str, ApplianceState] = {}
        self._prev_act_key: tuple[str | None, str] | None = None

    def ensure(self, device_id: str, label: str) -> ApplianceState:
        if device_id not in self.devices:
            self.devices[device_id] = ApplianceState(device_id=device_id, label=label)
        else:
            self.devices[device_id].label = label
        return self.devices[device_id]

    def on_decision(
        self,
        action: str,
        device_id: str | None,
        label: str | None,
    ) -> ActuationEvent | None:
        """
        Edge-triggered: toggle only when we newly enter ACT for a device.
        Holding SPACE must not spam toggles every frame.
        """
        key = (device_id, action)
        if action != "ACT" or not device_id:
            self._prev_act_key = key
            return None

        if self._prev_act_key == key:
            return None
        self._prev_act_key = key

        state = self.ensure(device_id, label or device_id)
        state.is_on = not state.is_on
        state.toggle_count += 1
        return ActuationEvent(
            device_id=device_id,
            label=state.label,
            new_state=state.is_on,
            command="ON" if state.is_on else "OFF",
        )

    def snapshot(self) -> list[ApplianceState]:
        return list(self.devices.values())
