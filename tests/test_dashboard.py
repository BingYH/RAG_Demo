import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from rag_demo.dashboard import DashboardService
from rag_demo.tickets import TicketStore, content_hash
from rag_demo.ui_i18n import translate
from tests.test_motion_workflow import MotionIndex
from tests.test_ros_capture import complete
from simulator.http_motion import HttpMotionSession, RosCaptureError

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


class FakeModel:
    def __init__(self):
        self.messages = self
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        name = kwargs["tools"][0]["name"]
        if name == "report_review_decision":
            payload = {"passed": True, "issues": []}
        else:
            context = json.loads(kwargs["messages"][0]["content"])
            fid = next(f["fact_id"] for f in context["bound_facts"] if f["field"] == "metrics.overshoot_pct")
            payload = {"language": "en", "fact_ids": [fid], "interpretations": [{
                "text": 'The response exceeds a limit; verify the test conditions.', "fact_ids": [fid], "chunk_ids": [context["knowledge"][0]["chunk_id"]]}],
                "questions": [], "next_steps": ['Retain unknowns for engineering review.']}
            if context.get("response_language") == "en":
                payload["language"] = "en"
                payload["interpretations"][0]["text"] = "The response exceeds the demo limit. Retain the missing test context."
                payload["next_steps"] = ["Ask an engineer to verify the missing records."]
            elif context.get("response_language") == "zh":
                payload["language"] = "zh"
                payload["interpretations"][0]["text"] = translate(payload["interpretations"][0]["text"], "zh")
                payload["next_steps"] = [translate(step, "zh") for step in payload["next_steps"]]
        return SimpleNamespace(stop_reason="tool_use", usage=SimpleNamespace(input_tokens=10, output_tokens=5),
            content=[SimpleNamespace(model_dump=lambda **_: {"type": "tool_use", "name": name, "input": payload})])


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        directory = Path(self.tmp.name)
        self.service = DashboardService(directory / "graph.sqlite3", directory / "runs", TicketStore(directory / "tickets"))
        self.model = FakeModel()
        self.service.dependencies = lambda scope: (self.model, MotionIndex(), "fake")
        self.service.tracing_client = lambda: None
        # The real index fake has the same declared version throughout this thread.
        self.index_patch = patch.object(MotionIndex, "knowledge_version", "motion-kb", create=True)
        self.index_patch.start()

    def tearDown(self):
        self.index_patch.stop()
        self.tmp.cleanup()

    def start(self, thread="ui-test"):
        return self.service.execute(thread, task_type="joint_response", scenario="joint_tracking_load_unknown",
                                    question='Analyze this test', ticket=True)

    def test_service_pause_resume_edit_stale_approval_and_idempotency(self):
        view = self.start()
        self.assertEqual(view["state"]["status"], "awaiting_input")
        self.assertEqual(self.model.calls, [])
        before = copy.deepcopy(view["state"]["evidence"])
        self.service.read("ui-test")
        self.assertEqual(self.model.calls, [])
        draft_view = self.service.execute("ui-test", decision='I do not know; retain the unknowns.')
        self.assertEqual(draft_view["state"]["evidence"], before)
        self.assertEqual(len(self.model.calls), 2)
        old_hash = content_hash(draft_view["state"]["ticket_draft"])
        edited = self.service.execute("ui-test", decision={"action": "edit", "draft_hash": old_hash,
            "edits": {"engineer_notes": "Demo review only"}})
        with self.assertRaises(ValueError):
            self.service.execute("ui-test", decision={"action": "approve", "draft_hash": old_hash})
        new_hash = content_hash(edited["state"]["ticket_draft"])
        result = self.service.execute("ui-test", decision={"action": "approve", "draft_hash": new_hash})
        self.assertEqual(result["state"]["status"], "ticket_created")
        again = self.service.execute("ui-test", decision={"action": "approve", "draft_hash": new_hash})
        self.assertEqual(result["state"]["ticket"], again["state"]["ticket"])
        self.assertEqual(len(self.model.calls), 2)
        self.assertEqual(len(list((Path(self.tmp.name) / "tickets").glob("DEMO-TKT-*.json"))), 1)

    def test_cancel_and_duplicate_start(self):
        self.start()
        with self.assertRaises(ValueError):
            self.start()
        self.service.execute("ui-test", decision='I do not know.')
        result = self.service.execute("ui-test", decision={"action": "cancel"})
        self.assertEqual(result["state"]["status"], "ticket_cancelled")
        self.assertFalse(list((Path(self.tmp.name) / "tickets").glob("DEMO-TKT-*.json")))

    def test_ui_preview_load_clarify_edit_approve_without_implicit_calls(self):
        self.start("from-cli")
        with patch("rag_demo.dashboard.DashboardService", return_value=self.service):
            app = AppTest.from_file(str(APP), default_timeout=30).run()
            self.assertFalse(app.exception)
            self.assertEqual(self.model.calls, [])
            app.text_input(key="load_id").set_value("from-cli")
            next(b for b in app.button if b.label == 'Open thread').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["active_thread"], "from-cli")
            self.assertEqual(self.model.calls, [])
            app.text_area(key="reply-from-cli").set_value('I do not know yet.')
            next(b for b in app.button if b.label == 'Submit context and continue').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(self.model.calls), 2)

            next(b for b in app.button if b.label == 'Refresh thread').click().run()
            self.assertEqual(len(self.model.calls), 2)
            next(b for b in app.button if b.label == 'Approve and create local ticket').click().run()
            self.assertTrue(any('check' in w.value for w in app.warning))
            self.assertEqual(self.service.read("from-cli")["state"]["status"], "awaiting_ticket_approval")
            digest = content_hash(self.service.read("from-cli")["state"]["ticket_draft"])
            app.text_area(key=digest + "engineer_notes").set_value("Reviewed UI demo")
            next(b for b in app.button if b.label == 'Save changes for re-approval').click().run()
            self.assertFalse(app.exception)
            digest = content_hash(self.service.read("from-cli")["state"]["ticket_draft"])
            self.assertFalse(app.checkbox(key="reviewed-" + digest).value)
            app.checkbox(key="reviewed-" + digest).check()
            next(b for b in app.button if b.label == 'Approve and create local ticket').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(self.service.read("from-cli")["state"]["status"], "ticket_created")
            self.assertEqual(len(self.model.calls), 2)

    def test_english_ui_and_workflow_preserve_draft_on_language_switch(self):
        from rag_demo.tickets import render_draft
        with patch("rag_demo.dashboard.DashboardService", return_value=self.service):
            app = AppTest.from_file(str(APP), default_timeout=30).run()
            self.assertEqual(app.selectbox(key="ui_language").value, "en")
            self.assertEqual(app.title[0].value, "From test anomalies to evidence-based action")
            app.selectbox(key="ui_language").set_value("en").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.title[0].value, "From test anomalies to evidence-based action")
            self.assertIn("Reply in English", app.text_area[0].value)
            app.selectbox(key="scenario").set_value("joint_tracking_load_unknown").run()
            next(b for b in app.button if b.label == "Start new diagnosis").click().run()
            self.assertFalse(app.exception)
            thread = app.session_state["active_thread"]
            saved = self.service.read(thread)
            self.assertEqual(saved["state"]["output_language"], "en")
            self.assertEqual(self.model.calls, [])
            self.assertIn("load context", saved["interrupts"][0]["question"])
            app.text_area(key="reply-" + thread).set_value("I do not know; retain the missing load record.")
            next(b for b in app.button if b.label == "Submit context and continue").click().run()
            self.assertFalse(app.exception)
            saved = self.service.read(thread)
            self.assertEqual(saved["state"]["report"]["language"], "en")
            self.assertTrue({"Observed facts", "Analysis and hypotheses", "Open questions and evidence gaps",
                             "Recommended next steps", "Issue details"}.issubset({item.value for item in app.subheader}))
            self.assertTrue(any(frame.value.shape[0] for frame in app.dataframe))
            self.assertIn("REQUIRED RESPONSE LANGUAGE: English", self.model.calls[0]["system"])
            draft = saved["state"]["ticket_draft"]
            self.assertEqual(draft["language"], "en")
            self.assertFalse(any("\u4e00" <= c <= "\u9fff" for c in render_draft(draft)))
            old_hash = content_hash(draft)
            app.selectbox(key="ui_language").set_value("zh").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.title[0].value, translate("From test anomalies to evidence-based action", "zh"))
            self.assertIn(translate("Observed facts", "zh"), {item.value for item in app.subheader})
            self.assertEqual(len(self.model.calls), 2)
            self.assertEqual(content_hash(self.service.read(thread)["state"]["ticket_draft"]), old_hash)
            app.selectbox(key="ui_language").set_value("en").run()
            self.assertFalse(app.exception)
            self.assertEqual(len(self.model.calls), 2)

    def test_explicit_chinese_diagnosis_keeps_optional_localized_report_and_draft(self):
        from rag_demo.tickets import render_draft
        view = self.service.execute("chinese-demo", task_type="joint_response",
            scenario="joint_tracking_load_unknown", question="Analyze this test", ticket=True, output_language="zh")
        self.assertIn(translate("The load context for this joint test is incomplete. Which tool/fixture and payload were used, did they change, and is a corresponding record available? If you do not know, please say so.", "zh"),
                      view["interrupts"][0]["question"])
        view = self.service.execute("chinese-demo", decision="Unknown; keep the evidence gap.")
        state = view["state"]
        self.assertEqual(state["status"], "awaiting_ticket_approval")
        self.assertEqual(state["report"]["language"], "zh")
        self.assertIn(translate("Facts (application-rendered)", "zh"), state["answer"])
        self.assertIn(translate("Ticket draft", "zh"), render_draft(state["ticket_draft"]))

    def ros_session(self, expected_capture_id=None):
        payload = complete().frozen
        if expected_capture_id and expected_capture_id != payload["capture_id"]:
            raise RosCaptureError("Capture changed.")
        session = object.__new__(HttpMotionSession)
        session._state = copy.deepcopy(payload["snapshot"])
        session.trajectory = copy.deepcopy(payload["trajectory"])
        session.capture_id = payload["capture_id"]
        return session

    def test_ros_source_freezes_curve_and_resumes_with_bridge_offline(self):
        captured = self.ros_session()
        with patch("rag_demo.dashboard.HttpMotionSession", return_value=captured):
            view = self.service.execute("ros-saved", task_type="joint_response", data_source="wsl_ros",
                question="Analyze the ROS replay", ticket=True, expected_capture_id=captured.capture_id)
        self.assertEqual(view["state"]["data_source"], "wsl_ros")
        self.assertEqual(view["state"]["status"], "awaiting_input")
        self.assertEqual(len(view["motion"]["rows"]), 601)
        evidence = copy.deepcopy(view["state"]["evidence"])
        with patch("rag_demo.dashboard.HttpMotionSession", side_effect=AssertionError("must not reconnect")):
            resumed = self.service.execute("ros-saved", decision="Unknown load; retain the gap.")
        self.assertEqual(resumed["state"]["evidence"], evidence)
        self.assertEqual(resumed["state"]["ticket_draft"]["data_source"], "wsl_ros")
        self.assertEqual(resumed["state"]["ticket_draft"]["source_metadata"]["capture_id"], captured.capture_id)
        self.assertEqual(len(resumed["motion"]["rows"]), 601)
        with self.assertRaises(ValueError):
            self.service.execute("ros-saved", decision={"action": "cancel"}, data_source="local_json")
        path = self.service.captures / (captured.capture_id + ".json")
        path.write_text("{}")
        damaged = self.service.read("ros-saved")
        self.assertTrue(damaged["motion_error"])
        self.assertNotIn("motion", damaged)
        self.assertEqual(damaged["state"]["evidence"], evidence)

    def test_ros_unavailable_never_constructs_model_or_local_session(self):
        with patch("rag_demo.dashboard.HttpMotionSession", side_effect=RosCaptureError("unavailable")), \
             patch.object(self.service, "dependencies", side_effect=AssertionError("model must not be created")), \
             patch("rag_demo.dashboard.MotionSession", side_effect=AssertionError("no JSON fallback")):
            with self.assertRaises(RosCaptureError):
                self.service.execute("ros-offline", task_type="joint_response", data_source="wsl_ros",
                    question="Analyze capture", expected_capture_id="0" * 32)
        self.assertFalse(self.service.read("ros-offline")["state"])

    def test_ui_ros_check_start_resume_and_no_implicit_network_on_refresh(self):
        captured = self.ros_session()
        with patch("rag_demo.dashboard.DashboardService", return_value=self.service), \
             patch.object(self.service, "fetch_ros", return_value=captured.export_capture()) as fetch, \
             patch("rag_demo.dashboard.HttpMotionSession", return_value=captured) as connect:
            app = AppTest.from_file(str(APP), default_timeout=30).run()
            app.selectbox(key="ui_language").set_value("en").run()
            app.selectbox(key="data_source").set_value("wsl_ros").run()
            self.assertFalse(app.exception)
            self.assertTrue(next(b for b in app.button if b.label == "Start new diagnosis").disabled)
            self.assertEqual(fetch.call_count, 0)
            next(b for b in app.button if b.label == "Check and load ROS capture").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(fetch.call_count, 1)
            self.assertFalse(next(b for b in app.button if b.label == "Start new diagnosis").disabled)
            next(b for b in app.button if b.label == "Start new diagnosis").click().run()
            self.assertFalse(app.exception)
            thread = app.session_state["active_thread"]
            self.assertEqual(connect.call_count, 1)
            self.assertEqual(self.model.calls, [])
            self.assertEqual(self.service.read(thread)["state"]["data_source"], "wsl_ros")
            # A changed source selector affects only the next new thread.
            app.selectbox(key="data_source").set_value("local_json").run()
            self.assertEqual(connect.call_count, 1)
            self.assertEqual(fetch.call_count, 1)
            app.text_area(key="reply-" + thread).set_value("I do not know the load.")
            next(b for b in app.button if b.label == "Submit context and continue").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(connect.call_count, 1)
            self.assertEqual(self.service.read(thread)["state"]["ticket_draft"]["data_source"], "wsl_ros")
            self.assertEqual(len(self.model.calls), 2)




if __name__ == "__main__":
    unittest.main()
