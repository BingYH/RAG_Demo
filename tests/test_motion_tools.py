import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from rag_demo.facts import extract_facts, render_analysis
from rag_demo.retrieval import load_chunks
from simulator.motion import ROOT, SCENARIOS
from simulator.motion_tools import MotionSession, TOOL_DESCRIPTIONS, tool_specs


class MotionToolTests(unittest.TestCase):
    def test_all_scenarios_use_session_snapshot_and_neutral_evidence(self):
        for scenario in SCENARIOS:
            session = MotionSession(scenario)
            outputs = [session.call(name, {"bench_id": "BENCH-001", "test_id": session.test_id})
                       for name in TOOL_DESCRIPTIONS]
            self.assertEqual(len({o["snapshot_id"] for o in outputs}), 1)
            self.assertEqual(len({o["evidence_id"] for o in outputs}), 3)
            self.assertTrue(all(o["status"] in ("ok", "partial") for o in outputs))
            for secret in (*SCENARIOS, "root_cause", "expected_behavior", "trajectory.csv", "references/", "motion_scenarios"):
                self.assertNotIn(secret, json.dumps(outputs))

    def test_snapshot_is_copied_and_never_reread_by_calls(self):
        session = MotionSession(SCENARIOS[0])
        args = {"bench_id": "BENCH-001", "test_id": session.test_id}
        initial = session.call("read_control_configuration", args)
        initial["data"]["registered_baseline"]["kd"] = 99
        with patch("pathlib.Path.read_text", side_effect=OSError("changed")), patch("pathlib.Path.read_bytes", side_effect=OSError("changed")):
            self.assertEqual(session.call("read_control_configuration", args)["data"]["registered_baseline"]["kd"], .85)

    def test_rejects_other_tests_mutations_paths_and_unknown_tools(self):
        session = MotionSession(SCENARIOS[1])
        args = {"bench_id": "BENCH-001", "test_id": session.test_id}
        for name, request, code in (
            ("read_control_configuration", args | {"test_id": "TEST-104"}, "UNKNOWN_TEST"),
            ("read_control_configuration", args | {"bench_id": "OTHER"}, "UNKNOWN_BENCH"),
            ("read_control_configuration", args | {"path": "secret"}, "INVALID_ARGUMENTS"),
            ("read_control_configuration", {"bench_id": "BENCH-001"}, "INVALID_ARGUMENTS"),
            ("set_gains", args, "UNKNOWN_TOOL"),
        ):
            result = session.call(name, request)
            self.assertEqual(result["error"]["code"], code)
            self.assertEqual(extract_facts(name, result), [])
        for spec in tool_specs():
            self.assertEqual(set(spec["input_schema"]["required"]), {"bench_id", "test_id"})
            self.assertFalse(spec["input_schema"]["additionalProperties"])

    def test_corrupt_fixture_fails_without_leaking_path_or_label(self):
        for failure in (ValueError("secret/path"), OSError("private")):
            with patch("simulator.motion_tools.verify_fixture", side_effect=failure):
                with self.assertRaisesRegex(ValueError, "^Motion snapshot could not be loaded or validated.$"):
                    MotionSession(SCENARIOS[0])
        state = json.loads((ROOT / SCENARIOS[2] / "state.json").read_text())
        state["observations"]["read_motion_test_conditions"]["unavailable_fields"] = []
        with patch("simulator.motion_tools.verify_fixture", return_value=(state, [])):
            with self.assertRaises(ValueError):
                MotionSession(SCENARIOS[2])

    def test_unknown_load_fact_is_not_replaced_and_registry_is_labelled(self):
        session = MotionSession(SCENARIOS[2])
        envelope = session.call("read_motion_test_conditions", {"bench_id": "BENCH-001", "test_id": session.test_id})
        facts = {f["fact_id"]: f for f in extract_facts("read_motion_test_conditions", envelope)}
        unknown_id = envelope["evidence_id"] + "::equivalent_inertia"
        self.assertIsNone(facts[unknown_id]["value"])
        self.assertEqual(facts[unknown_id]["unavailable_reason"], "not_collected")
        registry = next(f for f in facts.values() if f["field"] == "registered_baseline.equivalent_inertia_kg_m2")
        self.assertEqual(registry["origin"], "asset_registry")
        payload = {"language": "en", "fact_ids": [unknown_id], "interpretations": [{
            "text": "Current inertia is unknown; verify test conditions.", "fact_ids": [unknown_id], "chunk_ids": ["rule::c01"]}],
            "questions": [], "next_steps": ["Ask for the load record."]}
        answer, report = render_analysis(payload, facts, {"rule::c01"})
        self.assertIn("Unknown (not_collected)", answer)
        self.assertIn(registry["fact_id"], report["rendered_fact_ids"])

    def test_configuration_and_procedure_must_match_trajectory(self):
        from simulator.motion import verify_fixture
        state, rows = verify_fixture(ROOT / SCENARIOS[1])
        for tool, field, value in (("read_control_configuration", "kd", .85),
                                   ("read_control_configuration", "kp", float("nan")),
                                   ("read_motion_test_conditions", "sample_period_s", .02)):
            changed = copy.deepcopy(state)
            changed["observations"][tool]["data"][field] = value
            with patch("simulator.motion_tools.verify_fixture", return_value=(changed, rows)):
                with self.assertRaises(ValueError):
                    MotionSession(SCENARIOS[1])

    def test_metrics_bind_by_identity_not_list_position_and_keep_provenance(self):
        session = MotionSession(SCENARIOS[1])
        envelope = session.call("read_motion_test_results", {"bench_id": "BENCH-001", "test_id": session.test_id})
        initial = extract_facts("read_motion_test_results", envelope)
        reversed_copy = copy.deepcopy(envelope)
        reversed_copy["data"]["metrics"].reverse()
        self.assertEqual(initial, extract_facts("read_motion_test_results", reversed_copy))
        overshoot = next(f for f in initial if f["field"] == "metrics.overshoot_pct")
        self.assertEqual(overshoot["origin"], "derived_calculation")
        self.assertEqual(overshoot["value"]["threshold"], 5.)
        self.assertEqual(overshoot["value"]["result"], "fail")
        self.assertEqual(overshoot["derivation"]["trajectory_sha256"], envelope["data"]["trajectory_sha256"])
        envelope["data"]["metrics"][0]["value"] = 0.
        self.assertGreater(overshoot["value"]["value"], 50.)

    def test_knowledge_scopes_are_disjoint_and_exclude_answer_labels(self):
        root = Path(__file__).resolve().parents[1] / "knowledge"
        init = load_chunks(root)
        motion = load_chunks(root, applies_to="demo-joint-response-v1")
        self.assertEqual(len(init), 25)
        self.assertEqual({c["metadata"]["doc_id"] for c in motion},
                         {"procedure.joint_response_test", "troubleshooting.joint_response_anomalies"})
        self.assertFalse({c["id"] for c in init} & {c["id"] for c in motion})
        for scope, chunks in (("demo-bench-v1", init), ("demo-joint-response-v1", motion)):
            self.assertTrue(all(c["metadata"]["applies_to"] == scope for c in chunks))
        serialized = json.dumps(motion)
        for label in (*SCENARIOS, "SNAP-307", "TEST-218", "58.53", "16.01"):
            self.assertNotIn(label, serialized)


if __name__ == "__main__":
    unittest.main()
