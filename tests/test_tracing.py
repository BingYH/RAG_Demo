import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from rag_demo.tracing import verify_trace


class TraceVerificationTests(unittest.TestCase):
    def test_new_trace_url_format_and_completed_steps(self):
        url = "https://eu.smith.langchain.com/o/org/projects/p/project/trace/root/run/root"
        root = SimpleNamespace(id="root", get_url=lambda: url)
        api = MagicMock()
        api.runs.query_v2.return_value = [SimpleNamespace(end_time="done")] * 3
        with patch.dict("os.environ", {"LANGSMITH_API_KEY": "test-only", "LANGSMITH_ENDPOINT": "https://example.invalid"}):
            with patch("langsmith.Langsmith", return_value=api):
                self.assertEqual(verify_trace(root, 3), url)
        self.assertEqual(api.runs.query_v2.call_args.kwargs["project_ids"], ["project"])
        self.assertEqual(api.runs.query_v2.call_args.kwargs["trace_id"], "root")

    def test_graph_verification_requires_expected_node_names(self):
        url = "https://eu.smith.langchain.com/o/org/projects/p/project/trace/root/run/root"
        root = SimpleNamespace(id="root", get_url=lambda: url)
        api = MagicMock()
        api.runs.query_v2.side_effect = [
            [SimpleNamespace(end_time="done", name="root")],
            [SimpleNamespace(end_time="done", name="root"), SimpleNamespace(end_time="done", name="bench-workflow")],
        ]
        with patch.dict("os.environ", {"LANGSMITH_API_KEY": "test-only", "LANGSMITH_ENDPOINT": "https://example.invalid"}):
            with patch("langsmith.Langsmith", return_value=api), patch("rag_demo.tracing.time.sleep"):
                self.assertEqual(verify_trace(root, 1, expected_names={"bench-workflow"}), url)
        self.assertEqual(api.runs.query_v2.call_count, 2)


if __name__ == "__main__":
    unittest.main()
