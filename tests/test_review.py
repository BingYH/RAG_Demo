import json
import unittest
from types import SimpleNamespace

from langsmith import tracing_context

from rag_demo.review import review_report


class ReviewerTests(unittest.TestCase):
    def invoke(self, decision):
        inputs = []
        def create(**kwargs):
            inputs.append(kwargs)
            return SimpleNamespace(stop_reason="tool_use", usage=SimpleNamespace(input_tokens=10, output_tokens=5),
                content=[SimpleNamespace(model_dump=lambda **_: {
                    "type": "tool_use", "name": "report_review_decision", "input": decision})])
        with tracing_context(enabled=False):
            result = review_report(SimpleNamespace(messages=SimpleNamespace(create=create)), "fake",
                {"interpretations": [{"chunk_ids": ["rule::c01"]}]}, {}, {"rule::c01": {"text": "Rule text"}})
        return result, inputs

    def test_reviewer_uses_only_referenced_knowledge_and_returns_usage(self):
        result, inputs = self.invoke({"passed": True, "issues": []})
        self.assertTrue(result["passed"])
        self.assertEqual(result["usage"], {"input_tokens": 10, "output_tokens": 5})
        context = json.loads(inputs[0]["messages"][0]["content"])
        self.assertEqual(context["knowledge"], [{"chunk_id": "rule::c01", "text": "Rule text"}])
        self.assertNotIn("expected_issue_codes", context)

    def test_inconsistent_reviewer_decision_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "inconsistent"):
            self.invoke({"passed": True, "issues": [{"code": "redundant_question", "location": "questions[0]", "message": "Known value"}]})

    def test_invalid_reviewer_schema_is_not_reported_as_diagnosis_schema_error(self):
        with self.assertRaisesRegex(RuntimeError, "invalid decision schema"):
            self.invoke({"passed": True})
