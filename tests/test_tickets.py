import copy
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from langsmith import tracing_context

from rag_demo.tickets import (TicketStore, approval_record, build_draft, content_hash,
                              render_draft, revise_draft, validate_decision)
from rag_demo.workflow import build_workflow, initial_state
from scripts.graph_bench import check_resume, check_retry
from simulator.tools import DiagnosticSession
from test_workflow import FakeClaude, FakeIndex, passed_review


class TicketIndex(FakeIndex):
    def search(self, query, top_k=5):
        result = super().search(query, top_k)
        if not self.empty_always:
            result["matches"].append({"doc_id": "support.ticket_workflow", "chunk_id": "support.ticket_workflow::c01",
                "text": "Create only after exact-content approval.", "status": "current", "applies_to": "demo-bench-v1"})
        return result


def draft_fixture():
    session = DiagnosticSession("version_mismatch")
    from rag_demo.facts import extract_facts
    evidence = {name: session.call(name, {"bench_id": "BENCH-001"}) for name in (
        "read_bench_inventory", "read_runtime_config", "read_connection_observations", "read_initialization_status")}
    facts = {f["fact_id"]: f for name, result in evidence.items() for f in extract_facts(name, result)}
    return build_draft({"facts": facts, "evidence": evidence, "question": "Investigate initialization failure.",
        "diagnosis_status": "completed", "report": {"interpretations": [], "questions": [], "next_steps": []},
        "knowledge_version": "test", "chunks": {}})


class TicketStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name) / "tickets"
        self.store = TicketStore(self.root)
        self.draft = draft_fixture()
        self.approval = approval_record("thread-a", self.draft)

    def tearDown(self):
        self.directory.cleanup()

    def count(self):
        with closing(sqlite3.connect(self.root / "tickets.sqlite3")) as connection:
            return connection.execute("SELECT count(*) FROM tickets").fetchone()[0]

    def test_no_write_without_exact_approval(self):
        for approval in ({"approved": True}, {}, approval_record("other-thread", self.draft)):
            with self.assertRaises(ValueError):
                self.store.create("thread-a", self.draft, approval)
        self.assertFalse(self.root.exists())

    def test_replay_returns_same_ticket_and_exact_approved_content(self):
        first = self.store.create("thread-a", self.draft, self.approval)
        second = self.store.create("thread-a", self.draft, approval_record("thread-a", self.draft))
        self.assertEqual(first["ticket_id"], second["ticket_id"])
        self.assertEqual(first["created_at"], second["created_at"])
        self.assertFalse(first["reused"])
        self.assertTrue(second["reused"])
        self.assertEqual(self.count(), 1)
        record = json.loads(Path(first["file_path"]).read_text(encoding="utf-8"))
        self.assertEqual(record["draft"], self.draft)
        self.assertEqual(record["draft_hash"], content_hash(self.draft))
        self.assertEqual(self.store.get(first["ticket_id"]), record)

    def test_conflicting_content_for_same_revision_does_not_overwrite(self):
        first = self.store.create("thread-a", self.draft, self.approval)
        altered = copy.deepcopy(self.draft)
        altered["title"] = "Changed without incrementing revision"
        with self.assertRaisesRegex(ValueError, "different content"):
            self.store.create("thread-a", altered, approval_record("thread-a", altered))
        self.assertEqual(self.store.get(first["ticket_id"])["draft"], self.draft)
        self.assertEqual(self.count(), 1)

    def test_export_failure_after_commit_is_repairable_without_duplicate(self):
        with patch.object(self.store, "_export", side_effect=OSError("simulated export failure")):
            with self.assertRaises(OSError):
                self.store.create("thread-a", self.draft, self.approval)
        self.assertEqual(self.count(), 1)
        receipt = TicketStore(self.root).create("thread-a", self.draft, self.approval)
        self.assertTrue(receipt["reused"])
        self.assertTrue(Path(receipt["file_path"]).is_file())
        self.assertEqual(self.count(), 1)

    def test_concurrent_replay_creates_one_record(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            receipts = list(pool.map(lambda _: TicketStore(self.root).create("thread-a", self.draft, self.approval), range(2)))
        self.assertEqual(len({r["ticket_id"] for r in receipts}), 1)
        self.assertEqual(self.count(), 1)

    def test_edit_preserves_sources_and_invalidates_old_approval(self):
        old_hash = content_hash(self.draft)
        revised = revise_draft(self.draft, {"action": "edit", "draft_hash": old_hash,
                                          "edits": {"engineer_notes": "Investigate approved recovery baseline."}})
        self.assertEqual(revised["revision"], 2)
        self.assertEqual(revised["facts"], self.draft["facts"])
        self.assertEqual(revised["completed_checks"], self.draft["completed_checks"])
        self.assertNotEqual(content_hash(revised), old_hash)
        with self.assertRaises(ValueError):
            validate_decision(revised, {"action": "approve", "draft_hash": old_hash})
        with self.assertRaises(ValueError):
            self.store.create("thread-a", revised, self.approval)

    def test_protected_fields_and_nonexplicit_approval_are_rejected(self):
        for edits in ({"facts": []}, {"revision": 99}, {"title": None}, {"title": "   "}, {}):
            with self.assertRaises(ValueError):
                revise_draft(self.draft, {"action": "edit", "draft_hash": content_hash(self.draft), "edits": edits})
        with self.assertRaises(ValueError):
            validate_decision(self.draft, "yes")

    def test_escalated_draft_never_includes_unreviewed_interpretation(self):
        draft = build_draft({"facts": {}, "evidence": {}, "question": "Need support",
            "diagnosis_status": "escalated", "report": {"interpretations": [{"text": "UNREVIEWED"}]},
            "error": "Evidence missing", "knowledge_version": "test", "chunks": {}})
        self.assertEqual(draft["interpretations"], [])
        self.assertEqual(draft["evidence_gaps"], ["Evidence missing"])
        self.assertNotIn("UNREVIEWED", render_draft(draft))


class TicketWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tracing = tracing_context(enabled=False)
        self.tracing.__enter__()
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.store = TicketStore(self.root / "tickets")
        self.config = {"configurable": {"thread_id": "ticket-thread"}, "recursion_limit": 40}

    def tearDown(self):
        self.directory.cleanup()
        self.tracing.__exit__(None, None, None)

    def start(self, saver, index=None):
        model = FakeClaude()
        app = build_workflow(model, index or TicketIndex(), DiagnosticSession("version_mismatch"), saver,
                             passed_review, self.store)
        state = app.invoke(initial_state("Please prepare support", "fake", "test-knowledge", True, "ticket-thread"), self.config)
        return app, state, model

    def test_pause_before_creation_approve_and_repeated_cli_receipt(self):
        app, state, model = self.start(InMemorySaver())
        self.assertEqual(state["status"], "awaiting_ticket_approval")
        self.assertFalse(self.store.root.exists())
        decision = {"action": "approve", "draft_hash": state["ticket_draft_hash"]}
        self.assertEqual(check_resume(app.get_state(self.config), decision, "test-knowledge", "fake"), "ticket_decision")
        result = app.invoke(Command(resume=decision), self.config)
        self.assertEqual(result["status"], "ticket_created")
        self.assertEqual(len(model.calls), 1)
        self.assertTrue(Path(result["ticket"]["file_path"]).is_file())
        self.assertEqual(check_resume(app.get_state(self.config), decision, "test-knowledge", "fake"), "existing_ticket")
        with self.assertRaises(ValueError):
            check_resume(app.get_state(self.config), {"action": "approve", "draft_hash": "stale"}, "test-knowledge", "fake")

    def test_cancel_creates_no_ticket(self):
        app, _, _ = self.start(InMemorySaver())
        result = app.invoke(Command(resume={"action": "cancel"}), self.config)
        self.assertEqual(result["status"], "ticket_cancelled")
        self.assertFalse(self.store.root.exists())
        self.assertIsNone(result["ticket_approval"])

    def test_edit_restart_and_reapprove(self):
        path = str(self.root / "checkpoint.sqlite3")
        with SqliteSaver.from_conn_string(path) as saver:
            app, state, _ = self.start(saver)
            old_hash = state["ticket_draft_hash"]
        with SqliteSaver.from_conn_string(path) as saver:
            app = build_workflow(checkpointer=saver, ticket_store=self.store)
            edited = app.invoke(Command(resume={"action": "edit", "draft_hash": old_hash,
                "edits": {"engineer_notes": "Please prioritize compatibility review."}}), self.config)
            self.assertEqual(edited["ticket_draft"]["revision"], 2)
            self.assertIsNone(edited["ticket_approval"])
            self.assertFalse(self.store.root.exists())
            with self.assertRaises(ValueError):
                check_resume(app.get_state(self.config), {"action": "approve", "draft_hash": old_hash}, "test-knowledge", "fake")
        with SqliteSaver.from_conn_string(path) as saver:
            app = build_workflow(checkpointer=saver, ticket_store=self.store)
            result = app.invoke(Command(resume={"action": "approve", "draft_hash": edited["ticket_draft_hash"]}), self.config)
            record = self.store.get(result["ticket"]["ticket_id"])
            self.assertEqual(record["draft"]["revision"], 2)
            self.assertEqual(record["draft"]["engineer_notes"], "Please prioritize compatibility review.")

    def test_committed_ticket_then_checkpoint_failure_retries_without_model(self):
        class CrashAfterCommit(TicketStore):
            def create(self, *args):
                super().create(*args)
                raise OSError("simulated crash before graph checkpoint")
        path = str(self.root / "checkpoint.sqlite3")
        with SqliteSaver.from_conn_string(path) as saver:
            app, state, _ = self.start(saver)
        with SqliteSaver.from_conn_string(path) as saver:
            app = build_workflow(checkpointer=saver, ticket_store=CrashAfterCommit(self.store.root))
            with self.assertRaises(OSError):
                app.invoke(Command(resume={"action": "approve", "draft_hash": state["ticket_draft_hash"]}), self.config)
        with SqliteSaver.from_conn_string(path) as saver:
            app = build_workflow(checkpointer=saver, ticket_store=self.store)
            check_retry(app.get_state(self.config), "test-knowledge", "fake")
            result = app.invoke(None, self.config)
            self.assertEqual(result["status"], "ticket_created")
            self.assertTrue(result["ticket"]["reused"])
            self.assertEqual(result["generation_attempts"], 1)
            with closing(sqlite3.connect(self.store.root / "tickets.sqlite3")) as connection:
                self.assertEqual(connection.execute("SELECT count(*) FROM tickets").fetchone()[0], 1)

    def test_evidence_gap_ticket_can_be_drafted_without_publishing_failed_analysis(self):
        app, state, model = self.start(InMemorySaver(), TicketIndex(empty_always=True))
        self.assertEqual(state["status"], "awaiting_ticket_approval")
        self.assertEqual(state["diagnosis_status"], "escalated")
        self.assertEqual(state["ticket_draft"]["interpretations"], [])
        self.assertTrue(state["ticket_draft"]["evidence_gaps"])
        self.assertEqual(model.calls, [])
        result = app.invoke(Command(resume={"action": "cancel"}), self.config)
        self.assertEqual(result["status"], "ticket_cancelled")


if __name__ == "__main__":
    unittest.main()
