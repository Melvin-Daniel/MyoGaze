"""Toggle lamp (M1) and fan (M2) over USB serial — run after wiring ESP32.

Usage (ESP32 on COM4, server closed or share port carefully):
  python scripts/test_hub_relays.py
  python scripts/test_hub_relays.py --port COM4 --device fan
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Test ESP32 relay hub over serial")
    parser.add_argument("--port", default="", help="COM port (default: config hub_serial_port)")
    parser.add_argument("--device", choices=("lamp", "fan"), default="lamp")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    port = (args.port or "").strip()
    if not port:
        sys.path.insert(0, str(ROOT))
        from src.neuroshift.config import load_config

        port = (load_config().hub_serial_port or "").strip()
    if not port:
        print("Set hub_serial_port in config/default.yaml or pass --port COM4")
        return 1

    try:
        import serial
    except ImportError:
        print("pip install pyserial")
        return 1

    ser = serial.Serial(port, args.baud, timeout=0.5)
    time.sleep(1.5)
    ser.reset_input_buffer()

    def send(device: str, command: str) -> None:
        line = json.dumps({"device_id": device, "command": command}) + "\n"
        ser.write(line.encode("utf-8"))
        ser.flush()
        print(f"Sent: {line.strip()}")
        time.sleep(0.8)
        while ser.in_waiting:
            print("Hub:", ser.readline().decode("utf-8", errors="replace").strip())

    print(f"Port {port} — testing {args.device} ON then OFF (Ctrl+C to abort)")
    send(args.device, "ON")
    time.sleep(2)
    send(args.device, "OFF")
    ser.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
