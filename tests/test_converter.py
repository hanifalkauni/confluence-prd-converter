"""
Unit Tests for Confluence PRD Converter.
Verifies parsing of HTML exports, Storage XML, Draw.io diagrams, nested tables,
Jira lozenges, Figma/Miro embeds, image mappings, and document integrity validation.
"""

import unittest
from pathlib import Path
import sys

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.clean import is_system_icon, clean_text
from core.confluence_client import extract_page_id_from_url
from core.formatters import format_jira_macro, format_embed_iframe
from core.parser import ConfluencePRDParser
from core.validator import PRDValidator


class TestConfluenceConverter(unittest.TestCase):

    def setUp(self):
        self.tests_dir = Path(__file__).parent
        self.sample_html_path = self.tests_dir / "sample_prd.html"
        self.sample_xml_path = self.tests_dir / "sample_storage.xml"

    def test_extract_page_id(self):
        # Pure numeric
        self.assertEqual(extract_page_id_from_url("1766097385"), "1766097385")
        # Action URL
        self.assertEqual(
            extract_page_id_from_url("https://wiki.example.com/pages/viewpage.action?pageId=1766097385"),
            "1766097385"
        )
        # Release / space action URL
        self.assertEqual(
            extract_page_id_from_url("https://wiki.example.com/pages/releaseview.action?pageId=1776167017"),
            "1776167017"
        )
        # Display URL with query
        self.assertEqual(
            extract_page_id_from_url("https://wiki.example.com/display/PROD/My+PRD?pageId=99887766"),
            "99887766"
        )
        # REST API URL
        self.assertEqual(
            extract_page_id_from_url("https://wiki.example.com/rest/api/content/55443322"),
            "55443322"
        )

    def test_system_icon_filter(self):
        self.assertTrue(is_system_icon("epic.svg"))
        self.assertTrue(is_system_icon("/images/icons/viewavatar?avatarId=100"))
        self.assertTrue(is_system_icon("default.svg"))
        self.assertFalse(is_system_icon("profile_main_view.png"))
        self.assertFalse(is_system_icon("architecture_flowchart.jpg"))
        self.assertFalse(is_system_icon("Frontend Architecture.png"))

    def test_html_conversion(self):
        with open(self.sample_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        parser = ConfluencePRDParser(assets_folder="assets", preserve_nested_tables=True)
        md_output = parser.parse_html(html_content, title="[PRD] User Profile & Notification Service")

        # 1. Verify H1 Title
        self.assertIn("# [PRD] User Profile & Notification Service", md_output)

        # 2. Verify Callout Alerts (Note, Warning, Tip)
        self.assertIn("> [!NOTE]", md_output)
        self.assertIn("> [!WARNING]", md_output)
        self.assertIn("> [!TIP]", md_output)

        # 3. Verify Jira issue extraction
        self.assertIn("[PROJ-1042](https://jira.example.com/browse/PROJ-1042)", md_output)
        self.assertIn("- User Profile Revamp & Notification Engine", md_output)
        self.assertIn("`IN PROGRESS`", md_output)

        # 4. Verify Figma & Miro embeds
        self.assertIn("[Figma Design](https://www.figma.com/file/AbCdEf12345/Platform-Design-System?node-id=10:25)", md_output)
        self.assertIn("[Miro Board](https://miro.com/app/board/uXjVO987654=/)", md_output)

        # 5. Verify nested table converted to compact HTML <table> inside markdown
        self.assertIn("<table><tr><th>Field</th><th>Validation Rule</th></tr>", md_output)
        self.assertIn("<table><tr><th>Event Name</th><th>Captured Attributes</th></tr>", md_output)

        # 6. Verify image mapping & system icon exclusion
        self.assertIn("![Profile Main View Screen](./assets/profile_main_view.png)", md_output)
        self.assertIn("![Edit Modal Dialog](./assets/edit_modal_dialog.png)", md_output)
        self.assertNotIn("epic.svg", md_output)

        # 7. Verify Code Block
        self.assertIn("```sql", md_output)
        self.assertIn("CREATE TABLE user_profiles", md_output)

        # 8. Verify Task List
        self.assertIn("- [x] API contract finalized", md_output)
        self.assertIn("- [ ] Perform automated security", md_output)

        # 9. Verify Comments and Discussions Conversion
        self.assertIn("## 💬 Discussions & Page Comments", md_output)
        self.assertIn("Alex Morgan (Tech Lead)", md_output)
        self.assertIn("E.164 standard formatting", md_output)
        self.assertIn("Sarah Jenkins (Security)", md_output)

    def test_comments_formatting(self):
        parser = ConfluencePRDParser()
        sample_comments = [
            {
                "author": "Alfajri Kusuma",
                "date": "2026-07-13T08:48:56.749Z",
                "body_view": "<p>For API Gateway, use existing <strong>api-b2b</strong>.</p>"
            }
        ]
        formatted = parser.format_comments_section(sample_comments)
        self.assertIn("## 💬 Discussions & Page Comments", formatted)
        self.assertIn("> 👤 **Alfajri Kusuma** — *2026-07-13 08:48:56 UTC*", formatted)
        self.assertIn("> For API Gateway, use existing **api-b2b**.", formatted)

    def test_storage_xml_conversion(self):
        with open(self.sample_xml_path, "r", encoding="utf-8") as f:
            xml_content = f.read()

        parser = ConfluencePRDParser(assets_folder="assets")
        md_output = parser.parse_storage_xml(xml_content, title="Unified Payment & Notification Engine PRD")

        # 1. Verify Title
        self.assertIn("# Unified Payment & Notification Engine PRD", md_output)

        # 2. Verify Callouts
        self.assertIn("> [!NOTE]", md_output)
        self.assertIn("> [!WARNING]", md_output)

        # 3. Verify Jira keys and statuses in tables
        self.assertIn("[PAY-501](https://jira.atlassian.com/browse/PAY-501)", md_output)
        self.assertIn("`ACTIVE`", md_output)
        self.assertIn("[PAY-502](https://jira.atlassian.com/browse/PAY-502)", md_output)
        self.assertIn("`IN REVIEW`", md_output)

        # 4. Verify Draw.io diagram macro
        self.assertIn("![Draw.io Diagram: Core-Architecture-Flow](./assets/Core-Architecture-Flow.png)", md_output)

        # 5. Verify Image attachment
        self.assertIn("payment_flow_v2.png", md_output)

        # 6. Verify Figma widget embed
        self.assertIn("[Figma Design](https://www.figma.com/file/SampleFigma123/Checkout-Flow)", md_output)

        # 7. Verify Code Block
        self.assertIn("```json", md_output)
        self.assertIn("tx_99881100", md_output)

        # 8. Verify Nested Subtable
        self.assertIn("<table><tr><th>Parameter</th><th>Default</th></tr>", md_output)

        # 9. Verify Confluence Page Link
        self.assertIn("[Security Architecture Guidelines](#security-architecture-guidelines)", md_output)

        # 10. Verify Checklist
        self.assertIn("- [x] Finalize ISO-20022", md_output)
        self.assertIn("- [ ] Conduct automated performance", md_output)

    def test_validator(self):
        sample_md = """# Sample PRD Document

> [!NOTE]
> System Overview and High Level Architecture

| Story | Criteria & Config | Status |
| --- | --- | --- |
| [PROJ-101](https://jira.example.com/browse/PROJ-101) | <table><tr><th>Param</th><th>Value</th></tr><tr><td>timeout</td><td>30s</td></tr></table> | `DONE` |

![Draw.io Architecture Diagram](https://example.com/diagram.png)
"""
        validator = PRDValidator()
        report = validator.validate_content(sample_md)

        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["metrics"]["total_tables"], 1)
        self.assertEqual(report["metrics"]["total_images"], 1)
        self.assertEqual(report["metrics"]["jira_links"], 1)


if __name__ == "__main__":
    unittest.main()
