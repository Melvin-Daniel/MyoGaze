"""EMG confirmation source — keyboard / mouse sim now, serial hardware later."""

from __future__ import annotations

import time
from typing import Any

from .config import Config, DEFAULT


class EmgSource:
    """Returns volition score in [0, 1]."""

    def __init__(self, cfg: Config = DEFAULT):
        self.cfg = cfg
        self._held = False
        self._pulse_until = 0.0
        self._space_down = False
        self._mouse_score = 0.0
        self._serial: Any = None
        self._last_hardware = 0.0
        if cfg.emg_mode == "hardware":
            self._open_serial()

    def set_mode(self, mode: str) -> str:
        mode = mode.lower().strip()
        if mode not in {"keyboard", "mouse", "hardware"}:
            raise ValueError(f"Unknown emg_mode: {mode}")
        if self.cfg.emg_mode == "hardware" and mode != "hardware":
            self._close_serial()
        self.cfg.emg_mode = mode
        self.clear()
        if mode == "hardware":
            self._open_serial()
        return mode

    def _open_serial(self) -> None:
        try:
            import serial  # type: ignore

            self._serial = serial.Serial(
                self.cfg.emg_serial_port,
                self.cfg.emg_serial_baud,
                timeout=0.01,
            )
            print(
                f"[emg] serial open {self.cfg.emg_serial_port} "
                f"@ {self.cfg.emg_serial_baud}"
            )
        except Exception as exc:  # noqa: BLE001
            self._serial = None
            print(f"[emg] serial unavailable ({exc}) — staying at 0.0")

    def _close_serial(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:  # noqa: BLE001
                pass
            self._serial = None

    def poll(self, key: int = -1, mouse_y_norm: float | None = None) -> float:
        """
        Call each frame.

        mouse_y_norm: 0 = top of window (high effort), 1 = bottom (low),
        only used when emg_mode=mouse.
        """
        if self.cfg.emg_mode == "keyboard":
            return self._poll_keyboard(key)

        if self.cfg.emg_mode == "mouse":
            # Optional SPACE still works as a hard confirm pulse
            pulse = self._poll_keyboard(key)
            if pulse >= self.cfg.emg_confirm_threshold:
                return pulse
            if mouse_y_norm is not None:
                # Invert: move mouse UP = stronger "muscle" effort
                y = max(0.0, min(1.0, float(mouse_y_norm)))
                self._mouse_score = max(0.0, min(1.0, 1.0 - y))
            return self._mouse_score

        if self.cfg.emg_mode == "hardware":
            return self._poll_hardware()

        return 0.0

    def _poll_keyboard(self, key: int) -> float:
        space = key in (32, ord(" "))
        clear = key in (ord("x"), ord("X"))

        if clear:
            self._held = False
            self._pulse_until = 0.0
            self._space_down = False
            return 0.0

        # Rising edge of SPACE → one-shot confirm pulse
        if space and not self._space_down:
            self._pulse_until = time.time() + (self.cfg.emg_pulse_ms / 1000.0)
        self._space_down = space

        if time.time() < self._pulse_until:
            return 1.0
        return 0.0

    def _poll_hardware(self) -> float:
        """
        Expect lines like: EMG:0.73   or a bare float 0.73
        (ESP32 sketch can print MyoWare envelope normalized to 0..1)
        """
        if self._serial is None:
            return 0.0
        try:
            while self._serial.in_waiting:
                line = self._serial.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                if ":" in line:
                    line = line.split(":")[-1].strip()
                try:
                    self._last_hardware = max(0.0, min(1.0, float(line)))
                except ValueError:
                    continue
        except Exception:  # noqa: BLE001
            return self._last_hardware
        return self._last_hardware

    def clear(self) -> None:
        """Force clear after a successful ACT (ready for next confirm)."""
        self._pulse_until = 0.0
        self._held = False
        self._mouse_score = 0.0

    def confirmed(self, score: float) -> bool:
        return score >= self.cfg.emg_confirm_threshold

    def close(self) -> None:
        self._close_serial()
