"""Offline unit tests — no camera / no MediaPipe required."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.neuroshift.aliases import appliance_label
from src.neuroshift.config import apply_overrides, load_config, DEFAULT
from src.neuroshift.devices import select_by_yaw
from src.neuroshift.fusion import IntentionFusion
from src.neuroshift.demo import run_mock_demo
from src.neuroshift.report import build_report


class TestFusion(unittest.TestCase):
    def test_two_factor_gate(self):
        f = IntentionFusion(DEFAULT)
        self.assertEqual(f.decide("lamp", 0.9, 1.0, True).action, "ACT")
        self.assertEqual(f.decide("lamp", 0.9, 0.0, False).action, "ABSTAIN")
        self.assertEqual(f.decide(None, 0.9, 1.0, True).action, "ABSTAIN")


class TestHysteresis(unittest.TestCase):
    def test_sticky_lamp(self):
        d = select_by_yaw(-0.15, side_threshold=0.20, hysteresis=0.10, current_id="lamp")
        self.assertEqual(d.device_id, "lamp")
        d2 = select_by_yaw(-0.05, side_threshold=0.20, hysteresis=0.10, current_id="lamp")
        self.assertEqual(d2.device_id, "fan")


class TestAliases(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(appliance_label("bottle"), "Lamp")
        self.assertEqual(appliance_label("cup"), "Fan")


class TestConfig(unittest.TestCase):
    def test_load_yaml(self):
        cfg = load_config(ROOT / "config" / "default.yaml")
        self.assertEqual(cfg.product_name, "NeuroShift")
        self.assertGreater(cfg.dwell_seconds, 0)
        cfg2 = apply_overrides(cfg, {"emg_mode": "mouse"})
        self.assertEqual(cfg2.emg_mode, "mouse")


class TestMockProduct(unittest.TestCase):
    def test_mock_demo_and_report(self):
        out = ROOT / "logs" / "test_out"
        out.mkdir(parents=True, exist_ok=True)
        cfg = apply_overrides(DEFAULT, {"mock_fps": 10, "mock_write_video": False})
        result = run_mock_demo(cfg, show_window=False, write_video=False, out_dir=out)
        self.assertTrue(Path(result["session"]).exists())
        self.assertTrue(Path(result["decisions"]).exists())
        session = json.loads(Path(result["session"]).read_text(encoding="utf-8"))
        self.assertGreaterEqual(session["acts"], 1)
        self.assertGreaterEqual(session["actuations"], 1)
        self.assertGreaterEqual(session["abstains"], 1)
        report = build_report(
            session_path=Path(result["session"]),
            decisions_path=Path(result["decisions"]),
            out_path=out / "report.html",
        )
        self.assertTrue(report.exists())
        html = report.read_text(encoding="utf-8")
        self.assertIn("NeuroShift", html)
        self.assertIn("ACT", html)


if __name__ == "__main__":
    unittest.main()
