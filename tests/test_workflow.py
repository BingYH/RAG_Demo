import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from langsmith import tracing_context

from rag_demo.workflow import WORKFLOW_VERSION, build_workflow, initial_state
from scripts.graph_bench import check_resume
from simulator.tools import DiagnosticSession


class FakeIndex:
    knowledge_version = "test-knowledge"

    def __init__(self, empty_first=False, empty_always=False):
        self.calls = 0
        self.empty_first, self.empty_always = empty_first, empty_always

    def search(self, query, top_k=5):
        self.calls += 1
        docs = ("configuration.version_and_endpoint", "troubleshooting.initialization_failures",
                "bench.overview", "procedure.initialization_and_evidence")
        matches = [{"doc_id": doc, "chunk_id": doc + "::c01", "text": "An applicable demo rule.",
                    "status": "current", "applies_to": "demo-bench-v1"} for doc in docs]
        if self.empty_always or (self.empty_first and self.calls == 1):
            matches = []
        return {"status": "ok", "matches": matches}


class FakeClaude:
    def __init__(self, invalid_first=False):
        self.messages = self
        self.calls = []
        self.invalid_first = invalid_first

    def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        context = json.loads(kwargs["messages"][0]["content"])
        client = next(f["fact_id"] for f in context["bound_facts"] if f["field"] == "client_version")
        chunk = context["knowledge"][0]["chunk_id"]
        payload = {"language": "en", "fact_ids": [client], "interpretations": [{
            "text": 'Check against the configuration and compatibility rules.', "fact_ids": [client], "chunk_ids": [chunk]}],
            "questions": [], "next_steps": ['Ask an engineer to assess the next steps.']}
        if self.invalid_first and len(self.calls) == 1:
            payload = {}
        return SimpleNamespace(stop_reason="tool_use", usage=SimpleNamespace(input_tokens=10, output_tokens=5),
            content=[SimpleNamespace(model_dump=lambda **_: {"type": "tool_use", "name": "submit_analysis", "input": payload})])


def passed_review(*args, **kwargs):
    return {"passed": True, "issues": [], "usage": {"input_tokens": 2, "output_tokens": 1}, "trace_steps": 2}


def failed_review(*args, **kwargs):
    return {"passed": False, "issues": [{"code": "unsupported_claim", "location": "interpretations[0]",
        "message": "Narrow the claim."}], "usage": {"input_tokens": 2, "output_tokens": 1}, "trace_steps": 2}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.context = tracing_context(enabled=False)
        self.context.__enter__()

    def tearDown(self):
        self.context.__exit__(None, None, None)

    def run_graph(self, scenario="version_mismatch", index=None, claude=None, reviewer=passed_review):
        index, claude = index or FakeIndex(), claude or FakeClaude()
        app = build_workflow(claude, index, DiagnosticSession(scenario), review_function=reviewer)
        result = app.invoke(initial_state("Check bench", "fake", index.knowledge_version))
        return result, claude, index

    def test_version_path_is_an_explicit_graph(self):
        result, claude, _ = self.run_graph()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["node_history"], ["collect_evidence", "retrieve_knowledge", "check_evidence",
            "generate_report", "validate_report", "review_report", "finalize"])
        self.assertEqual(result["usage"], {"input_tokens": 12, "output_tokens": 6})
        self.assertIn('Installed client version: "2.0.0" [EV-026-02]', result["answer"])
        self.assertIn('Registered expected client version: "1.4.0" [EV-026-01]', result["answer"])
        self.assertEqual(len(claude.calls), 1)

    def test_healthy_path_does_not_force_clarification(self):
        result, _, _ = self.run_graph("healthy")
        self.assertEqual(result["status"], "completed")
        self.assertNotIn("clarify", result["node_history"])
        self.assertEqual(set(result["required_docs"]), {"bench.overview", "procedure.initialization_and_evidence"})

    def test_retrieval_retries_once_then_succeeds(self):
        result, _, _ = self.run_graph(index=FakeIndex(empty_first=True))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["retrieval_attempts"], 2)
        self.assertEqual(result["node_history"].count("refine_query"), 1)

    def test_empty_retrieval_escalates_without_model(self):
        result, claude, index = self.run_graph(index=FakeIndex(empty_always=True))
        self.assertEqual(result["status"], "escalated")
        self.assertEqual(result["retrieval_attempts"], 2)
        self.assertEqual(index.calls, 3)  # One initial query, then two focused queries.
        self.assertEqual(claude.calls, [])

    def test_tool_acquisition_failure_is_not_diagnosed_as_product_failure(self):
        class FailingSession(DiagnosticSession):
            def call(self, name, arguments):
                if name == "read_runtime_config":
                    return {"status": "error", "error": {"code": "ACQUISITION_FAILED"}}
                return super().call(name, arguments)
        claude = FakeClaude()
        app = build_workflow(claude, FakeIndex(), FailingSession("version_mismatch"), review_function=passed_review)
        result = app.invoke(initial_state("Check bench", "fake", "test-knowledge"))
        self.assertEqual(result["status"], "escalated")
        self.assertIn("observations could not be acquired", result["error"])
        self.assertEqual(claude.calls, [])

    def test_archived_retrieval_cannot_satisfy_coverage(self):
        class ArchivedIndex(FakeIndex):
            def search(self, query, top_k=5):
                result = super().search(query, top_k)
                for match in result["matches"]:
                    match["status"] = "archived"
                return result
        result, claude, _ = self.run_graph(index=ArchivedIndex())
        self.assertEqual(result["status"], "escalated")
        self.assertEqual(result["chunks"], {})
        self.assertEqual(claude.calls, [])

    def test_schema_correction_then_success(self):
        result, claude, _ = self.run_graph(claude=FakeClaude(invalid_first=True))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["corrections"], 1)
        self.assertEqual(result["generation_attempts"], 2)
        context = json.loads(claude.calls[1]["messages"][0]["content"])
        self.assertIn("language", context["correction_feedback"])

    def test_review_failure_corrects_once(self):
        decisions = iter([failed_review(), passed_review()])
        result, _, _ = self.run_graph(reviewer=lambda *a, **kw: next(decisions))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["corrections"], 1)
        self.assertEqual(len(result["evidence_reviews"]), 2)
        self.assertEqual(result["usage"]["input_tokens"], 24)

    def test_repeated_review_failure_does_not_publish_draft(self):
        result, _, _ = self.run_graph(reviewer=failed_review)
        self.assertEqual(result["status"], "escalated")
        self.assertEqual(result["generation_attempts"], 2)
        self.assertNotIn('Facts (application-rendered)', result["answer"])
        self.assertNotIn("finalize", result["node_history"])

    def test_sqlite_pause_and_fresh_graph_resume_uses_saved_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "state.sqlite3")
            config = {"configurable": {"thread_id": "test-thread"}}
            first_model = FakeClaude()
            with SqliteSaver.from_conn_string(path) as saver:
                app = build_workflow(first_model, FakeIndex(), DiagnosticSession("connection_timeout"), saver, passed_review)
                result = app.invoke(initial_state("Check bench", "fake", "test-knowledge"), config)
                self.assertTrue(result["__interrupt__"])
                self.assertEqual(first_model.calls, [])
                saved = copy.deepcopy(app.get_state(config).values["evidence"])
            # New checkpointer connection + new compiled graph, without a fixture session.
            second_model = FakeClaude()
            with SqliteSaver.from_conn_string(path) as saver:
                app = build_workflow(second_model, None, None, saver, passed_review)
                snapshot = app.get_state(config)
                check_resume(snapshot, 'I do not know yet.', "test-knowledge", "fake")
                result = app.invoke(Command(resume='I do not know yet.'), config)
                self.assertEqual(result["status"], "completed")
                self.assertEqual(result["evidence"], saved)
                self.assertEqual(result["node_history"].count("collect_evidence"), 1)
                self.assertEqual(result["node_history"].count("retrieve_knowledge"), 1)
                self.assertEqual(result["user_context"], 'I do not know yet.')
                self.assertIsNone(next(f["value"] for f in result["facts"].values()
                                      if f["field"] == "controller_version"))
                self.assertEqual(json.loads(second_model.calls[0]["messages"][0]["content"])["user_context_unverified"], 'I do not know yet.')
                with self.assertRaisesRegex(ValueError, "not waiting"):
                    check_resume(app.get_state(config), "again", "test-knowledge", "fake")

    def test_resume_rejects_version_drift_and_empty_reply(self):
        state = initial_state("Question", "fake", "kb")
        state["status"] = "awaiting_input"
        snapshot = SimpleNamespace(values=state, next=("clarify",))
        for kb, model, reply in [("changed", "fake", "reply"), ("kb", "changed", "reply"), ("kb", "fake", " ")]:
            with self.assertRaises(ValueError):
                check_resume(snapshot, reply, kb, model)
        state["workflow_version"] = WORKFLOW_VERSION + "-changed"
        with self.assertRaisesRegex(ValueError, "Workflow version changed"):
            check_resume(snapshot, "reply", "kb", "fake")


if __name__ == "__main__":
    unittest.main()
