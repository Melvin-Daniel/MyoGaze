"""Install MyoGaze Control App as a Windows logon task so it runs whenever this laptop is on."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_NAME = "MyoGaze Control App"
STARTER = ROOT / "scripts" / "start_myogaze.cmd"


def _python() -> Path:
    exe = Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")
    # Keep python.exe so uvicorn logs still land in server.log via the cmd wrapper.
    return exe if exe.exists() else pyw


def write_starter() -> None:
    python = _python()
    STARTER.write_text(
        "\r\n".join(
            [
                "@echo off",
                f'cd /d "{ROOT}"',
                "if not exist logs mkdir logs",
                f'"{python}" -m src.neuroshift serve --host 0.0.0.0 --port 8000 >> logs\\server.log 2>&1',
                "",
            ]
        ),
        encoding="utf-8",
    )


def install() -> int:
    write_starter()
    startup = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup.mkdir(parents=True, exist_ok=True)
    shortcut = startup / "MyoGaze Control App.cmd"
    shortcut.write_text(STARTER.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Startup shortcut: {shortcut}")

    create = [
        "schtasks",
        "/Create",
        "/TN",
        TASK_NAME,
        "/TR",
        str(STARTER),
        "/SC",
        "ONLOGON",
        "/RL",
        "LIMITED",
        "/F",
    ]
    result = subprocess.run(create, capture_output=True, text=True)
    extra = (result.stdout or result.stderr or "").strip()
    if extra:
        print(extra)
    if result.returncode != 0:
        print("Scheduled task not registered (needs user permission). Startup folder shortcut is enough.")
        return 0
    print(f"Registered '{TASK_NAME}' to start at logon.")
    return 0


if __name__ == "__main__":
    raise SystemExit(install())
