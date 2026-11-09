import json
import unittest
from unittest.mock import patch

from simulator.tools import DiagnosticSession, SCENARIOS, TOOL_DESCRIPTIONS, tool_specs


class DiagnosticToolsTests(unittest.TestCase):
    def test_all_tools_and_scenarios_share_snapshot(self):
        for scenario in SCENARIOS:
            session = DiagnosticSession(scenario)
            results = [session.call(name, {"bench_id": "BENCH-001"}) for name in TOOL_DESCRIPTIONS]
            self.assertEqual(len({r["snapshot_id"] for r in results}), 1)
            self.assertEqual(len({r["evidence_id"] for r in results}), 5)
            self.assertTrue(all(r["status"] != "error" for r in results))
            serialized = json.dumps(results)
            for label in (*SCENARIOS, "root_cause", "expected_behavior", "references/"):
                self.assertNotIn(label, serialized)

    def test_unreachable_does_not_reveal_registered_version_as_observation(self):
        session = DiagnosticSession("connection_timeout")
        self.assertEqual(session.read_bench_inventory("BENCH-001")["data"]["expected_controller_version"], "1.3.0")
        result = session.read_connection_observations("BENCH-001")
        self.assertEqual(result["status"], "partial")
        self.assertIsNone(result["data"]["controller_version"])
        self.assertIsNone(result["data"]["reported_protocol"])
        self.assertEqual(result["data"]["ping"]["received"], 0)

    def test_returned_data_cannot_mutate_session(self):
        session = DiagnosticSession("healthy")
        result = session.read_runtime_config("BENCH-001")
        result["data"]["supported_protocols"].append(999)
        self.assertEqual(session.read_runtime_config("BENCH-001")["data"]["supported_protocols"], [1])
        logs = session.read_diagnostic_log("BENCH-001")
        logs["data"]["events"][0]["message"] = "modified"
        self.assertNotEqual(session.read_diagnostic_log("BENCH-001")["data"]["events"][0]["message"], "modified")

    def test_snapshot_does_not_reread_files(self):
        session = DiagnosticSession("healthy")
        with patch("pathlib.Path.read_text", side_effect=OSError("file changed")):
            self.assertEqual(session.read_initialization_status("BENCH-001")["data"]["status"], "ready")

    def test_log_tail_and_evidence_identity(self):
        session = DiagnosticSession("healthy")
        full = session.read_diagnostic_log("BENCH-001")
        tail = session.read_diagnostic_log("BENCH-001", 2)
        self.assertEqual(tail["data"]["events"], full["data"]["events"][-2:])
        self.assertNotEqual(tail["evidence_id"], full["evidence_id"])
        self.assertEqual(tail, session.read_diagnostic_log("BENCH-001", 2))
        self.assertEqual(len(session.read_diagnostic_log("BENCH-001", 100)["data"]["events"]), len(full["data"]["events"]))

    def test_invalid_inputs_return_tool_errors(self):
        session = DiagnosticSession("healthy")
        cases = [
            ("execute_motion", {"bench_id": "BENCH-001"}, "UNKNOWN_TOOL"),
            ("read_runtime_config", {}, "INVALID_ARGUMENTS"),
            ("read_runtime_config", [], "INVALID_ARGUMENTS"),
            ("read_runtime_config", {"bench_id": "OTHER"}, "UNKNOWN_BENCH"),
            ("read_runtime_config", {"bench_id": "BENCH-001", "scenario": "healthy"}, "INVALID_ARGUMENTS"),
        ]
        cases += [("read_diagnostic_log", {"bench_id": "BENCH-001", "limit": value}, "INVALID_LIMIT")
                  for value in (0, 101, True, 2.5, "2", None)]
        for name, arguments, code in cases:
            with self.subTest(name=name, arguments=arguments):
                result = session.call(name, arguments)
                self.assertEqual(result["status"], "error")
                self.assertIsNone(result["data"])
                self.assertEqual(result["error"]["code"], code)

    def test_session_selection_is_application_only(self):
        for selection in ("../healthy", "unknown"):
            with self.assertRaisesRegex(ValueError, "Unknown diagnostic scenario"):
                DiagnosticSession(selection)
        with patch("pathlib.Path.read_text", side_effect=OSError("private/path")):
            with self.assertRaisesRegex(ValueError, "could not be loaded") as caught:
                DiagnosticSession("healthy")
        self.assertNotIn("private/path", str(caught.exception))

    def test_model_specs_do_not_offer_scenario_or_mutation(self):
        specs = tool_specs()
        self.assertEqual({s["name"] for s in specs}, set(TOOL_DESCRIPTIONS))
        for spec in specs:
            props = spec["input_schema"]["properties"]
            self.assertLessEqual(set(props), {"bench_id", "limit"})
            self.assertFalse(spec["input_schema"]["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
