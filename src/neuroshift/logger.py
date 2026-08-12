"""Append-only decision log for later FAR / intention analysis."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class DecisionLogger:
    def __init__(self, path: Path | None = None):
        root = Path(__file__).resolve().parents[2]
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = path or (root / "logs" / f"decisions_{stamp}.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._last_key: tuple | None = None

    def log(self, payload: dict) -> None:
        key = (
            payload.get("action"),
            payload.get("selected_device"),
            payload.get("reason"),
        )
        # Log on state change only (keeps file small)
        if key == self._last_key:
            return
        self._last_key = key
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
