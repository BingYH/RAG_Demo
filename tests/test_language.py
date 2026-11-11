import unittest

from scripts.check_language import audit_text


class LanguagePolicyTests(unittest.TestCase):
    def test_project_prose_is_checked_but_vendor_and_catalog_are_exempt(self):
        prose = chr(0x4e2d) + chr(0x6587)
        self.assertTrue(audit_text("docs/example.md", prose))
        self.assertEqual(audit_text("references/repos/vendor/README.md", prose), [])
        self.assertEqual(audit_text("rag_demo/ui_i18n.py", prose), [])
        self.assertEqual(audit_text("docs/interview_demo/Chinese/speaker_notes.md", prose), [])
        self.assertEqual(audit_text("docs/interview_demo/Chinese/README.md", prose), [])
        self.assertEqual(audit_text("docs/interview_demo/Chinese/run_of_show.md", prose), [])
        self.assertTrue(audit_text("docs/interview_demo/speaker_notes.md", prose))
        self.assertTrue(audit_text("docs/interview_demo/run_of_show.md", prose))

    def test_escaped_prose_is_checked_and_unicode_range_bounds_are_allowed(self):
        self.assertTrue(audit_text("example.py", 'message = "\\u4e2d\\u6587"'))
        self.assertEqual(audit_text("example.py", 'lower = "\\u4e00"; upper = "\\u9fff"'), [])


if __name__ == "__main__":
    unittest.main()
