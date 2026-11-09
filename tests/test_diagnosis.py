import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from langsmith import tracing_context

from rag_demo.diagnosis import run_diagnosis
from rag_demo.retrieval import load_chunks
from simulator.tools import DiagnosticSession


class Block:
    def __init__(self, **data):
        self.data = data

    def model_dump(self, **kwargs):
        return self.data


def response(blocks, reason):
    return SimpleNamespace(content=[Block(**b) for b in blocks], stop_reason=reason,
                           usage=SimpleNamespace(input_tokens=1, output_tokens=1))


class FakeClaude:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.messages = self
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(json.loads(json.dumps(kwargs)))
        return next(self.responses)


class FakeIndex:
    knowledge_version = "test-version"

    def search(self, query, top_k=4):
        return {"status": "ok", "matches": [{"chunk_id": "rule::c01", "text": "A discrepancy needs verification."}]}


def tool_round():
    names = ["read_bench_inventory", "read_runtime_config", "read_connection_observations", "search_knowledge"]
    return response([{"type": "tool_use", "name": name, "id": f"t{i}",
        "input": {"query": "endpoint configuration"} if name == "search_knowledge" else {"bench_id": "BENCH-001"}}
        for i, name in enumerate(names)], "tool_use")


def report_response(fact_id="EV-039-03::controller_version", chunk_id="rule::c01"):
    return response([{"type": "tool_use", "id": "report", "name": "submit_analysis", "input": {
        "language": "zh", "fact_ids": [fact_id],
        "interpretations": [{"text": "Further verification is needed.", "fact_ids": [fact_id], "chunk_ids": [chunk_id]}],
        "questions": ["Which endpoint is intended?"], "next_steps": ["Verify the intended endpoint."]}}], "tool_use")


class DiagnosisTests(unittest.TestCase):
    def run_case(self, claude, **kwargs):
        with tracing_context(enabled=False):
            return run_diagnosis(claude, DiagnosticSession("connection_timeout"),
                                 FakeIndex(), "Investigate the bench.", "fake-model",
                                 review_function=kwargs.pop("review_function", lambda *_: {
                                     "passed": True, "issues": [], "usage": {"input_tokens": 0, "output_tokens": 0},
                                     "trace_steps": 0}), **kwargs)

    def test_evidence_review_failure_is_corrected_once_and_usage_counted(self):
        decisions = iter([
            {"passed": False, "issues": [{"code": "network_overclaim", "location": "interpretations[0]",
                "message": "A ping reply cannot exclude all network problems."}],
             "usage": {"input_tokens": 10, "output_tokens": 2}, "trace_steps": 2},
            {"passed": True, "issues": [], "usage": {"input_tokens": 10, "output_tokens": 2}, "trace_steps": 2},
        ])
        claude = FakeClaude([tool_round(), report_response(), report_response()])
        result = self.run_case(claude, review_function=lambda *_: next(decisions))
        self.assertEqual(len(result["evidence_reviews"]), 2)
        self.assertEqual(result["usage"]["input_tokens"], 23)
        self.assertTrue(result["evidence_reviews"][-1]["passed"])
        feedback = json.loads(claude.requests[2]["messages"][-1]["content"][0]["content"])
        self.assertIn("network_overclaim", feedback["error"]["message"])

    def test_repeated_evidence_review_failure_stops(self):
        failed = {"passed": False, "issues": [{"code": "redundant_question", "location": "questions[0]",
            "message": "Version already observed."}], "usage": {"input_tokens": 1, "output_tokens": 1}, "trace_steps": 2}
        with self.assertRaisesRegex(RuntimeError, "after one correction"):
            self.run_case(FakeClaude([tool_round(), report_response(), report_response()]), review_function=lambda *_: failed)

    def test_tool_results_are_fed_back_with_matching_ids(self):
        claude = FakeClaude([tool_round(), report_response()])
        result = self.run_case(claude)
        self.assertEqual(result["rounds"], 2)
        self.assertEqual(len(result["tool_calls"]), 5)
        results = claude.requests[1]["messages"][-1]["content"]
        self.assertEqual([r["tool_use_id"] for r in results], ["t0", "t1", "t2", "t3"])
        self.assertIsNone(json.loads(results[2]["content"])["data"]["controller_version"])
        self.assertNotIn("connection_timeout", json.dumps(claude.requests))
        self.assertIn("事实（程序生成）", result["answer"])
        self.assertEqual(result["facts"][0]["evidence_id"], "EV-039-01")

    def test_ungrounded_early_answer_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "minimum diagnostic evidence"):
            self.run_case(FakeClaude([response([{"type": "text", "text": "Replace controller."}], "end_turn")]))

    def test_invented_citation_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "not returned"):
            self.run_case(FakeClaude([tool_round(), report_response("EV-invented::client_version"),
                                     report_response("EV-invented::client_version")]))

    def test_citation_repair_is_bounded_and_can_succeed(self):
        claude = FakeClaude([tool_round(), report_response("EV-invented::client_version"), report_response()])
        result = self.run_case(claude)
        self.assertEqual(result["rounds"], 3)
        correction = json.loads(claude.requests[2]["messages"][-1]["content"][0]["content"])
        self.assertEqual(correction["error"]["code"], "INVALID_REPORT")
        self.assertTrue(result["citation_repaired"])

    def test_invalid_knowledge_reference_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "knowledge chunk not returned"):
            self.run_case(FakeClaude([tool_round(), report_response(chunk_id="missing::c99"),
                                     report_response(chunk_id="missing::c99")]))

    def test_free_text_cannot_replace_the_rendered_facts(self):
        claude = FakeClaude([tool_round(), response([{"type": "text", "text": "Wrong facts: controller version 999."}], "end_turn"), report_response()])
        result = self.run_case(claude)
        self.assertNotIn("999", result["answer"])
        self.assertIn("未知", result["answer"])

    def test_truncated_answer_is_not_accepted(self):
        with self.assertRaisesRegex(RuntimeError, "truncated"):
            self.run_case(FakeClaude([response([{"type": "text", "text": "Partial"}], "max_tokens")]))

    def test_tool_and_round_budgets(self):
        with self.assertRaisesRegex(RuntimeError, "tool-call budget"):
            self.run_case(FakeClaude([tool_round()]), max_tool_calls=2)
        with self.assertRaisesRegex(RuntimeError, "round budget"):
            self.run_case(FakeClaude([tool_round()]), max_rounds=1)


class CorpusTests(unittest.TestCase):
    def test_current_corpus_and_stable_chunk_ids(self):
        root = Path(__file__).resolve().parents[1] / "knowledge"
        chunks = load_chunks(root)
        self.assertEqual(len({c["metadata"]["doc_id"] for c in chunks}), 5)
        self.assertEqual(len(chunks), len({c["id"] for c in chunks}))
        self.assertEqual(chunks, load_chunks(root))
        self.assertNotIn("SNAP-039", json.dumps(chunks))

    def test_archived_and_other_bench_docs_are_excluded(self):
        template = "---\ndoc_id: x\ntitle: Test\nversion: '1'\nstatus: current\nsource_type: synthetic\napplies_to: [other-bench]\nsource_ids: []\n---\n# Test\n\n## Rule\nText.\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "archived").mkdir()
            (root / "active").mkdir()
            (root / "archived" / "old.md").write_text(template.replace("other-bench", "demo-bench-v1"))
            (root / "active" / "other.md").write_text(template)
            with self.assertRaisesRegex(ValueError, "No current"):
                load_chunks(root)


if __name__ == "__main__":
    unittest.main()
