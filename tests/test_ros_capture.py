import copy
import json
import unittest
from unittest.mock import patch

from simulator.http_motion import HttpMotionSession
from simulator.motion import ROOT, SCENARIOS, verify_fixture
from simulator.motion_tools import TOOL_DESCRIPTIONS
from simulator.ros_capture import Capture, validate_capture


def recording(scenario=SCENARIOS[2]):
    state, rows = verify_fixture(ROOT / scenario)
    observations = state["observations"]
    capture_id = "1234567890abcdef" * 2
    begin = {"kind": "begin", "capture_id": capture_id, "expected_samples": 601,
        "conditions": observations["read_motion_test_conditions"]["data"],
        "configuration": observations["read_control_configuration"]["data"],
        "unavailable_fields": observations["read_motion_test_conditions"]["unavailable_fields"],
        "trajectory_sha256": observations["read_motion_test_results"]["data"]["trajectory_sha256"],
        "model_version": observations["read_motion_test_results"]["data"]["model_version"],
        "fixture_observed_at": observations["read_motion_test_conditions"]["observed_at"]}
    messages = [copy.deepcopy(begin)] + [{"kind": "sample", "capture_id": capture_id,
        "sequence": i, "row": row} for i, row in enumerate(rows)] + [{"kind": "end", "capture_id": capture_id,
        "sample_count": 601, "trajectory_sha256": begin["trajectory_sha256"]}]
    return state, messages


def complete(scenario=SCENARIOS[2]):
    _, messages = recording(scenario)
    capture = Capture()
    for msg in messages:
        capture.accept(msg)
    return capture


class RosCaptureTests(unittest.TestCase):
    def test_all_cases_recalculate_and_preserve_unknowns_with_new_provenance(self):
        for scenario in SCENARIOS:
            source, _ = recording(scenario)
            captured = complete(scenario)
            state, rows = validate_capture(captured.frozen)
            self.assertEqual(len(rows), 601)
            self.assertNotEqual(state["snapshot_id"], source["snapshot_id"])
            self.assertEqual(state["observations"]["read_motion_test_results"]["data"]["metrics"],
                             source["observations"]["read_motion_test_results"]["data"]["metrics"])
            for envelope in state["observations"].values():
                self.assertEqual(envelope["source_type"], "synthetic")
                self.assertEqual(envelope["transport"]["received_samples"], 601)
                self.assertNotIn(scenario, json.dumps(envelope))
            if scenario == SCENARIOS[2]:
                cond = state["observations"]["read_motion_test_conditions"]
                self.assertIsNone(cond["data"]["equivalent_inertia"])
                self.assertIsNone(cond["data"]["payload_record"])
                self.assertEqual(cond["status"], "partial")

    def test_drop_duplicate_mixed_and_truncated_records_never_publish_snapshot(self):
        _, source = recording()
        variants = [source[:5] + source[6:], source[:5] + [source[4]] + source[5:], source[:5] + [source[-1]]]
        mixed = copy.deepcopy(source)
        mixed[5]["capture_id"] = "0" * 32
        variants.append(mixed)
        for messages in variants:
            capture = Capture()
            with self.assertRaises(ValueError):
                for msg in messages:
                    capture.accept(msg)
            self.assertIsNone(capture.frozen)
            self.assertIsNotNone(capture.error)

    def test_modified_sample_or_metric_is_rejected(self):
        _, messages = recording()
        messages[100]["row"]["actual_position_rad"] += .01
        capture = Capture()
        with self.assertRaises(ValueError):
            for msg in messages:
                capture.accept(msg)
        payload = complete().frozen
        payload["snapshot"]["observations"]["read_motion_test_results"]["data"]["metrics"][0]["value"] = 0.
        with self.assertRaises(ValueError):
            validate_capture(payload)

    def test_http_session_reads_once_and_never_replaces_snapshot(self):
        payload = complete().frozen
        raw = json.dumps(payload).encode()
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return raw
        with patch("simulator.http_motion.build_opener") as factory:
            opener = factory.return_value
            opener.open.return_value = Response()
            session = HttpMotionSession(expected_capture_id=payload["capture_id"])
            self.assertEqual(opener.open.call_count, 1)
            opener.open.side_effect = OSError("offline")
            for tool in TOOL_DESCRIPTIONS:
                args = {"bench_id": "BENCH-001", "test_id": session.test_id}
                response = session.call(tool, args)
                response["data"].clear()
                self.assertTrue(session.call(tool, args)["data"])
            self.assertEqual(opener.open.call_count, 1)
        with patch("simulator.http_motion.build_opener", side_effect=OSError("offline")):
            with self.assertRaisesRegex(ValueError, "no fixture fallback"):
                HttpMotionSession()
        with patch("simulator.http_motion.build_opener") as factory:
            factory.return_value.open.return_value = Response()
            with self.assertRaisesRegex(ValueError, "no fixture fallback"):
                HttpMotionSession(expected_capture_id="0" * 32)


if __name__ == "__main__":
    unittest.main()
