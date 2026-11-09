import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from langsmith import tracing_context

from rag_demo.tickets import TicketStore, content_hash
from rag_demo.workflow import MOTION_QUERIES, build_workflow, initial_state
from simulator.motion import SCENARIOS
from simulator.motion_tools import MotionSession, TOOL_DESCRIPTIONS


class MotionIndex:
    def __init__(self, scope="demo-joint-response-v1", omit_section=None):
        self.scope = scope
        self.omit_section = omit_section

    def search(self, query, top_k=5):
        return {"status": "ok", "matches": [{"chunk_id": f"rule::{i}",
            "doc_id": "procedure.joint_response_test" if i < 3 else "troubleshooting.joint_response_anomalies",
            "section": section, "status": "current", "applies_to": self.scope, "text": section}
            for i, section in enumerate(MOTION_QUERIES) if section != self.omit_section]}


class MotionClaude:
    def __init__(self):
        self.messages = self
        self.contexts = []

    def create(self, **kwargs):
        context = json.loads(kwargs["messages"][0]["content"])
        self.contexts.append(copy.deepcopy(context))
        metric = next(f["fact_id"] for f in context["bound_facts"] if f["field"] == "metrics.overshoot_pct")
        payload = {"language": "en", "fact_ids": [metric], "interpretations": [{
            "text": "Use the recorded response and retain missing context.", "fact_ids": [metric],
            "chunk_ids": [context["knowledge"][0]["chunk_id"]]}], "questions": [],
            "next_steps": ["Have an engineer verify the test record."]}
        return SimpleNamespace(stop_reason="tool_use", usage=SimpleNamespace(input_tokens=10, output_tokens=5),
            content=[SimpleNamespace(model_dump=lambda **_: {"type": "tool_use", "name": "submit_analysis", "input": payload})])


def approve_review(*args, **kwargs):
    return {"passed": True, "issues": [], "usage": {"input_tokens": 1, "output_tokens": 1}}


class MotionWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tracing = tracing_context(enabled=False)
        self.tracing.__enter__()

    def tearDown(self):
        self.tracing.__exit__(None, None, None)

    def state(self, ticket=False, thread="test-motion"):
        return initial_state("Analyze this motion test", "fake", "motion-kb", ticket, thread, "joint_response")

    def test_complete_cases_collect_only_motion_tools(self):
        for scenario in SCENARIOS[:2]:
            model = MotionClaude()
            app = build_workflow(model, MotionIndex(), MotionSession(scenario), review_function=approve_review)
            result = app.invoke(self.state())
            self.assertEqual(result["status"], "completed")
            self.assertEqual(set(result["evidence"]), set(TOOL_DESCRIPTIONS))
            self.assertNotIn("clarify", result["node_history"])
            self.assertEqual(len(model.contexts), 1)
            self.assertEqual(result["task_type"], "joint_response")

    def test_wrong_scope_or_missing_requirement_escalates_without_model(self):
        for index in (MotionIndex(scope="demo-bench-v1"), MotionIndex(omit_section="Settling requirement DEMO-RESP-02")):
            model = MotionClaude()
            app = build_workflow(model, index, MotionSession(SCENARIOS[0]), review_function=approve_review)
            result = app.invoke(self.state())
            self.assertEqual(result["status"], "escalated")
            self.assertEqual(result["retrieval_attempts"], 2)
            self.assertEqual(model.contexts, [])

    def test_missing_result_tool_escalates_without_model(self):
        class FailingSession(MotionSession):
            def call(self, name, args):
                if name == "read_motion_test_results":
                    return {"status": "error", "error": {"code": "ACQUISITION_FAILED"}}
                return super().call(name, args)
        model = MotionClaude()
        result = build_workflow(model, MotionIndex(), FailingSession(SCENARIOS[0]),
                                review_function=approve_review).invoke(self.state())
        self.assertEqual(result["status"], "escalated")
        self.assertEqual(model.contexts, [])

    def test_sqlite_clarification_resume_ticket_approval_keeps_unknowns(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / "graph.sqlite3")
            store = TicketStore(Path(directory) / "tickets")
            config = {"configurable": {"thread_id": "motion-resume"}}
            model = MotionClaude()
            with SqliteSaver.from_conn_string(db) as saver:
                app = build_workflow(model, MotionIndex(), MotionSession(SCENARIOS[2]), saver, approve_review, store)
                paused = app.invoke(self.state(True, "motion-resume"), config)
                self.assertEqual(paused["status"], "awaiting_input")
                self.assertIn("负载", paused["__interrupt__"][0].value["question"])
                self.assertEqual(model.contexts, [])
                saved = copy.deepcopy(paused["evidence"])
            with SqliteSaver.from_conn_string(db) as saver:
                # No session or retriever is needed on a new process after clarification.
                app = build_workflow(model, None, None, saver, approve_review, store)
                draft_state = app.invoke(Command(resume="I do not know the payload; no record is available."), config)
                self.assertEqual(draft_state["status"], "awaiting_ticket_approval")
                self.assertEqual(draft_state["evidence"], saved)
                self.assertEqual(draft_state["node_history"].count("collect_evidence"), 1)
                self.assertEqual(draft_state["node_history"].count("clarify"), 1)
                self.assertEqual(len(model.contexts), 1)
                self.assertIn("do not know", model.contexts[0]["user_context_unverified"])
                draft = draft_state["ticket_draft"]
                self.assertEqual(draft["test_id"], "TEST-307")
                self.assertIsNone(draft["startup_attempt_id"])
                self.assertTrue(any("payload_record" in gap for gap in draft["evidence_gaps"]))
                self.assertIsNone(next(f["value"] for f in draft["facts"] if f["field"] == "equivalent_inertia"))
                self.assertFalse(list((Path(directory) / "tickets").glob("DEMO-TKT-*")))
                result = app.invoke(Command(resume={"action": "approve", "draft_hash": content_hash(draft)}), config)
                self.assertEqual(result["status"], "ticket_created")
                self.assertEqual(len(model.contexts), 1)
                self.assertEqual(len(list((Path(directory) / "tickets").glob("DEMO-TKT-*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
