import copy
import unittest

from pydantic import ValidationError

from rag_demo.facts import extract_facts, render_analysis
from simulator.tools import DiagnosticSession


def payload(fact_ids):
    return {"language": "en", "fact_ids": fact_ids,
            "interpretations": [{"text": 'The configuration needs verification.', "fact_ids": fact_ids, "chunk_ids": ["rule::c01"]}],
            "questions": [], "next_steps": ['Ask an engineer to check the versions.']}


def registry(scenario):
    session = DiagnosticSession(scenario)
    facts = {}
    for name in ("read_bench_inventory", "read_runtime_config", "read_connection_observations", "read_initialization_status"):
        facts.update({f["fact_id"]: f for f in extract_facts(name, session.call(name, {"bench_id": "BENCH-001"}))})
    return facts


class BoundFactsTests(unittest.TestCase):
    def test_different_registered_and_installed_versions_keep_own_sources(self):
        facts = registry("version_mismatch")
        answer, report = render_analysis(payload(["EV-026-02::client_version"]), facts, {"rule::c01"})
        self.assertIn('Installed client version: "2.0.0" [EV-026-02]', answer)
        self.assertIn('Registered expected client version: "1.4.0" [EV-026-01]', answer)
        self.assertIn("EV-026-01::expected_client_version", report["rendered_fact_ids"])
        self.assertEqual(facts["EV-026-02::client_version"]["origin"], "runtime_observation")
        self.assertEqual(facts["EV-026-01::expected_client_version"]["origin"], "asset_registry")

    def test_same_version_values_are_not_merged(self):
        facts = registry("healthy")
        answer, _ = render_analysis(payload(["EV-017-01::expected_client_version"]), facts, {"rule::c01"})
        self.assertIn('Installed client version: "1.4.0" [EV-017-02]', answer)
        self.assertIn('Registered expected client version: "1.4.0" [EV-017-01]', answer)

    def test_unreachable_version_is_unknown_not_registered_value(self):
        facts = registry("connection_timeout")
        answer, _ = render_analysis(payload(["EV-039-01::expected_controller_version"]), facts, {"rule::c01"})
        self.assertIn('Registered expected controller version: "1.3.0" [EV-039-01]', answer)
        self.assertIn('Controller version observed during handshake: Unknown (endpoint_unreachable) [EV-039-03]', answer)

    def test_cannot_bind_client_version_to_registry_evidence(self):
        with self.assertRaisesRegex(ValueError, "fact not returned"):
            render_analysis(payload(["EV-026-01::client_version"]), registry("version_mismatch"), {"rule::c01"})

    def test_model_cannot_supply_fact_text_or_values(self):
        for field in ("facts", "values", "evidence_id"):
            bad = payload(["EV-026-02::client_version"])
            bad[field] = "invented"
            with self.assertRaises(ValidationError):
                render_analysis(bad, registry("version_mismatch"), {"rule::c01"})

    def test_mixed_snapshot_is_rejected(self):
        facts = registry("healthy") | registry("version_mismatch")
        with self.assertRaisesRegex(ValueError, "different snapshots"):
            render_analysis(payload(["EV-017-02::client_version", "EV-026-02::client_version"]), facts, {"rule::c01"})

    def test_failed_acquisition_and_absent_field_do_not_become_facts(self):
        self.assertEqual(extract_facts("read_runtime_config", {"status": "error"}), [])
        source = DiagnosticSession("healthy").read_runtime_config("BENCH-001")
        del source["data"]["client_version"]
        self.assertNotIn("client_version", {f["field"] for f in extract_facts("read_runtime_config", source)})

    def test_bound_values_are_copied(self):
        source = DiagnosticSession("healthy").read_runtime_config("BENCH-001")
        facts = extract_facts("read_runtime_config", source)
        before = copy.deepcopy(facts)
        source["data"]["supported_protocols"].append(99)
        self.assertEqual(facts, before)

    def test_available_null_means_none_not_unknown(self):
        facts = registry("healthy")
        answer, _ = render_analysis(payload(["EV-017-04::error_code"]), facts, {"rule::c01"})
        self.assertIn('Initialization error code: None [EV-017-04]', answer)


if __name__ == "__main__":
    unittest.main()
