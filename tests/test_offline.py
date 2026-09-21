"""Offline unit tests — no camera / no MediaPipe required."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.neuroshift.aliases import appliance_label, relay_id_for
from src.neuroshift.appliances import ApplianceHub
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
    def test_honest_display_names(self):
        self.assertEqual(appliance_label("bottle"), "Bottle")
        self.assertEqual(appliance_label("cup"), "Lamp")
        self.assertEqual(appliance_label("cell phone"), "Phone")
        self.assertEqual(appliance_label("fan"), "Fan")
        self.assertEqual(appliance_label("cooling fan"), "Fan")
        self.assertEqual(appliance_label("lamp"), "Lamp")

    def test_relay_mapping(self):
        self.assertEqual(relay_id_for("lamp", "Lamp"), "lamp")
        self.assertEqual(relay_id_for("bottle_1", "Bottle"), "lamp")
        self.assertEqual(relay_id_for("cup_2", "Cup"), "lamp")
        self.assertEqual(relay_id_for("cell phone_1", "Phone"), "plug")
        self.assertEqual(relay_id_for("fan_1", "Fan"), "fan")


class TestHubRelay(unittest.TestCase):
    def test_yolo_act_drives_slot_relay(self):
        hub = ApplianceHub()
        hub.ensure("lamp", "Lamp")
        event = hub.on_decision("ACT", "bottle_1", "Bottle")
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.device_id, "lamp")
        self.assertEqual(event.command, "ON")
        self.assertTrue(hub.devices["lamp"].is_on)


class TestDwellMode(unittest.TestCase):
    def test_instant_gaze_selects_without_wait(self):
        from src.neuroshift.engine import IntentionEngine
        from src.neuroshift.gaze import GazeEstimate

        cfg = apply_overrides(DEFAULT, {"dwell_required": False, "dwell_seconds": 0.55})
        engine = IntentionEngine(cfg=cfg)
        g = GazeEstimate(face_found=True, yaw=-0.4, pitch=0.0, confidence=0.9, nose_xy=(200, 240))
        result = engine.tick(g, [], prefer_detections=False, frame_w=640, frame_h=480, now=1.0)
        self.assertIsNotNone(result.selected)
        self.assertEqual(result.dwell_progress, 1.0)

    def test_hot_patch_updates_running_engine(self):
        from src.neuroshift.api.state import AppRuntime
        from src.neuroshift.engine import IntentionEngine
        from src.neuroshift.gaze import GazeEstimate

        rt = AppRuntime()
        engine = IntentionEngine(cfg=apply_overrides(rt.cfg, {}))
        rt._engine = engine
        self.assertTrue(engine.cfg.dwell_required)
        rt.set_dwell_required(False)
        self.assertFalse(rt.cfg.dwell_required)
        self.assertFalse(engine.cfg.dwell_required)
        g = GazeEstimate(face_found=True, yaw=-0.4, pitch=0.0, confidence=0.9, nose_xy=(200, 240))
        result = engine.tick(g, [], prefer_detections=False, frame_w=640, frame_h=480, now=2.0)
        self.assertIsNotNone(result.selected)

    def test_two_second_look_toggles_without_confirm(self):
        from src.neuroshift.engine import IntentionEngine
        from src.neuroshift.gaze import GazeEstimate

        cfg = apply_overrides(
            DEFAULT,
            {
                "dwell_required": True,
                "dwell_seconds": 2.0,
                "dwell_actuates": True,
                "act_cooldown_seconds": 0.4,
            },
        )
        engine = IntentionEngine(cfg=cfg)
        g = GazeEstimate(face_found=True, yaw=-0.4, pitch=0.0, confidence=0.9, nose_xy=(200, 240))
        start = engine.tick(
            g, [], prefer_detections=False, frame_w=640, frame_h=480, now=1.0, emg_score_override=0.0
        )
        self.assertIsNone(start.actuation)
        self.assertLess(start.dwell_progress, 1.0)
        on = engine.tick(
            g, [], prefer_detections=False, frame_w=640, frame_h=480, now=3.05, emg_score_override=0.0
        )
        self.assertIsNotNone(on.actuation)
        assert on.actuation is not None
        self.assertEqual(on.actuation.command, "ON")
        still = engine.tick(
            g, [], prefer_detections=False, frame_w=640, frame_h=480, now=3.2, emg_score_override=0.0
        )
        self.assertIsNone(still.actuation)
        kept = engine.tick(
            g, [], prefer_detections=False, frame_w=640, frame_h=480, now=8.0, emg_score_override=0.0
        )
        self.assertIsNone(kept.actuation)
        away = GazeEstimate(face_found=True, yaw=0.45, pitch=0.0, confidence=0.9, nose_xy=(440, 240))
        engine.tick(
            away, [], prefer_detections=False, frame_w=640, frame_h=480, now=8.1, emg_score_override=0.0
        )
        engine.tick(
            away, [], prefer_detections=False, frame_w=640, frame_h=480, now=8.7, emg_score_override=0.0
        )
        engine.reset_gaze_state()
        begin = engine.tick(
            g, [], prefer_detections=False, frame_w=640, frame_h=480, now=8.8, emg_score_override=0.0
        )
        self.assertIsNone(begin.actuation)
        self.assertLess(begin.dwell_progress, 1.0)
        off = engine.tick(
            g, [], prefer_detections=False, frame_w=640, frame_h=480, now=10.85, emg_score_override=0.0
        )
        self.assertIsNotNone(off.actuation)
        assert off.actuation is not None
        self.assertEqual(off.actuation.command, "OFF")


class TestTrials(unittest.TestCase):
    def test_csv_export(self):
        from src.neuroshift.trials import TrialLog

        log = TrialLog()
        log.log_confirm(dwell_required=True, detect_mode="slots")
        log.log_decision(
            action="ACT",
            device_id="lamp",
            label="Lamp",
            reason="gaze_selected_and_emg_confirmed",
            dwell_progress=1.0,
            dwell_required=True,
            detect_mode="slots",
        )
        log.log_marker(note="block_A_dwell_gated", dwell_required=True, detect_mode="slots")
        self.assertIn("trial_id", log.to_csv())
        self.assertEqual(log.summary()["confirms"], 1)
        self.assertEqual(log.summary()["markers"], 1)

    def test_trials_report(self):
        from src.neuroshift.report import build_trials_report
        from src.neuroshift.trials import TrialLog

        log = TrialLog()
        log.log_confirm(dwell_required=True, detect_mode="slots")
        log.log_decision(
            action="ACT",
            device_id="fan",
            label="Fan",
            reason="gaze_selected_and_emg_confirmed",
            dwell_progress=1.0,
            dwell_required=True,
            detect_mode="slots",
        )
        out = ROOT / "logs" / "test_out" / "trials_report.html"
        path = build_trials_report(
            trials=log,
            session={"far_proxy": 0.0, "actuations": 1},
            out_path=out,
        )
        self.assertTrue(path.exists())
        html = path.read_text(encoding="utf-8")
        self.assertIn("MyoGaze", html)
        self.assertIn("ACT", html)


class TestCuedTrials(unittest.TestCase):
    def _runner(self):
        from src.neuroshift.evaluation import CuedTrialRunner

        return CuedTrialRunner(seed=1)

    def test_hit_wrong_and_miss_are_scored(self):
        r = self._runner()
        r.start(device_id="lamp", now=0.0)
        r.on_actuation(device_id="lamp", label="Lamp", now=1.5)

        r.start(device_id="fan", now=2.0)
        r.on_actuation(device_id="plug", label="Plug", now=3.0)

        r.start(device_id="plug", now=4.0)
        r.skip(now=5.0)

        s = r.summary()
        self.assertEqual(s["trials"], 3)
        self.assertEqual((s["hits"], s["wrong"], s["misses"]), (1, 1, 1))
        self.assertAlmostEqual(s["accuracy"], 1 / 3, places=3)
        self.assertAlmostEqual(s["false_activation_rate"], 1 / 3, places=3)

    def test_latency_measured_only_for_hits(self):
        r = self._runner()
        r.start(device_id="lamp", now=10.0)
        trial = r.on_actuation(device_id="lamp", label="Lamp", now=12.25)
        assert trial is not None
        self.assertEqual(trial.outcome, "HIT")
        self.assertAlmostEqual(trial.latency_s, 2.25, places=3)
        self.assertEqual(r.summary()["latency_s"]["median"], 2.25)

    def test_timeout_closes_trial_as_miss(self):
        from src.neuroshift.evaluation import CuedTrialRunner

        r = CuedTrialRunner(timeout_s=5.0, seed=2)
        r.start(device_id="fan", now=0.0)
        self.assertIsNone(r.check_timeout(now=4.9))
        trial = r.check_timeout(now=5.1)
        assert trial is not None
        self.assertEqual(trial.outcome, "MISS")
        self.assertIsNone(r.active)

    def test_starting_over_an_open_trial_records_a_miss(self):
        r = self._runner()
        r.start(device_id="lamp", now=0.0)
        r.start(device_id="fan", now=1.0)
        self.assertEqual(r.trials[0].outcome, "MISS")
        self.assertEqual(len(r.trials), 2)

    def test_actuation_outside_a_trial_is_not_scored(self):
        r = self._runner()
        self.assertIsNone(r.on_actuation(device_id="lamp", label="Lamp", now=1.0))
        self.assertEqual(r.summary()["trials"], 0)

    def test_cue_never_repeats_back_to_back(self):
        r = self._runner()
        prev = None
        for i in range(12):
            t = r.start(now=float(i))
            self.assertNotEqual(t.cued_device_id, prev)
            prev = t.cued_device_id
            r.skip(now=float(i) + 0.5)

    def test_condition_breakdown_splits_dwell_and_instant(self):
        r = self._runner()
        r.start(device_id="lamp", dwell_required=True, now=0.0)
        r.on_actuation(device_id="lamp", label="Lamp", now=1.0)
        r.start(device_id="fan", dwell_required=False, now=2.0)
        r.on_actuation(device_id="plug", label="Plug", now=3.0)

        by = r.summary()["by_condition"]
        self.assertEqual(by["dwell_gated"]["accuracy"], 1.0)
        self.assertEqual(by["instant_gaze"]["false_activation_rate"], 1.0)

    def test_csv_export_has_cue_and_outcome(self):
        r = self._runner()
        r.start(device_id="lamp", now=0.0)
        r.on_actuation(device_id="lamp", label="Lamp", now=1.0)
        csv_text = r.to_csv()
        self.assertIn("cued_device_id", csv_text)
        self.assertIn("outcome", csv_text)
        self.assertIn("HIT", csv_text)

    def test_empty_summary_is_safe(self):
        s = self._runner().summary()
        self.assertEqual(s["trials"], 0)
        self.assertEqual(s["accuracy"], 0.0)
        self.assertIsNone(s["latency_s"]["median"])


class TestCuedTrialRuntime(unittest.TestCase):
    """The scoring hook lives in AppRuntime._record_tick_result, so exercise it
    through the same path the live session uses."""

    def _runtime(self):
        from src.neuroshift.api.state import AppRuntime

        return AppRuntime()

    def _tick(self, *, actuated: str | None):
        from src.neuroshift.appliances import ActuationEvent
        from src.neuroshift.api.schemas import DecisionOut

        class _Result:
            changed = False
            dwell_progress = 1.0
            actuation = (
                ActuationEvent(device_id=actuated, label=actuated.title(), new_state=True, command="ON")
                if actuated
                else None
            )

        decision = DecisionOut(
            action="ACT" if actuated else "ABSTAIN",
            selected_device=actuated,
            selected_label=actuated.title() if actuated else None,
            reason="test",
            yaw=0.0,
            emg=1.0,
        )
        return _Result(), decision

    def test_actuation_during_cue_is_scored_as_hit(self):
        rt = self._runtime()
        rt.start_cued_trial("lamp")
        result, decision = self._tick(actuated="lamp")
        rt._record_tick_result(result, decision)

        summary = rt.cued.summary()
        self.assertEqual(summary["hits"], 1)
        self.assertEqual(summary["accuracy"], 1.0)
        self.assertIsNone(rt.cued.active)

    def test_wrong_appliance_counts_as_false_activation(self):
        rt = self._runtime()
        rt.start_cued_trial("lamp")
        result, decision = self._tick(actuated="fan")
        rt._record_tick_result(result, decision)

        summary = rt.cued.summary()
        self.assertEqual(summary["wrong"], 1)
        self.assertEqual(summary["false_activation_rate"], 1.0)

    def test_free_play_actuation_is_not_scored(self):
        rt = self._runtime()
        result, decision = self._tick(actuated="lamp")
        rt._record_tick_result(result, decision)
        self.assertEqual(rt.cued.summary()["trials"], 0)

    def test_reset_session_clears_cued_trials(self):
        rt = self._runtime()
        rt.start_cued_trial("lamp")
        result, decision = self._tick(actuated="lamp")
        rt._record_tick_result(result, decision)
        rt.reset_session()
        self.assertEqual(rt.cued.summary()["trials"], 0)

    def test_cue_records_the_current_dwell_condition(self):
        rt = self._runtime()
        rt.set_dwell_required(False)
        rt.start_cued_trial("plug")
        result, decision = self._tick(actuated="plug")
        rt._record_tick_result(result, decision)
        self.assertIn("instant_gaze", rt.cued.summary()["by_condition"])


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


class TestFusionAmbiguity(unittest.TestCase):
    def test_ambiguous_gaze_always_abstains(self):
        f = IntentionFusion(DEFAULT)
        d = f.decide("lamp", 0.9, 1.0, True, ambiguous=True)
        self.assertEqual(d.action, "ABSTAIN")
        self.assertEqual(d.reason, "ambiguous_gaze_targets")
        self.assertIsNone(d.selected_device)


class TestGazeCombine(unittest.TestCase):
    def test_combine_look_uses_head_when_eyes_are_weak(self):
        from src.neuroshift.gaze import _combine_look

        agreed = _combine_look(0.32, 0.18, 0.55)
        self.assertGreater(agreed, 0.22)
        headed = _combine_look(0.34, 0.04, 0.55)
        self.assertGreater(headed, 0.20)
        glance = _combine_look(0.02, 0.40, 0.82)
        self.assertGreater(glance, 0.28)


class TestSelectorAmbiguity(unittest.TestCase):
    def test_two_close_objects_are_ambiguous(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        left = DetectedObject("bottle_1", "bottle", 0.9, (360, 140, 520, 320), "Bottle")
        right = DetectedObject("bottle_2", "bottle", 0.9, (430, 140, 600, 320), "Bottle")
        g = GazeEstimate(True, (480, 230), 0.40, 0.12, 0.9, aim_xy=(480, 230))
        target = select_target(
            g, [left, right], 640, 480, 0.2, prefer_detections=True, ambiguity_margin=0.20
        )
        self.assertIsNotNone(target)
        assert target is not None
        self.assertTrue(target.ambiguous)

    def test_lone_object_is_not_ambiguous(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        bottle = DetectedObject("bottle_1", "bottle", 0.9, (160, 140, 250, 280), "Bottle")
        looking = GazeEstimate(True, (200, 210), -0.29, 0.05, 0.9)
        target = select_target(looking, [bottle], 640, 480, 0.2, prefer_detections=True)
        self.assertIsNotNone(target)
        assert target is not None
        self.assertFalse(target.ambiguous)
        at_camera = GazeEstimate(True, (320, 200), 0.0, 0.0, 0.9)
        self.assertIsNone(
            select_target(
                at_camera, [bottle], 640, 480, 0.2, prefer_detections=True, allow_slots=False
            )
        )

    def test_objects_mode_does_not_invent_fan_or_plug(self):
        from src.neuroshift.engine import IntentionEngine
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        center = GazeEstimate(True, (320, 240), 0.0, 0.0, 0.9)
        right = GazeEstimate(True, (500, 240), 0.55, 0.0, 0.9)
        self.assertIsNone(
            select_target(center, [], 640, 480, 0.2, prefer_detections=True, allow_slots=False)
        )
        self.assertIsNone(
            select_target(right, [], 640, 480, 0.2, prefer_detections=True, allow_slots=False)
        )
        slotted = select_target(center, [], 640, 480, 0.2, prefer_detections=True, allow_slots=True)
        self.assertIsNotNone(slotted)
        assert slotted is not None
        self.assertEqual(slotted.target_id, "fan")
        self.assertEqual(slotted.kind, "slot")

        cfg = apply_overrides(DEFAULT, {"dwell_required": False})
        engine = IntentionEngine(cfg=cfg)
        result = engine.tick(
            center,
            [],
            prefer_detections=True,
            frame_w=640,
            frame_h=480,
            allow_slots=False,
            now=1.0,
        )
        self.assertIsNone(result.candidate)
        self.assertIsNone(result.selected)

    def test_looking_at_the_camera_does_not_lock_a_ceiling_lamp(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        lamp = DetectedObject("lamp_1", "lamp", 0.8, (180, 0, 520, 220), "Lamp")
        at_camera = GazeEstimate(True, (320, 180), 0.02, -0.08, 0.9, aim_xy=(320, 200))
        self.assertIsNone(
            select_target(at_camera, [lamp], 640, 480, 0.2, prefer_detections=True, allow_slots=False)
        )
        looking_up = GazeEstimate(True, (340, 80), 0.05, -0.62, 0.9, aim_xy=(340, 90))
        locked = select_target(looking_up, [lamp], 640, 480, 0.2, prefer_detections=True, allow_slots=False)
        self.assertIsNotNone(locked)
        assert locked is not None
        self.assertEqual(locked.label, "Lamp")

        held = DetectedObject("fan_1", "fan", 0.86, (250, 160, 390, 300), "Fan")
        looking_at_fan = GazeEstimate(True, (320, 220), 0.02, -0.04, 0.9, aim_xy=(320, 230))
        found = select_target(
            looking_at_fan, [lamp, held], 640, 480, 0.2, prefer_detections=True, allow_slots=False
        )
        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.label, "Fan")

    def test_looking_at_the_camera_does_not_lock_a_mirror_lamp(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.selector import box_on_face, drop_boxes_on_face, select_target
        from src.neuroshift.types import GazeEstimate

        oval = (320.0, 200.0, 90.0, 110.0)
        wardrobe = DetectedObject("lamp_w", "lamp", 0.7, (30, 20, 380, 430), "Lamp")
        held = DetectedObject("lamp_h", "lamp", 0.9, (470, 140, 575, 290), "Lamp")
        self.assertTrue(box_on_face(wardrobe.xyxy, oval))
        self.assertFalse(box_on_face(held.xyxy, oval))
        kept = drop_boxes_on_face([wardrobe, held], oval)
        self.assertEqual([item.obj_id for item in kept], ["lamp_h"])

        at_camera = GazeEstimate(
            True, (320, 200), 0.0, 0.0, 0.9, aim_xy=(320, 200), face_oval=oval
        )
        self.assertIsNone(
            select_target(
                at_camera, kept, 640, 480, 0.2, prefer_detections=True, allow_slots=False
            )
        )
        looking_right = GazeEstimate(
            True, (320, 200), 0.42, 0.0, 0.9, eye_xy=(320, 200), aim_xy=(522.0, 215.0), face_oval=oval
        )
        locked = select_target(
            looking_right, kept, 640, 480, 0.2, prefer_detections=True, allow_slots=False
        )
        self.assertIsNotNone(locked)
        assert locked is not None
        self.assertEqual(locked.target_id, "lamp_h")

    def test_chest_badge_is_not_the_lamp(self):
        from src.neuroshift.detector import DetectedObject, _keep_held_appliances, _on_torso
        from src.neuroshift.selector import box_on_body, drop_boxes_on_face, keep_lamp_detections, select_target
        from src.neuroshift.types import GazeEstimate

        # Head-only person box — the lanyard sits below it, which used to look like a lamp.
        head = (250, 60, 400, 230)
        badge = (300, 280, 355, 345)
        side_lamp = (480, 140, 575, 290)
        self.assertTrue(_on_torso(badge, [head]))
        self.assertFalse(_on_torso(side_lamp, [head]))
        kept = _keep_held_appliances(
            [("lamp", 0.80, badge), ("lamp", 0.86, side_lamp)], [head], 640, 480
        )
        lamps = [item for item in kept if item[0] == "lamp"]
        self.assertEqual(len(lamps), 1)
        self.assertEqual(lamps[0][2], side_lamp)

        oval = (325.0, 145.0, 75.0, 85.0)
        on_chest = DetectedObject("lamp_badge", "lamp", 0.7, badge, "Lamp")
        beside = DetectedObject("lamp_side", "lamp", 0.9, side_lamp, "Lamp")
        phone = DetectedObject("phone_1", "cell phone", 0.9, (230, 235, 470, 400), "Phone")
        self.assertTrue(box_on_body(badge, oval))
        self.assertFalse(box_on_body(side_lamp, oval))
        dropped = drop_boxes_on_face([on_chest, beside], oval)
        self.assertEqual([item.obj_id for item in dropped], ["lamp_side"])
        self.assertEqual(
            [item.obj_id for item in keep_lamp_detections([beside, phone])],
            ["lamp_side"],
        )

        looking_down = GazeEstimate(
            True, (325, 145), 0.0, 0.35, 0.9, aim_xy=(327, 312), face_oval=oval
        )
        self.assertIsNone(
            select_target(
                looking_down,
                drop_boxes_on_face([on_chest], oval),
                640,
                480,
                0.2,
                prefer_detections=True,
                allow_slots=False,
            )
        )
        looking_right = GazeEstimate(
            True, (325, 145), 0.42, 0.0, 0.9, eye_xy=(325, 145), face_oval=oval
        )
        locked = select_target(
            looking_right, dropped, 640, 480, 0.2, prefer_detections=True, allow_slots=False
        )
        self.assertIsNotNone(locked)
        assert locked is not None
        self.assertEqual(locked.target_id, "lamp_side")

    def test_offset_lanyard_is_not_the_lamp(self):
        """A badge hanging off the shoulder used to sit outside the face column."""
        from src.neuroshift.detector import DetectedObject, _on_torso
        from src.neuroshift.selector import box_on_body, drop_boxes_on_face, drop_lamps_on_people, select_target
        from src.neuroshift.types import GazeEstimate

        head = (250, 60, 400, 230)
        oval = (325.0, 145.0, 75.0, 85.0)
        # Past the old 1.45*face_rx gate (~109px), still on the shoulder.
        lanyard = (418, 305, 478, 375)
        shoulder = (390, 300, 450, 365)
        side_lamp = (480, 140, 575, 290)
        self.assertTrue(box_on_body(lanyard, oval))
        self.assertTrue(box_on_body(shoulder, oval))
        self.assertFalse(box_on_body(side_lamp, oval))
        self.assertTrue(_on_torso(shoulder, [head]))
        self.assertFalse(_on_torso(side_lamp, [head]))

        on_strap = DetectedObject("lamp_strap", "lamp", 0.7, lanyard, "Lamp")
        on_face = DetectedObject("lamp_face", "lamp", 0.7, (280, 80, 360, 160), "Lamp")
        beside = DetectedObject("lamp_side", "lamp", 0.9, side_lamp, "Lamp")
        dropped = drop_boxes_on_face([on_strap, beside], oval)
        self.assertEqual([item.obj_id for item in dropped], ["lamp_side"])
        self.assertEqual(
            [item.obj_id for item in drop_lamps_on_people([on_face, beside], [head])],
            ["lamp_side"],
        )
        looking_down = GazeEstimate(
            True, (325, 145), 0.0, 0.35, 0.9, aim_xy=(448, 340), face_oval=oval
        )
        self.assertIsNone(
            select_target(
                looking_down,
                drop_boxes_on_face([on_strap], oval),
                640,
                480,
                0.2,
                prefer_detections=True,
                allow_slots=False,
            )
        )

    def test_rectangular_badge_is_not_a_bulb(self):
        import cv2
        import numpy as np

        from src.neuroshift.detector import find_led_bulbs, looks_like_led_bulb

        frame = np.full((480, 640, 3), 50, np.uint8)
        cv2.rectangle(frame, (300, 280), (360, 350), (240, 240, 240), -1)
        badge = (290, 270, 370, 360)
        self.assertFalse(looks_like_led_bulb(frame, badge))
        self.assertEqual(find_led_bulbs(frame, [(250, 60, 400, 430)]), [])

    def test_chest_highlight_is_not_a_lamp(self):
        import cv2
        import numpy as np

        from src.neuroshift.detector import find_led_bulbs

        frame = np.full((480, 640, 3), 50, np.uint8)
        cv2.circle(frame, (325, 310), 28, (235, 235, 235), -1)
        people = [(250, 60, 400, 430)]
        self.assertEqual(find_led_bulbs(frame, people), [])

    def test_floral_shirt_is_not_the_lamp(self):
        from pathlib import Path

        import cv2

        from src.neuroshift.detector import find_led_bulbs

        path = Path(__file__).resolve().parents[1] / "assets" / "shirt_print_not_lamp.png"
        frame = cv2.imread(str(path))
        self.assertIsNotNone(frame)
        h, w = frame.shape[:2]
        people = [(int(w * 0.05), int(h * 0.02), int(w * 0.72), h - 2)]
        self.assertEqual(find_led_bulbs(frame, people), [])
        self.assertEqual(find_led_bulbs(frame, []), [])

    def test_phone_on_the_camera_axis_locks(self):
        """A phone held in front of the face sits just under the projected aim.

        Neutral aim is y = h*(0.42+0.38*pitch), which lands in the empty wall
        above the phone. That is still a look at the phone. The same look must
        not lock a ceiling lamp whose box only clips that point.
        """
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        # Screenshot geometry on a 640x480 frame: phone under the aim, large
        # enough that the small-box `near` shortcut does not apply.
        phone = DetectedObject("phone_1", "cell phone", 0.91, (230, 235, 470, 400), "Phone")
        at_camera = GazeEstimate(True, (320, 190), 0.02, -0.04, 0.9)
        locked = select_target(
            at_camera, [phone], 640, 480, 0.2, prefer_detections=True, allow_slots=False
        )
        self.assertIsNotNone(locked)
        assert locked is not None
        self.assertEqual(locked.label, "Phone")
        self.assertFalse(locked.ambiguous)

        lamp = DetectedObject("lamp_1", "lamp", 0.8, (180, 0, 520, 220), "Lamp")
        self.assertIsNone(
            select_target(
                at_camera, [lamp], 640, 480, 0.2, prefer_detections=True, allow_slots=False
            )
        )
        both = select_target(
            at_camera, [lamp, phone], 640, 480, 0.2, prefer_detections=True, allow_slots=False
        )
        self.assertIsNotNone(both)
        assert both is not None
        self.assertEqual(both.label, "Phone")
        self.assertFalse(both.ambiguous)

    def test_eye_aim_hits_the_object_not_the_face(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.gaze import aim_from_eyes
        from src.neuroshift.selector import box_on_face, drop_boxes_on_face, select_target
        from src.neuroshift.types import GazeEstimate

        eyes = (280.0, 180.0)
        aim = aim_from_eyes(eyes, 0.55, 0.05, 640, 480)
        self.assertGreater(aim[0], eyes[0] + 40)
        face = DetectedObject("fan_face", "fan", 0.8, (190, 70, 370, 290), "Fan")
        fan = DetectedObject("fan_1", "fan", 0.9, (430, 150, 560, 290), "Fan")
        oval = (280.0, 180.0, 100.0, 120.0)
        self.assertTrue(box_on_face(face.xyxy, oval))
        self.assertFalse(box_on_face(fan.xyxy, oval))
        kept = drop_boxes_on_face([face, fan], oval)
        self.assertEqual([item.obj_id for item in kept], ["fan_1"])

        looking = GazeEstimate(True, eyes, 0.55, 0.05, 0.9, aim_xy=aim)
        target = select_target(
            looking, [face, fan], 640, 480, 0.2, prefer_detections=True, allow_slots=False
        )
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.target_id, "fan_1")
        self.assertFalse(target.ambiguous)

    def test_a_short_glance_still_reaches_the_held_fan(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        eyes = (250.0, 200.0)
        # Short aim stops on the face. The fan is held to the right of it.
        short = (250.0 + 0.12 * 0.52 * 640, 200.0)
        fan = DetectedObject("fan_1", "fan", 0.9, (420, 90, 560, 240), "Fan")
        self.assertLess(short[0], fan.xyxy[0])
        looking = GazeEstimate(True, eyes, 0.12, -0.08, 0.9, eye_xy=eyes, aim_xy=short)
        target = select_target(
            looking, [fan], 640, 480, 0.2, prefer_detections=True, allow_slots=False
        )
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.target_id, "fan_1")
        straight = GazeEstimate(True, eyes, 0.0, 0.0, 0.9, eye_xy=eyes, aim_xy=eyes)
        self.assertIsNone(
            select_target(straight, [fan], 640, 480, 0.2, prefer_detections=True, allow_slots=False)
        )

    def test_mirrored_head_yaw_follows_the_image(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.gaze import align_head_to_image
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        # Matrix yaw is flipped after the webcam mirror. The nose in the picture is the truth.
        yaw, pitch = align_head_to_image(-0.55, -0.2, 0.4, 0.1)
        self.assertGreater(yaw, 0.4)
        self.assertGreater(pitch, 0)
        same, _ = align_head_to_image(0.4, 0.0, 0.3, 0.0)
        self.assertGreater(same, 0)

        eyes = (320.0, 200.0)
        right = DetectedObject("fan_r", "fan", 0.9, (470, 120, 600, 270), "Fan")
        left = DetectedObject("fan_l", "fan", 0.9, (40, 120, 170, 270), "Fan")
        glance_right = GazeEstimate(True, eyes, 0.42, 0.0, 0.9, eye_xy=eyes)
        glance_left = GazeEstimate(True, eyes, -0.42, 0.0, 0.9, eye_xy=eyes)
        hit_r = select_target(glance_right, [right], 640, 480, 0.2, prefer_detections=True, allow_slots=False)
        hit_l = select_target(glance_left, [left], 640, 480, 0.2, prefer_detections=True, allow_slots=False)
        self.assertIsNotNone(hit_r)
        self.assertIsNotNone(hit_l)
        assert hit_r is not None and hit_l is not None
        self.assertEqual(hit_r.target_id, "fan_r")
        self.assertEqual(hit_l.target_id, "fan_l")

    def test_a_modest_glance_at_a_side_object_starts_a_look(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        eyes = (360.0, 220.0)
        fan = DetectedObject("fan_1", "fan", 0.9, (80, 70, 230, 230), "Fan")
        looking = GazeEstimate(True, eyes, -0.16, -0.02, 0.9, eye_xy=eyes)
        target = select_target(
            looking, [fan], 640, 480, 0.2, prefer_detections=True, allow_slots=False
        )
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.target_id, "fan_1")
        self.assertFalse(target.ambiguous)

    def test_looking_at_the_real_object_not_the_preview_still_hits(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        # Eyes look sideways at the fan in the room. In the camera picture the
        # fan sits lower than that glance, so a screen-tuned ray would miss.
        eyes = (320.0, 160.0)
        fan = DetectedObject("fan_1", "fan", 0.9, (470, 280, 610, 430), "Fan")
        looking = GazeEstimate(True, eyes, 0.28, 0.0, 0.9, eye_xy=eyes)
        target = select_target(
            looking, [fan], 640, 480, 0.2, prefer_detections=True, allow_slots=False
        )
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.target_id, "fan_1")
        straight = GazeEstimate(True, eyes, 0.0, 0.0, 0.9, eye_xy=eyes)
        self.assertIsNone(
            select_target(straight, [fan], 640, 480, 0.2, prefer_detections=True, allow_slots=False)
        )

    def test_world_look_hits_a_side_object_the_ray_would_miss(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        eyes = (320.0, 180.0)
        oval = (320.0, 180.0, 90.0, 110.0)
        fan = DetectedObject("fan_1", "fan", 0.9, (470, 300, 610, 450), "Fan")
        looking = GazeEstimate(
            True, eyes, 0.0, 0.0, 0.9,
            eye_yaw=0.40, eye_pitch=0.02, has_iris=True, eye_xy=eyes, face_oval=oval,
        )
        target = select_target(
            looking, [fan], 640, 480, 0.2, prefer_detections=True, allow_slots=False
        )
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.target_id, "fan_1")
        self.assertFalse(target.ambiguous)

    def test_looking_at_the_camera_does_not_lock_a_side_fan(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        eyes = (320.0, 180.0)
        oval = (320.0, 180.0, 90.0, 110.0)
        fan = DetectedObject("fan_1", "fan", 0.9, (470, 120, 600, 270), "Fan")
        at_camera = GazeEstimate(
            True, eyes, 0.0, 0.0, 0.9,
            eye_yaw=0.02, eye_pitch=0.01, has_iris=True, eye_xy=eyes, face_oval=oval,
        )
        self.assertIsNone(
            select_target(at_camera, [fan], 640, 480, 0.2, prefer_detections=True, allow_slots=False)
        )

    def test_lamp_locks_only_when_gaze_is_on_the_box(self):
        """A head turn toward the lamp side must not toggle — aim must sit on the box."""
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        eyes = (320.0, 200.0)
        oval = (320.0, 200.0, 80.0, 90.0)
        lamp = DetectedObject("lamp_1", "lamp", 0.9, (470, 200, 580, 340), "Lamp")
        # Looking left/right of the lamp but not at it.
        glance = GazeEstimate(
            True, eyes, 0.35, 0.0, 0.9,
            eye_xy=eyes, aim_xy=(200.0, 200.0), face_oval=oval,
        )
        self.assertIsNone(
            select_target(glance, [lamp], 640, 480, 0.2, prefer_detections=True, allow_slots=False)
        )
        # Eyes / aim on the green lamp box.
        on_lamp = GazeEstimate(
            True, eyes, 0.22, 0.05, 0.9,
            eye_xy=eyes, aim_xy=(525.0, 270.0), face_oval=oval,
        )
        hit = select_target(
            on_lamp, [lamp], 640, 480, 0.2, prefer_detections=True, allow_slots=False
        )
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit.target_id, "lamp_1")

    def test_look_away_freezes_dwell_instead_of_finishing(self):
        from src.neuroshift.config import Config
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.engine import IntentionEngine
        from src.neuroshift.types import GazeEstimate

        cfg = Config(dwell_seconds=1.0, dwell_required=True, dwell_actuates=True)
        eng = IntentionEngine(cfg=cfg)
        lamp = DetectedObject("lamp_1", "lamp", 0.9, (470, 200, 580, 340), "Lamp")
        eyes = (320.0, 200.0)
        on_lamp = GazeEstimate(
            True, eyes, 0.22, 0.05, 0.9, eye_xy=eyes, aim_xy=(525.0, 270.0)
        )
        away = GazeEstimate(
            True, eyes, 0.0, 0.0, 0.9, eye_xy=eyes, aim_xy=(160.0, 200.0)
        )
        t0 = 1000.0
        r1 = eng.tick(
            on_lamp, [lamp], prefer_detections=True, frame_w=640, frame_h=480,
            allow_slots=False, now=t0,
        )
        self.assertIsNotNone(r1.candidate)
        r2 = eng.tick(
            on_lamp, [lamp], prefer_detections=True, frame_w=640, frame_h=480,
            allow_slots=False, now=t0 + 0.60,
        )
        self.assertGreater(r2.dwell_progress, 0.5)
        r3 = eng.tick(
            away, [lamp], prefer_detections=True, frame_w=640, frame_h=480,
            allow_slots=False, now=t0 + 0.70,
        )
        frozen_at = r3.dwell_progress
        self.assertGreater(frozen_at, 0.5)
        self.assertIsNone(r3.selected)
        r4 = eng.tick(
            away, [lamp], prefer_detections=True, frame_w=640, frame_h=480,
            allow_slots=False, now=t0 + 0.95,
        )
        self.assertLessEqual(r4.dwell_progress, frozen_at + 0.01)
        self.assertIsNone(r4.selected)
        r5 = eng.tick(
            away, [lamp], prefer_detections=True, frame_w=640, frame_h=480,
            allow_slots=False, now=t0 + 1.20,
        )
        self.assertIsNone(r5.selected)

    def test_fan_template_beats_lamp_template(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        eyes = (320.0, 200.0)
        fan = DetectedObject("fan_1", "fan", 0.9, (470, 120, 600, 270), "Fan")
        lamp = DetectedObject("lamp_1", "lamp", 0.9, (40, 120, 170, 270), "Lamp")
        looking = GazeEstimate(
            True, eyes, 0.0, 0.0, 0.9,
            eye_yaw=0.32, eye_pitch=0.04, has_iris=True, eye_xy=eyes,
        )
        templates = {"fan": (0.35, 0.05), "lamp": (-0.35, 0.05)}
        target = select_target(
            looking,
            [fan, lamp],
            640,
            480,
            0.2,
            prefer_detections=True,
            allow_slots=False,
            look_templates=templates,
        )
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.target_id, "fan_1")
        self.assertFalse(target.ambiguous)

    def test_two_objects_on_the_same_side_are_ambiguous(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        eyes = (280.0, 200.0)
        oval = (280.0, 200.0, 90.0, 110.0)
        fan = DetectedObject("fan_1", "fan", 0.9, (470, 60, 600, 200), "Fan")
        bottle = DetectedObject("bottle_1", "bottle", 0.9, (480, 280, 610, 430), "Bottle")
        looking = GazeEstimate(
            True, eyes, 0.0, 0.0, 0.9,
            eye_yaw=0.36, eye_pitch=0.0, has_iris=True, eye_xy=eyes, face_oval=oval,
        )
        target = select_target(
            looking, [fan, bottle], 640, 480, 0.2, prefer_detections=True, allow_slots=False
        )
        self.assertIsNotNone(target)
        assert target is not None
        self.assertTrue(target.ambiguous)

    def test_overlapping_boxes_are_one_look(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        eyes = (250.0, 200.0)
        phone = DetectedObject("p", "cell phone", 0.8, (420, 80, 560, 250), "Phone")
        lamp = DetectedObject("l", "lamp", 0.7, (440, 110, 555, 230), "Lamp")
        looking = GazeEstimate(True, eyes, 0.35, -0.05, 0.9, eye_xy=eyes)
        target = select_target(
            looking, [phone, lamp], 640, 480, 0.2, prefer_detections=True, allow_slots=False
        )
        self.assertIsNotNone(target)
        assert target is not None
        self.assertFalse(target.ambiguous)

    def test_dwell_survives_one_dropped_frame(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.engine import IntentionEngine
        from src.neuroshift.types import GazeEstimate

        cfg = apply_overrides(DEFAULT, {"dwell_required": True, "dwell_seconds": 0.4})
        engine = IntentionEngine(cfg=cfg)
        fan = DetectedObject("fan_1", "fan", 0.9, (400, 140, 540, 290), "Fan")
        aim = (470.0, 215.0)
        gaze = GazeEstimate(True, (240, 180), 0.4, 0.0, 0.9, aim_xy=aim)
        engine.tick(
            gaze, [fan], prefer_detections=True, frame_w=640, frame_h=480, allow_slots=False, now=10.0
        )
        self.assertEqual(engine.dwell_id, "fan_1")
        missed = engine.tick(
            gaze, [], prefer_detections=True, frame_w=640, frame_h=480, allow_slots=False, now=10.05
        )
        self.assertEqual(engine.dwell_id, "fan_1")
        self.assertIsNone(missed.selected)
        locked = engine.tick(
            gaze, [fan], prefer_detections=True, frame_w=640, frame_h=480, allow_slots=False, now=10.45
        )
        self.assertIsNotNone(locked.selected)
        assert locked.selected is not None
        self.assertEqual(locked.selected.target_id, "fan_1")

    def test_dwell_keeps_going_when_lamp_id_changes(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.engine import IntentionEngine
        from src.neuroshift.types import GazeEstimate

        cfg = apply_overrides(DEFAULT, {"dwell_required": True, "dwell_seconds": 0.4})
        engine = IntentionEngine(cfg=cfg)
        eyes = (320.0, 200.0)
        oval = (320.0, 200.0, 90.0, 110.0)
        lamp_a = DetectedObject("lamp_1", "lamp", 0.9, (470, 140, 600, 300), "Lamp")
        lamp_b = DetectedObject("lamp_2", "lamp", 0.9, (480, 150, 610, 310), "Lamp")
        looking = GazeEstimate(
            True,
            eyes,
            0.22,
            0.0,
            0.9,
            eye_yaw=0.22,
            head_yaw=0.20,
            has_iris=True,
            eye_xy=eyes,
            aim_xy=(535.0, 225.0),
            face_oval=oval,
        )
        engine.tick(
            looking,
            [lamp_a],
            prefer_detections=True,
            frame_w=640,
            frame_h=480,
            allow_slots=False,
            now=1.0,
        )
        self.assertEqual(engine.dwell_id, "lamp_1")
        later = engine.tick(
            looking,
            [lamp_b],
            prefer_detections=True,
            frame_w=640,
            frame_h=480,
            allow_slots=False,
            now=1.45,
        )
        self.assertIsNotNone(later.selected)
        assert later.selected is not None
        self.assertEqual(later.selected.target_id, "lamp_2")

    def test_head_turn_toward_lamp_locks(self):
        from src.neuroshift.detector import DetectedObject
        from src.neuroshift.selector import select_target
        from src.neuroshift.types import GazeEstimate

        eyes = (320.0, 200.0)
        oval = (320.0, 200.0, 90.0, 110.0)
        lamp = DetectedObject("lamp_1", "lamp", 0.9, (470, 140, 600, 300), "Lamp")
        # Head turned toward the lamp side but aim not on the box — must not lock.
        turn_only = GazeEstimate(
            True,
            eyes,
            0.34,
            0.0,
            0.9,
            eye_yaw=0.07,
            head_yaw=0.34,
            has_iris=True,
            eye_xy=eyes,
            aim_xy=(200.0, 200.0),
            face_oval=oval,
        )
        self.assertIsNone(
            select_target(turn_only, [lamp], 640, 480, 0.2, prefer_detections=True, allow_slots=False)
        )
        # Aim on the lamp box — locks.
        looking = GazeEstimate(
            True,
            eyes,
            0.22,
            0.0,
            0.9,
            eye_yaw=0.22,
            head_yaw=0.20,
            has_iris=True,
            eye_xy=eyes,
            aim_xy=(535.0, 220.0),
            face_oval=oval,
        )
        target = select_target(
            looking, [lamp], 640, 480, 0.2, prefer_detections=True, allow_slots=False
        )
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.target_id, "lamp_1")
        at_camera = GazeEstimate(
            True,
            eyes,
            0.0,
            0.0,
            0.9,
            eye_yaw=0.02,
            head_yaw=0.02,
            has_iris=True,
            eye_xy=eyes,
            aim_xy=(320.0, 200.0),
            face_oval=oval,
        )
        self.assertIsNone(
            select_target(at_camera, [lamp], 640, 480, 0.2, prefer_detections=True, allow_slots=False)
        )


class TestDetectorPrune(unittest.TestCase):
    def test_drops_tiny_and_overlapping_boxes(self):
        from src.neuroshift.detector import ObjectDetector

        det = ObjectDetector.__new__(ObjectDetector)
        det.min_area_frac = 0.004
        det.max_area_frac = 0.70
        det.nms_iou = 0.55
        det.max_objects = 8
        raw = [
            ("bottle", 0.95, (0, 0, 2, 2)),
            ("lamp", 0.90, (40, 40, 240, 240)),
            ("lamp", 0.70, (50, 50, 230, 230)),
        ]
        kept = ObjectDetector._prune(det, raw, 640 * 480)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0][0], "lamp")
        self.assertAlmostEqual(kept[0][1], 0.90)


class TestPcFanShape(unittest.TestCase):
    def _paint_pc_fan(self, canvas, x, y, size=72):
        import math

        import cv2
        import numpy as np

        canvas[y : y + size, x : x + size] = (22, 22, 22)
        cx, cy = x + size // 2, y + size // 2
        r = int(size * 0.36)
        cv2.circle(canvas, (cx, cy), r, (78, 78, 78), -1)
        for a in range(0, 180, 18):
            rad = math.radians(a)
            x2 = int(cx + r * math.cos(rad))
            y2 = int(cy + r * math.sin(rad))
            cv2.line(canvas, (cx, cy), (x2, y2), (28, 28, 28), 2)
        cv2.circle(canvas, (cx, cy), 7, (36, 36, 36), -1)
        return (x, y, x + size, y + size)

    def test_black_square_grille_is_a_fan(self):
        import numpy as np

        from src.neuroshift.detector import find_cooling_fans, looks_like_pc_fan

        frame = np.full((240, 320, 3), 200, np.uint8)
        box = self._paint_pc_fan(frame, 120, 80, 72)
        self.assertTrue(looks_like_pc_fan(frame, box))
        found = find_cooling_fans(frame)
        self.assertGreaterEqual(len(found), 1)

    def test_tall_phone_box_on_a_fan_is_still_a_fan(self):
        import numpy as np

        from src.neuroshift.detector import _collapse_same_object, _fan_crop

        frame = np.full((320, 240, 3), 190, np.uint8)
        self._paint_pc_fan(frame, 140, 90, 70)
        tall = (130, 40, 220, 280)
        self.assertIsNotNone(_fan_crop(frame, tall))
        collapsed = _collapse_same_object(
            frame,
            [("cell phone", 0.7, tall), ("lamp", 0.6, (145, 95, 215, 175))],
        )
        self.assertEqual(len(collapsed), 1)
        self.assertEqual(collapsed[0][0], "fan")

    def test_wall_sized_lamp_box_is_dropped(self):
        import numpy as np

        from src.neuroshift.detector import _collapse_same_object

        frame = np.full((240, 320, 3), 180, np.uint8)
        wall = (0, 0, 310, 230)
        collapsed = _collapse_same_object(frame, [("lamp", 0.5, wall), ("fan", 0.4, wall)])
        self.assertEqual(collapsed, [])
        held = (80, 70, 160, 160)
        kept = _collapse_same_object(frame, [("lamp", 0.6, held), ("cell phone", 0.7, held)])
        self.assertEqual(len(kept), 1)
        self.assertIn(kept[0][0], {"lamp", "cell phone"})

    def test_bright_square_is_not_a_fan(self):
        import numpy as np

        from src.neuroshift.detector import looks_like_pc_fan

        frame = np.full((200, 200, 3), 230, np.uint8)
        self.assertFalse(looks_like_pc_fan(frame, (40, 40, 160, 160)))

    def test_plain_room_is_not_full_of_fans(self):
        import numpy as np

        from src.neuroshift.detector import find_cooling_fans

        frame = np.full((480, 640, 3), 160, np.uint8)
        frame[40:120, 80:200] = (40, 40, 40)
        frame[200:260, 300:380] = (90, 70, 50)
        self.assertEqual(find_cooling_fans(frame), [])

    def test_large_dark_panel_is_not_a_fan(self):
        import numpy as np

        from src.neuroshift.detector import find_cooling_fans, looks_like_pc_fan

        frame = np.full((480, 640, 3), 180, np.uint8)
        frame[40:400, 80:520] = (30, 30, 30)
        self.assertFalse(looks_like_pc_fan(frame, (80, 40, 520, 400)))
        self.assertEqual(find_cooling_fans(frame), [])

    def test_real_pc_fan_photo_is_found(self):
        from pathlib import Path

        import cv2
        import numpy as np

        from src.neuroshift.detector import find_cooling_fans, looks_like_pc_fan

        ref = Path(__file__).resolve().parents[1] / "assets" / "pc_fan_ref.png"
        fan = cv2.imread(str(ref))
        self.assertIsNotNone(fan)
        frame = np.full((480, 640, 3), 150, np.uint8)
        fh, fw = fan.shape[:2]
        scale = 0.55
        small = cv2.resize(fan, (int(fw * scale), int(fh * scale)))
        y, x = 160, 230
        sh, sw = small.shape[:2]
        frame[y : y + sh, x : x + sw] = small
        box = (x, y, x + sw, y + sh)
        self.assertTrue(looks_like_pc_fan(frame, box))
        found = find_cooling_fans(frame)
        self.assertGreaterEqual(len(found), 1)
        fx0, fy0, fx1, fy1 = found[0][0]
        cx, cy = (fx0 + fx1) / 2, (fy0 + fy1) / 2
        self.assertTrue(x - 40 <= cx <= x + sw + 40)
        self.assertTrue(y - 40 <= cy <= y + sh + 40)

    def test_fan_templates_include_held_user_and_ref(self):
        from src.neuroshift.detector import _fan_asset_files, _load_fan_templates

        names = [path.stem.lower() for path in _fan_asset_files()]
        self.assertIn("pc_fan_user", names)
        self.assertIn("pc_fan_held", names)
        self.assertIn("pc_fan_ref", names)
        self.assertGreaterEqual(len(_load_fan_templates()), 3)

    def test_every_user_fan_photo_is_found(self):
        from pathlib import Path

        import cv2

        from src.neuroshift.detector import _fan_asset_files, find_cooling_fans

        extras = [path for path in _fan_asset_files() if path.stem.lower() != "pc_fan_ref"]
        self.assertGreaterEqual(len(extras), 2)
        for path in extras:
            frame = cv2.imread(str(path))
            self.assertIsNotNone(frame, path.name)
            found = find_cooling_fans(frame)
            self.assertGreaterEqual(len(found), 1, path.name)

    def test_user_desk_fan_photo_is_found(self):
        from pathlib import Path

        import cv2

        from src.neuroshift.detector import find_cooling_fans

        path = Path(__file__).resolve().parents[1] / "assets" / "pc_fan_user.png"
        frame = cv2.imread(str(path))
        self.assertIsNotNone(frame)
        found = find_cooling_fans(frame)
        self.assertGreaterEqual(len(found), 1)
        x0, y0, x1, y1 = found[0][0]
        h, w = frame.shape[:2]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.assertTrue(w * 0.22 <= cx <= w * 0.72)
        self.assertTrue(h * 0.28 <= cy <= h * 0.68)

    def test_user_desk_fan_at_webcam_scale(self):
        from pathlib import Path

        import cv2
        import numpy as np

        from src.neuroshift.detector import ObjectDetector, find_cooling_fans

        path = Path(__file__).resolve().parents[1] / "assets" / "pc_fan_user.png"
        fan = cv2.imread(str(path))
        self.assertIsNotNone(fan)
        canvas = np.full((480, 640, 3), 18, np.uint8)
        placed = cv2.resize(fan, (220, 390))
        canvas[45 : 45 + 390, 210 : 210 + 220] = placed
        found = find_cooling_fans(canvas)
        self.assertGreaterEqual(len(found), 1)
        x0, y0, x1, y1 = found[0][0]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.assertTrue(210 <= cx <= 430)
        self.assertTrue(80 <= cy <= 400)

        det = ObjectDetector.__new__(ObjectDetector)
        det.conf = 0.12
        det.target_classes = {"fan", "lamp", "bottle"}
        det.every_n_frames = 1
        det.iou_match = 0.3
        det.imgsz = 512
        det.model_name = "none"
        det._frame_i = 0
        det._last = []
        det._next_id = 1
        det.min_area_frac = 0.003
        det.max_area_frac = 0.45
        det.nms_iou = 0.55
        det.max_objects = 6
        det.available = False
        det.model = None
        objects = det.detect(canvas)
        self.assertTrue(any(obj.label == "fan" for obj in objects))

    def test_held_webcam_fan_beats_a_person_box(self):
        from pathlib import Path

        import cv2

        from src.neuroshift.detector import find_cooling_fans

        path = Path(__file__).resolve().parents[1] / "assets" / "pc_fan_held.png"
        frame = cv2.imread(str(path))
        self.assertIsNotNone(frame)
        h, w = frame.shape[:2]
        found = find_cooling_fans(frame, people=[(0, 0, w, h)])
        self.assertGreaterEqual(len(found), 1)
        x0, y0, x1, y1 = found[0][0]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.assertGreater(cx, w * 0.48)
        self.assertTrue(h * 0.18 <= cy <= h * 0.90)
        self.assertGreater(x1 - x0, 30)

    def test_empty_room_is_not_a_fan(self):
        from pathlib import Path

        import cv2

        from src.neuroshift.detector import find_cooling_fans

        path = Path(__file__).resolve().parents[1] / "assets" / "no_fan_room.png"
        frame = cv2.imread(str(path))
        self.assertIsNotNone(frame)
        h, w = frame.shape[:2]
        self.assertEqual(find_cooling_fans(frame, people=[(0, 0, w, h)]), [])

    def test_clock_lookalike_promotes_to_fan_relay(self):
        self.assertEqual(relay_id_for("fan_3", "Fan"), "fan")

    def test_canonicalize_cooling_fan(self):
        from src.neuroshift.detector import canonicalize_label, _fan_on_person

        self.assertEqual(canonicalize_label("cooling fan"), "fan")
        self.assertEqual(canonicalize_label("PC cooling fan"), "fan")
        self.assertEqual(canonicalize_label("cell phone"), "cell phone")
        self.assertEqual(canonicalize_label("light bulb"), "lamp")
        self.assertTrue(_fan_on_person((40, 40, 80, 80), [(10, 10, 200, 200)]))
        self.assertFalse(_fan_on_person((400, 300, 460, 360), [(10, 10, 80, 80)]))


class TestLedBulbShape(unittest.TestCase):
    def _paint_bulb(self, canvas, x, y, r=36):
        import cv2

        cx, cy = x + r, y + r
        cv2.circle(canvas, (cx, cy), r, (236, 238, 240), -1)
        cv2.circle(canvas, (cx, cy), r, (210, 214, 218), 2)
        neck_w, neck_h = int(r * 0.55), int(r * 0.45)
        cv2.rectangle(
            canvas,
            (cx - neck_w // 2, cy + r - 4),
            (cx + neck_w // 2, cy + r + neck_h),
            (228, 230, 232),
            -1,
        )
        cap_w, cap_h = int(r * 0.42), int(r * 0.38)
        cv2.rectangle(
            canvas,
            (cx - cap_w // 2, cy + r + neck_h - 2),
            (cx + cap_w // 2, cy + r + neck_h + cap_h),
            (170, 172, 176),
            -1,
        )
        return (x, y, x + 2 * r, cy + r + neck_h + cap_h)

    def test_close_shown_bulb_beats_distant_glow(self):
        import cv2
        import numpy as np

        from src.neuroshift.detector import (
            ObjectDetector,
            _keep_held_appliances,
            find_led_bulbs,
            looks_like_led_bulb,
        )

        frame = np.full((480, 640, 3), 36, np.uint8)
        cv2.circle(frame, (520, 48), 14, (255, 255, 255), -1)
        cv2.circle(frame, (520, 48), 20, (248, 250, 255), 5)
        far = (500, 28, 540, 68)
        held = self._paint_bulb(frame, 240, 150, 70)
        self.assertTrue(looks_like_led_bulb(frame, held))
        found = find_led_bulbs(frame)
        self.assertGreaterEqual(len(found), 1)
        x0, y0, x1, y1 = found[0][0]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.assertGreater(cx, 180)
        self.assertLess(cx, 460)
        self.assertGreater(cy, 120)
        self.assertGreater((x1 - x0) * (y1 - y0), 90 * 90)

        kept = _keep_held_appliances(
            [("lamp", 0.92, far), ("lamp", 0.80, held)], [], 640, 480
        )
        self.assertEqual(kept[0][2], held)

        det = ObjectDetector.__new__(ObjectDetector)
        det.conf = 0.12
        det.target_classes = {"fan", "lamp"}
        det.every_n_frames = 1
        det.iou_match = 0.3
        det.imgsz = 512
        det.model_name = "none"
        det._frame_i = 0
        det._last = []
        det._next_id = 1
        det.min_area_frac = 0.003
        det.max_area_frac = 0.45
        det.nms_iou = 0.55
        det.max_objects = 6
        det.available = False
        det.model = None
        objects = det.detect(frame)
        lamps = [obj for obj in objects if obj.label == "lamp"]
        self.assertEqual(len(lamps), 1)
        lcx = (lamps[0].xyxy[0] + lamps[0].xyxy[2]) / 2
        self.assertGreater(lcx, 180)
        self.assertLess(lcx, 460)

    def test_held_bulb_beats_ceiling_light_next_to_a_person(self):
        """Live screenshot: ceiling fixture boxed, real LUKER in the hand ignored."""
        import cv2
        import numpy as np

        from src.neuroshift.detector import ObjectDetector, find_led_bulbs

        frame = np.full((480, 640, 3), 36, np.uint8)
        cv2.circle(frame, (430, 72), 16, (255, 255, 255), -1)
        cv2.circle(frame, (430, 72), 22, (250, 252, 255), 4)
        self._paint_bulb(frame, 430, 250, 52)
        people = [(70, 20, 400, 470)]
        found = find_led_bulbs(frame, people)
        self.assertGreaterEqual(len(found), 1)
        x0, y0, x1, y1 = found[0][0]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.assertGreater(cx, 400)
        self.assertGreater(cy, 220)

        det = ObjectDetector.__new__(ObjectDetector)
        det.conf = 0.12
        det.target_classes = {"fan", "lamp"}
        det.every_n_frames = 1
        det.iou_match = 0.3
        det.imgsz = 512
        det.model_name = "none"
        det._frame_i = 0
        det._last = []
        det._next_id = 1
        det.min_area_frac = 0.003
        det.max_area_frac = 0.45
        det.nms_iou = 0.55
        det.max_objects = 6
        det.available = False
        det.model = None
        det.last_people = people
        det._people_misses = 0
        objects = det.detect(frame)
        lamps = [obj for obj in objects if obj.label == "lamp"]
        self.assertEqual(len(lamps), 1)
        lcy = (lamps[0].xyxy[1] + lamps[0].xyxy[3]) / 2
        self.assertGreater(lcy, 220)

    def test_close_up_shown_bulb_is_kept(self):
        import numpy as np

        from src.neuroshift.detector import find_led_bulbs, looks_like_led_bulb

        frame = np.full((480, 640, 3), 40, np.uint8)
        box = self._paint_bulb(frame, 170, 20, 155)
        self.assertTrue(looks_like_led_bulb(frame, box))
        found = find_led_bulbs(frame)
        self.assertGreaterEqual(len(found), 1)
        x0, y0, x1, y1 = found[0][0]
        self.assertGreater((x1 - x0) * (y1 - y0) / (640 * 480), 0.16)

    def test_real_globe_is_found_anywhere_on_the_frame(self):
        """Close held globe — any screen position. Far room lights stay ignored."""
        import numpy as np

        from src.neuroshift.detector import DetectedObject, find_led_bulbs
        from src.neuroshift.selector import drop_boxes_on_face, drop_lamps_on_people

        people = [(180, 20, 420, 470)]
        oval = (300.0, 140.0, 80.0, 90.0)
        placements = ((20, 140), (460, 140), (20, 280), (460, 280), (250, 180))
        for x, y in placements:
            frame = np.full((480, 640, 3), 40, np.uint8)
            self._paint_bulb(frame, x, y, 64)
            found = find_led_bulbs(frame, people)
            self.assertGreaterEqual(len(found), 1, f"missed close bulb at {x},{y}")
            bx0, by0, bx1, by1 = found[0][0]
            cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
            self.assertGreater(cx, x)
            self.assertLess(cx, x + 180)
            self.assertGreater(cy, y)
            self.assertLess(cy, y + 200)
            det = DetectedObject("lamp_1", "lamp", found[0][1], found[0][0], "Lamp")
            after_people = drop_lamps_on_people([det], people, 640, 480)
            self.assertEqual(len(after_people), 1, f"person filter dropped globe at {x},{y}")
            after_face = drop_boxes_on_face(after_people, oval)
            self.assertEqual(len(after_face), 1, f"face filter dropped globe at {x},{y}")

        # Tiny far glare must not lock.
        far = np.full((480, 640, 3), 40, np.uint8)
        import cv2

        cv2.circle(far, (500, 40), 14, (255, 255, 255), -1)
        self.assertEqual(find_led_bulbs(far, people), [])

    def test_painted_globe_is_a_bulb(self):
        import numpy as np

        from src.neuroshift.detector import find_led_bulbs, looks_like_led_bulb

        frame = np.full((320, 240, 3), 40, np.uint8)
        box = self._paint_bulb(frame, 70, 50, 40)
        self.assertTrue(looks_like_led_bulb(frame, box))
        found = find_led_bulbs(frame)
        self.assertGreaterEqual(len(found), 1)

    def test_held_bulb_is_found_anywhere_in_the_frame(self):
        """A shown LUKER must lock in corners and in front of the body, not only the photo pose."""
        import numpy as np

        from src.neuroshift.detector import find_led_bulbs, looks_like_led_bulb

        people = [(220, 50, 430, 450)]
        # Top-left of the painted globe. r=52 is a close held lamp on 640x480.
        placements = (
            (18, 18),
            (500, 18),
            (18, 290),
            (500, 290),
            (250, 155),
            (18, 155),
            (500, 155),
        )
        for x, y in placements:
            frame = np.full((480, 640, 3), 36, np.uint8)
            box = self._paint_bulb(frame, x, y, 52)
            self.assertTrue(looks_like_led_bulb(frame, box), (x, y))
            found = find_led_bulbs(frame, people)
            self.assertGreaterEqual(len(found), 1, (x, y))
            fx0, fy0, fx1, fy1 = found[0][0]
            fcx, fcy = (fx0 + fx1) / 2, (fy0 + fy1) / 2
            expected_cx = x + 52
            expected_cy = y + 52
            self.assertLess(abs(fcx - expected_cx), 70, (x, y, fcx, fcy))
            self.assertLess(abs(fcy - expected_cy), 90, (x, y, fcx, fcy))

    def test_second_person_is_not_the_lamp(self):
        import cv2
        import numpy as np

        from src.neuroshift.detector import _on_any_head, find_led_bulbs, looks_like_led_bulb

        frame = np.full((480, 640, 3), 40, np.uint8)
        cv2.circle(frame, (120, 130), 38, (96, 130, 180), -1)
        box = self._paint_bulb(frame, 470, 140, 36)
        people = [(70, 50, 190, 420), (240, 40, 430, 460)]
        self.assertTrue(looks_like_led_bulb(frame, box))
        self.assertTrue(_on_any_head((90, 90, 150, 170), people))
        self.assertFalse(_on_any_head(box, people))
        found = find_led_bulbs(frame, people)
        self.assertGreaterEqual(len(found), 1)
        cx = (found[0][0][0] + found[0][0][2]) / 2
        self.assertGreater(cx, 400)

    def test_shown_bulb_in_front_of_person_is_found(self):
        import numpy as np

        from src.neuroshift.detector import (
            DetectedObject,
            _on_torso,
            find_led_bulbs,
            looks_like_led_bulb,
        )
        from src.neuroshift.selector import drop_boxes_on_face

        frame = np.full((480, 640, 3), 40, np.uint8)
        people = [(200, 40, 420, 460)]
        box = self._paint_bulb(frame, 250, 180, 58)
        self.assertTrue(looks_like_led_bulb(frame, box))
        self.assertFalse(_on_torso(box, people))
        found = find_led_bulbs(frame, people)
        self.assertGreaterEqual(len(found), 1)
        globe = DetectedObject("lamp_1", "lamp", 0.88, found[0][0], "Lamp")
        oval = (310.0, 120.0, 70.0, 80.0)
        kept = drop_boxes_on_face([globe], oval)
        self.assertEqual([item.obj_id for item in kept], ["lamp_1"])

    def test_open_cup_is_not_a_bulb(self):
        import cv2
        import numpy as np

        from src.neuroshift.detector import looks_like_led_bulb

        frame = np.full((240, 240, 3), 50, np.uint8)
        cv2.circle(frame, (120, 120), 50, (230, 230, 230), -1)
        cv2.circle(frame, (120, 120), 28, (40, 40, 40), -1)
        self.assertFalse(looks_like_led_bulb(frame, (60, 60, 180, 180)))

    def test_skin_is_not_a_bulb_or_fan(self):
        import cv2
        import numpy as np

        from src.neuroshift.detector import looks_like_led_bulb, looks_like_pc_fan

        frame = np.full((240, 240, 3), 40, np.uint8)
        cv2.circle(frame, (120, 120), 55, (96, 130, 180), -1)
        box = (60, 60, 180, 180)
        self.assertFalse(looks_like_led_bulb(frame, box))
        self.assertFalse(looks_like_pc_fan(frame, box))

    def test_luker_webcam_screenshots_are_the_lamp(self):
        """Webcam assets train templates. Live only locks a close held globe."""
        import cv2
        import numpy as np

        from src.neuroshift.detector import (
            ObjectDetector,
            _bulb_asset_files,
            _load_bulb_templates,
            find_led_bulbs,
        )

        names = [path.stem.lower() for path in _bulb_asset_files()]
        self.assertTrue(any(name.startswith("luker_webcam") for name in names))
        self.assertGreaterEqual(len(_load_bulb_templates()), 6)
        webs = sorted(
            path
            for path in _bulb_asset_files()
            if path.stem.lower().startswith("luker_webcam")
        )
        self.assertGreaterEqual(len(webs), 6)

        # Far ceiling glare must never lock or toggle the relay.
        far = np.full((480, 640, 3), 36, np.uint8)
        cv2.circle(far, (420, 55), 18, (255, 255, 255), -1)
        cv2.circle(far, (420, 55), 24, (248, 250, 255), 4)
        self.assertEqual(find_led_bulbs(far, [(70, 20, 400, 470)]), [])

        # Close held globe (user keeps the lamp near the camera).
        close = np.full((480, 640, 3), 36, np.uint8)
        box = self._paint_bulb(close, 400, 200, 70)
        people = [(70, 20, 380, 470)]
        found = find_led_bulbs(close, people)
        self.assertGreaterEqual(len(found), 1)
        x0, y0, x1, y1 = found[0][0]
        self.assertGreater((x1 - x0) * (y1 - y0) / (640 * 480), 0.028)
        self.assertGreater((x0 + x1) / 2, 350)

        det = ObjectDetector.__new__(ObjectDetector)
        det.conf = 0.12
        det.target_classes = {"fan", "lamp"}
        det.every_n_frames = 1
        det.iou_match = 0.3
        det.imgsz = 512
        det.model_name = "none"
        det._frame_i = 0
        det._last = []
        det._next_id = 1
        det.min_area_frac = 0.003
        det.max_area_frac = 0.45
        det.nms_iou = 0.55
        det.max_objects = 6
        det.available = False
        det.model = None
        det.last_people = people
        det._people_misses = 0
        objects = det.detect(close)
        lamps = [obj for obj in objects if obj.label == "lamp"]
        self.assertTrue(lamps)
        self.assertGreater((lamps[0].xyxy[0] + lamps[0].xyxy[2]) / 2, 350)
        _ = box

    def test_luker_photos_train_the_lamp_matcher(self):
        from pathlib import Path

        import cv2
        import numpy as np

        from src.neuroshift.detector import (
            ObjectDetector,
            _bulb_asset_files,
            _load_bulb_templates,
            find_led_bulbs,
        )

        names = [path.stem.lower() for path in _bulb_asset_files()]
        self.assertTrue(any(name.startswith("luker_held") for name in names))
        self.assertGreaterEqual(len(_load_bulb_templates()), 4)
        lukers = [path for path in _bulb_asset_files() if path.stem.lower().startswith("luker_held")]
        self.assertGreaterEqual(len(lukers), 4)
        for path in lukers:
            frame = cv2.imread(str(path))
            self.assertIsNotNone(frame, path.name)
            found = find_led_bulbs(frame)
            self.assertGreaterEqual(len(found), 1, path.name)

        src = cv2.imread(str(Path(__file__).resolve().parents[1] / "assets" / "luker_held_bulb.png"))
        self.assertIsNotNone(src)
        canvas = np.full((480, 640, 3), 32, np.uint8)
        placed = cv2.resize(src, (210, 370))
        canvas[55 : 55 + 370, 215 : 215 + 210] = placed
        people = [(90, 8, 560, 472)]
        found = find_led_bulbs(canvas, people)
        self.assertGreaterEqual(len(found), 1)
        x0, y0, x1, y1 = found[0][0]
        cx = (x0 + x1) / 2
        self.assertTrue(200 <= cx <= 450)

        det = ObjectDetector.__new__(ObjectDetector)
        det.conf = 0.12
        det.target_classes = {"fan", "lamp"}
        det.every_n_frames = 1
        det.iou_match = 0.3
        det.imgsz = 512
        det.model_name = "none"
        det._frame_i = 0
        det._last = []
        det._next_id = 1
        det.min_area_frac = 0.003
        det.max_area_frac = 0.45
        det.nms_iou = 0.55
        det.max_objects = 6
        det.available = False
        det.model = None
        det.last_people = people
        det._people_misses = 0
        objects = det.detect(canvas)
        self.assertTrue(any(obj.label == "lamp" for obj in objects))

    def test_user_luker_held_bulb_is_found(self):
        from pathlib import Path

        import cv2

        from src.neuroshift.detector import find_led_bulbs, looks_like_led_bulb

        path = Path(__file__).resolve().parents[1] / "assets" / "luker_held_bulb.png"
        frame = cv2.imread(str(path))
        self.assertIsNotNone(frame)
        h, w = frame.shape[:2]
        found = find_led_bulbs(frame)
        self.assertGreaterEqual(len(found), 1)
        x0, y0, x1, y1 = found[0][0]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.assertTrue(w * 0.20 <= cx <= w * 0.80)
        self.assertTrue(h * 0.12 <= cy <= h * 0.78)
        self.assertGreater((x1 - x0) * (y1 - y0) / (w * h), 0.04)
        self.assertTrue(looks_like_led_bulb(frame, found[0][0]))

    def test_user_led_bulb_photo_is_found(self):
        from pathlib import Path

        import cv2
        import numpy as np

        from src.neuroshift.detector import ObjectDetector, find_led_bulbs, looks_like_led_bulb

        path = Path(__file__).resolve().parents[1] / "assets" / "led_bulb_user.png"
        src = cv2.imread(str(path))
        self.assertIsNotNone(src)
        # Close-only live rule: place the bulb large in frame like a held demo.
        canvas = np.full((480, 640, 3), 36, np.uint8)
        placed = cv2.resize(src, (280, 400))
        canvas[40 : 40 + 400, 180 : 180 + 280] = placed
        found = find_led_bulbs(canvas)
        self.assertGreaterEqual(len(found), 1)
        x0, y0, x1, y1 = found[0][0]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.assertTrue(180 <= cx <= 460)
        self.assertTrue(60 <= cy <= 420)
        self.assertTrue(looks_like_led_bulb(canvas, found[0][0]))

        det = ObjectDetector.__new__(ObjectDetector)
        det.conf = 0.12
        det.target_classes = {"fan", "lamp", "bottle"}
        det.every_n_frames = 1
        det.iou_match = 0.3
        det.imgsz = 512
        det.model_name = "none"
        det._frame_i = 0
        det._last = []
        det._next_id = 1
        det.min_area_frac = 0.003
        det.max_area_frac = 0.45
        det.nms_iou = 0.55
        det.max_objects = 6
        det.available = False
        det.model = None
        objects = det.detect(canvas)
        self.assertTrue(any(obj.label == "lamp" for obj in objects))

    def test_cup_box_promotes_to_lamp(self):
        import numpy as np

        from src.neuroshift.detector import ObjectDetector

        frame = np.full((320, 240, 3), 40, np.uint8)
        box = self._paint_bulb(frame, 70, 50, 40)
        det = ObjectDetector.__new__(ObjectDetector)
        det.conf = 0.12
        det.target_classes = {"fan", "lamp"}
        det.every_n_frames = 1
        det.iou_match = 0.3
        det.imgsz = 512
        det.model_name = "none"
        det._frame_i = 0
        det._last = []
        det._next_id = 1
        det.min_area_frac = 0.003
        det.max_area_frac = 0.45
        det.nms_iou = 0.55
        det.max_objects = 6
        det.available = True
        det.model = None

        class _Box:
            def __init__(self, xyxy):
                self.cls = type("C", (), {"item": lambda self: 0})()
                self.conf = type("C", (), {"item": lambda self: 0.8})()
                self.xyxy = [type("A", (), {"tolist": lambda self, vals=xyxy: list(vals)})()]

        class _Res:
            names = {0: "cup"}
            boxes = [_Box(box)]

        det.model = type("M", (), {"predict": lambda *a, **k: [_Res()]})()
        objects = det.detect(frame)
        self.assertTrue(any(obj.label == "lamp" for obj in objects))
        self.assertFalse(any(obj.label == "cup" for obj in objects))

    def test_cup_is_not_in_the_detector(self):
        from src.neuroshift.detector import DEFAULT_TARGET_CLASSES, PROMPT_CLASSES

        self.assertNotIn("cup", DEFAULT_TARGET_CLASSES)
        self.assertNotIn("cup", PROMPT_CLASSES)
        self.assertNotIn("cooling fan", PROMPT_CLASSES)
        self.assertNotIn("cell phone", PROMPT_CLASSES)
        self.assertNotIn("bottle", PROMPT_CLASSES)
        self.assertIn("led bulb", PROMPT_CLASSES)
        self.assertIn("desk lamp", PROMPT_CLASSES)
        self.assertNotIn("lamp", PROMPT_CLASSES)

    def test_globe_and_cap_boxes_merge_to_one_lamp(self):
        import numpy as np

        from src.neuroshift.detector import (
            ObjectDetector,
            _collapse_same_object,
            _keep_held_appliances,
        )

        frame = np.full((480, 360, 3), 40, np.uint8)
        r = 48
        x, y = 110, 80
        self._paint_bulb(frame, x, y, r)
        globe = (x, y, x + 2 * r, y + 2 * r)
        cx = x + r
        neck_h = int(r * 0.45)
        cap_w, cap_h = int(r * 0.42), int(r * 0.38)
        cap = (
            cx - cap_w // 2,
            y + 2 * r + neck_h - 2,
            cx + cap_w // 2,
            y + 2 * r + neck_h + cap_h,
        )
        people = [(20, 90, 95, 450)]
        for extra in ("fan", "cup"):
            collapsed = _collapse_same_object(
                frame, [("lamp", 0.91, globe), (extra, 0.84, cap)]
            )
            labels = [item[0] for item in collapsed]
            self.assertEqual(labels, ["lamp"], extra)
            self.assertFalse(any(item[0] in {"fan", "cup"} for item in collapsed))
            kept = _keep_held_appliances(
                [("lamp", 0.91, globe), (extra, 0.84, cap)], people, 360, 480
            )
            self.assertEqual([item[0] for item in kept], ["lamp"])

        det = ObjectDetector.__new__(ObjectDetector)
        det.conf = 0.12
        det.target_classes = {"fan", "lamp"}
        det.every_n_frames = 1
        det.iou_match = 0.3
        det.imgsz = 512
        det.model_name = "none"
        det._frame_i = 0
        det._last = []
        det._next_id = 1
        det.min_area_frac = 0.003
        det.max_area_frac = 0.45
        det.nms_iou = 0.55
        det.max_objects = 6
        det.available = True
        det.model = None

        class _Box:
            def __init__(self, cls_id, xyxy, conf=0.85):
                self.cls = type("C", (), {"item": lambda self, i=cls_id: i})()
                self.conf = type("C", (), {"item": lambda self, c=conf: c})()
                self.xyxy = [type("A", (), {"tolist": lambda self, vals=xyxy: list(vals)})()]

        class _Res:
            names = {0: "lamp", 1: "fan"}
            boxes = [_Box(0, globe), _Box(1, cap)]

        det.model = type("M", (), {"predict": lambda *a, **k: [_Res()]})()
        objects = det.detect(frame)
        self.assertEqual([obj.label for obj in objects], ["lamp"])
        self.assertFalse(any(obj.label in {"fan", "cup"} for obj in objects))
        x0, y0, x1, y1 = objects[0].xyxy
        self.assertLessEqual(x0, globe[0] + 4)
        self.assertGreaterEqual(y1, cap[3] - 8)

    def test_lamp_and_fan_side_by_side_stay_two(self):
        import math

        import cv2
        import numpy as np

        from src.neuroshift.detector import (
            _collapse_same_object,
            _keep_held_appliances,
            find_led_bulbs,
        )

        frame = np.full((480, 640, 3), 40, np.uint8)
        fx, fy, size = 40, 160, 80
        frame[fy : fy + size, fx : fx + size] = (22, 22, 22)
        cx, cy = fx + size // 2, fy + size // 2
        radius = int(size * 0.36)
        cv2.circle(frame, (cx, cy), radius, (78, 78, 78), -1)
        for a in range(0, 180, 18):
            rad = math.radians(a)
            x2 = int(cx + radius * math.cos(rad))
            y2 = int(cy + radius * math.sin(rad))
            cv2.line(frame, (cx, cy), (x2, y2), (28, 28, 28), 2)
        cv2.circle(frame, (cx, cy), 7, (36, 36, 36), -1)
        fan_box = (fx, fy, fx + size, fy + size)
        self._paint_bulb(frame, 450, 120, 60)
        people = [(220, 80, 430, 460)]
        found_lamp = find_led_bulbs(frame, people)
        self.assertGreaterEqual(len(found_lamp), 1)
        lamp_box = found_lamp[0][0]

        collapsed = _collapse_same_object(
            frame, [("lamp", 0.9, lamp_box), ("fan", 0.88, fan_box)]
        )
        labels = sorted(item[0] for item in collapsed)
        self.assertEqual(labels, ["fan", "lamp"])
        kept = _keep_held_appliances(
            [("lamp", 0.9, lamp_box), ("fan", 0.88, fan_box)], people, 640, 480
        )
        kept_labels = sorted(item[0] for item in kept)
        self.assertEqual(kept_labels, ["fan", "lamp"])

    def test_lamp_metal_cap_is_not_a_fan(self):
        import numpy as np

        from src.neuroshift.detector import (
            ObjectDetector,
            looks_like_led_bulb,
            looks_like_pc_fan,
        )

        frame = np.full((480, 360, 3), 40, np.uint8)
        box = self._paint_bulb(frame, 110, 80, 48)
        x0, y0, x1, y1 = box
        cap = (x0 + 18, y1 - 42, x1 - 18, y1)
        self.assertTrue(looks_like_led_bulb(frame, box))
        self.assertFalse(looks_like_pc_fan(frame, box))
        self.assertFalse(looks_like_pc_fan(frame, cap))

        det = ObjectDetector.__new__(ObjectDetector)
        det.conf = 0.12
        det.target_classes = {"fan", "lamp"}
        det.every_n_frames = 1
        det.iou_match = 0.3
        det.imgsz = 512
        det.model_name = "none"
        det._frame_i = 0
        det._last = []
        det._next_id = 1
        det.min_area_frac = 0.003
        det.max_area_frac = 0.45
        det.nms_iou = 0.55
        det.max_objects = 6
        det.available = False
        det.model = None
        objects = det.detect(frame)
        self.assertTrue(any(obj.label == "lamp" for obj in objects))
        self.assertFalse(any(obj.label == "fan" for obj in objects))

    def test_wardrobe_mirror_is_not_a_second_lamp(self):
        import cv2
        import numpy as np

        from src.neuroshift.detector import (
            ObjectDetector,
            _keep_held_appliances,
            find_led_bulbs,
            looks_like_led_bulb,
        )

        frame = np.full((480, 640, 3), 40, np.uint8)
        frame[40:440, 20:220] = (72, 88, 108)
        cv2.circle(frame, (120, 180), 18, (230, 232, 235), -1)
        self._paint_bulb(frame, 450, 120, 60)
        people = [(220, 80, 430, 460)]
        wardrobe = (20, 40, 220, 440)
        found = find_led_bulbs(frame, people)
        self.assertGreaterEqual(len(found), 1)
        held = found[0][0]
        self.assertTrue(looks_like_led_bulb(frame, held))
        self.assertFalse(looks_like_led_bulb(frame, wardrobe))
        kept = _keep_held_appliances(
            [("lamp", 0.72, wardrobe), ("lamp", 0.80, held)], people, 640, 480
        )
        lamps = [item for item in kept if item[0] == "lamp"]
        self.assertEqual(len(lamps), 1)
        self.assertEqual(lamps[0][2], held)

        det = ObjectDetector.__new__(ObjectDetector)
        det.conf = 0.12
        det.target_classes = {"fan", "lamp"}
        det.every_n_frames = 1
        det.iou_match = 0.3
        det.imgsz = 512
        det.model_name = "none"
        det._frame_i = 0
        det._last = []
        det._next_id = 1
        det.min_area_frac = 0.003
        det.max_area_frac = 0.45
        det.nms_iou = 0.55
        det.max_objects = 6
        det.available = False
        det.model = None
        objects = det.detect(frame)
        found = [obj for obj in objects if obj.label == "lamp"]
        self.assertEqual(len(found), 1)
        cx = (found[0].xyxy[0] + found[0].xyxy[2]) / 2
        self.assertGreater(cx, 400)

    def test_user_bulb_holder_is_not_a_fan(self):
        from pathlib import Path

        import cv2

        from src.neuroshift.detector import ObjectDetector, _iou, find_led_bulbs, looks_like_pc_fan

        path = Path(__file__).resolve().parents[1] / "assets" / "led_bulb_user.png"
        frame = cv2.imread(str(path))
        self.assertIsNotNone(frame)
        found = find_led_bulbs(frame)
        self.assertGreaterEqual(len(found), 1)
        lamp_box = found[0][0]
        self.assertFalse(looks_like_pc_fan(frame, lamp_box))
        x0, y0, x1, y1 = lamp_box
        cap = (x0 + (x1 - x0) // 4, y1 - (y1 - y0) // 3, x1 - (x1 - x0) // 4, y1)
        self.assertFalse(looks_like_pc_fan(frame, cap))

        det = ObjectDetector.__new__(ObjectDetector)
        det.conf = 0.12
        det.target_classes = {"fan", "lamp"}
        det.every_n_frames = 1
        det.iou_match = 0.3
        det.imgsz = 512
        det.model_name = "none"
        det._frame_i = 0
        det._last = []
        det._next_id = 1
        det.min_area_frac = 0.003
        det.max_area_frac = 0.45
        det.nms_iou = 0.55
        det.max_objects = 6
        det.available = False
        det.model = None
        objects = det.detect(frame)
        lamps = [obj for obj in objects if obj.label == "lamp"]
        self.assertTrue(lamps)
        for fan in (obj for obj in objects if obj.label == "fan"):
            self.assertLess(_iou(fan.xyxy, lamps[0].xyxy), 0.25)

    def test_empty_room_is_not_a_bulb(self):
        from pathlib import Path

        import cv2

        from src.neuroshift.detector import find_led_bulbs

        path = Path(__file__).resolve().parents[1] / "assets" / "no_fan_room.png"
        frame = cv2.imread(str(path))
        self.assertIsNotNone(frame)
        self.assertEqual(find_led_bulbs(frame), [])


class TestCuedStandInMapping(unittest.TestCase):
    def test_bottle_actuation_scores_as_lamp_hit(self):
        from src.neuroshift.api.state import AppRuntime
        from src.neuroshift.appliances import ActuationEvent
        from src.neuroshift.api.schemas import DecisionOut

        rt = AppRuntime()
        rt.start_cued_trial("lamp")

        class _Result:
            changed = False
            dwell_progress = 1.0
            actuation = ActuationEvent(
                device_id="bottle_1", label="Bottle", new_state=True, command="ON"
            )

        decision = DecisionOut(
            action="ACT",
            selected_device="bottle_1",
            selected_label="Bottle",
            reason="test",
            yaw=0.0,
            emg=1.0,
        )
        rt._record_tick_result(_Result(), decision)
        self.assertEqual(rt.cued.summary()["hits"], 1)
        self.assertIsNotNone(rt.cued.last_resolved)
        self.assertEqual(rt.cued.last_resolved.outcome, "HIT")


class TestLookWizard(unittest.TestCase):
    def test_stale_calibration_times_out(self):
        from src.neuroshift.api.state import AppRuntime
        from src.neuroshift.types import GazeEstimate

        rt = AppRuntime()
        rt._look_wizard = {"phase": "lamp", "t0": 0.0, "samples": [(0.0, 0.0)] * 8, "queue": ["lamp"]}
        g = GazeEstimate(True, (320, 200), 0.0, 0.0, 0.9)
        note = rt._step_look_wizard(g, [], object(), 20.0)
        self.assertIsNone(rt._look_wizard)
        self.assertIn("timed out", (note or "").lower())


class TestCuedReport(unittest.TestCase):
    def test_html_includes_cued_accuracy(self):
        from src.neuroshift.evaluation import CuedTrialRunner
        from src.neuroshift.report import build_trials_report
        from src.neuroshift.trials import TrialLog

        log = TrialLog()
        runner = CuedTrialRunner(seed=1)
        runner.start(device_id="lamp", now=0.0)
        runner.on_actuation(device_id="lamp", label="Lamp", now=1.0)
        out = ROOT / "logs" / "test_out" / "cued_report.html"
        path = build_trials_report(
            trials=log,
            session={"far_proxy": 0.0, "actuations": 1},
            cued=runner.summary(),
            cued_rows=runner.to_dicts(),
            out_path=out,
        )
        html = path.read_text(encoding="utf-8")
        self.assertIn("Cued accuracy", html)
        self.assertIn("HIT", html)


class TestIrisLook(unittest.TestCase):
    def _lm(self, *, iris_shift: float):
        class P:
            def __init__(self, x: float, y: float = 0.5):
                self.x = x
                self.y = y

        pts = [P(0.5, 0.5) for _ in range(478)]
        pts[33], pts[133], pts[159], pts[145] = P(0.30), P(0.40), P(0.35, 0.46), P(0.35, 0.54)
        pts[468] = P(0.35 + iris_shift)
        pts[263], pts[362], pts[386], pts[374] = P(0.70), P(0.60), P(0.65, 0.46), P(0.65, 0.54)
        pts[473] = P(0.65 + iris_shift)
        return pts

    def test_looking_left_is_negative_yaw(self):
        from src.neuroshift.gaze import iris_look

        yaw, pitch, xy = iris_look(self._lm(iris_shift=-0.03), 640, 480)
        self.assertLess(yaw, -0.5)
        self.assertIsNotNone(xy)

    def test_looking_right_is_positive_yaw(self):
        from src.neuroshift.gaze import iris_look

        yaw, _, _ = iris_look(self._lm(iris_shift=0.03), 640, 480)
        self.assertGreater(yaw, 0.5)

    def test_short_landmark_list_returns_none(self):
        from src.neuroshift.gaze import iris_look

        self.assertIsNone(iris_look([None] * 10, 640, 480))


class TestCameraFrameScore(unittest.TestCase):
    def test_black_buffer_is_rejected(self):
        import numpy as np

        from src.neuroshift.camera import score_frame

        black = np.zeros((48, 64, 3), dtype=np.uint8)
        self.assertLessEqual(score_frame(black), 0)
        self.assertLessEqual(score_frame(None), 0)

    def test_color_picture_outscores_ir_gray(self):
        import numpy as np

        from src.neuroshift.camera import score_frame

        gray = np.full((48, 64, 3), 40, dtype=np.uint8)
        color = np.zeros((48, 64, 3), dtype=np.uint8)
        color[:, :32] = (30, 80, 180)
        color[:, 32:] = (40, 160, 50)
        self.assertGreater(score_frame(color), score_frame(gray))
        self.assertGreater(score_frame(color), 8)


class TestPairingUrls(unittest.TestCase):
    def test_status_includes_android_apk_when_built(self):
        from src.neuroshift.api.state import AppRuntime

        apk = ROOT / "dist-mobile" / "MyoGaze.apk"
        rt = AppRuntime()
        out = rt.status("test")
        if apk.exists():
            self.assertTrue(out.android_apk_url)
            assert out.android_apk_url is not None
            self.assertTrue(out.android_apk_url.endswith("/app.apk"))
        if out.iphone_setup_url:
            self.assertTrue(out.iphone_setup_url.endswith("/iphone"))


class TestRemoteCameraFrame(unittest.TestCase):
    def test_jpeg_roundtrip(self):
        import base64

        import cv2
        import numpy as np

        from src.neuroshift.api.state import AppRuntime

        rt = AppRuntime()
        frame = np.zeros((48, 64, 3), dtype=np.uint8)
        frame[:] = (20, 40, 80)
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        self.assertTrue(ok)
        b64 = base64.b64encode(buf.tobytes()).decode("ascii")
        self.assertTrue(rt.push_remote_frame(b64))
        got = rt._take_remote_frame()
        self.assertEqual(got.shape[0], 48)
        self.assertEqual(got.shape[1], 64)

    def test_rejects_garbage(self):
        from src.neuroshift.api.state import AppRuntime

        rt = AppRuntime()
        self.assertFalse(rt.push_remote_frame(""))
        self.assertFalse(rt.push_remote_frame("$$$$"))


class TestAccounts(unittest.TestCase):
    def test_email_and_phone_accounts(self):
        import tempfile

        from src.neuroshift import accounts

        with tempfile.TemporaryDirectory() as tmp:
            accounts._STORE = Path(tmp) / "accounts.json"
            created = accounts.register("Ada@Example.com", "password1")
            self.assertEqual(created["user"]["identifier"], "ada@example.com")
            self.assertEqual(accounts.user_for_token(created["token"])["name"], "ada")

            phone = accounts.register("+1 555 010 1999", "password1")
            self.assertEqual(phone["user"]["kind"], "phone")
            signed = accounts.login("15550101999", "password1")
            self.assertEqual(signed["user"]["id"], phone["user"]["id"])

            with self.assertRaises(ValueError):
                accounts.login("ada@example.com", "wrong-pass")
            with self.assertRaises(ValueError):
                accounts.register("ada@example.com", "password1")


if __name__ == "__main__":
    unittest.main()
