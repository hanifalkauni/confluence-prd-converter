#!/usr/bin/env python3
"""Tests for related-pages discovery, config settings, and security hardening."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import inspect

from core import settings
from core.confluence_client import ConfluenceClient, extract_internal_page_refs
from core.parser import ConfluencePRDParser
from core.related import md_safe, format_related_section
from core.security import (
    assert_not_sensitive_path,
    is_within_directory,
    sanitize_subfolder_name,
)
from core.validator import PRDValidator
from server import fetch_and_convert_from_confluence, find_related_confluence_pages

ROOT = Path(__file__).parent.parent


def make_client():
    with patch(
        "core.confluence_client._discover_configured_credentials",
        return_value=("https://wiki.trusted-corp.com", "TOKEN_XYZ_123")
    ):
        return ConfluenceClient()


class TestRelatedPages(unittest.TestCase):
    def test_default_off_and_opt_in_signature(self):
        sig = inspect.signature(fetch_and_convert_from_confluence)
        self.assertIs(sig.parameters["include_related_pages"].default, False)
        self.assertIn("OPT-IN ONLY", find_related_confluence_pages.__doc__ or "")

    def test_cql_escape_blocks_injection(self):
        escaped = ConfluenceClient._cql_escape('x" OR space = "SECRET\\')
        self.assertNotIn('" OR', escaped.replace('\\"', ''))
        self.assertTrue(escaped.endswith("\\\\"))
        self.assertNotIn("\n", ConfluenceClient._cql_escape("a\nb"))

    def test_limit_clamp(self):
        self.assertEqual(ConfluenceClient._clamp_limit(9999), 50)
        self.assertEqual(ConfluenceClient._clamp_limit(-5), 1)
        self.assertEqual(ConfluenceClient._clamp_limit("abc"), 10)

    def test_extract_internal_page_refs(self):
        content = (
            '<ac:link><ri:page ri:content-title="API Spec" ri:space-key="PAY" /></ac:link>'
            '<a href="/pages/viewpage.action?pageId=123456">x</a>'
        )
        refs = extract_internal_page_refs(content)
        self.assertIn({"title": "API Spec", "space_key": "PAY"}, refs)
        self.assertIn({"page_id": "123456", "title": ""}, refs)

    def test_markdown_injection_neutralized(self):
        evil = "Title](http://evil) <script>alert(1)</script>\n* bullet"
        safe = md_safe(evil)
        self.assertNotIn("<script>", safe)
        self.assertNotRegex(safe, r"(?<!\\)\]")          # every ']' is backslash-escaped
        self.assertNotRegex(safe, r"(?<!\\)[<>*]")
        self.assertNotIn("\n", safe)

    def test_format_related_section(self):
        md = format_related_section([
            {"relation": "child", "page_id": "2", "title": "Child [x]", "url": "https://w/p?pageId=2"},
            {"relation": "parent", "page_id": "1", "title": "Parent", "url": "https://w/p?pageId=1"},
        ])
        self.assertIn("Related Confluence Documents", md)
        self.assertLess(md.index("Parent"), md.index("Sub-pages"))
        self.assertIn("Child \\[x\\]", md)

    def test_find_related_pages_flow_and_dedup(self):
        client = make_client()
        seen_paths = []

        def fake_get_json(path):
            seen_paths.append(path)
            if "expand=ancestors" in path:
                return {"ancestors": [{"id": "10"}, {"id": "100", "title": "Parent"}]}
            if "/child/page" in path:
                return {"results": [{"id": "112", "title": "Child"}, {"id": "bad;id", "title": "Evil"}]}
            if path.endswith("/label"):
                return {"results": [{"name": 'pay"ments'}]}
            if "search?cql=" in path:
                cql = urllib.parse.unquote(path.split("cql=")[1].split("&limit")[0])
                if cql.startswith("link ="):
                    return {"results": [{"id": "112", "title": "Child dup"}, {"id": "300", "title": "Backlink"}]}
                if cql.startswith("label IN"):
                    self.assertIn('pay\\"ments', cql)
                    return {"results": [{"id": "400", "title": "Same label", "space": {"key": "PAY"}}]}
                return {"results": [{"id": "500", "title": "Resolved by title"}]}
            return None

        page = {
            "page_id": "111", "title": "Main", "space_key": "PAY",
            "storage_xml": '<ri:page ri:content-title="Linked Doc" ri:space-key="PAY" />'
        }
        with patch.object(client, "fetch_page", return_value=page), \
             patch.object(client, "_get_json", side_effect=fake_get_json):
            result = client.find_related_pages("111", ["parent", "children", "linked", "backlinks", "labels", "bogus"], 9999)

        ids = [r["page_id"] for r in result["related_pages"]]
        self.assertEqual(len(ids), len(set(ids)))          # de-duplicated
        self.assertNotIn("", ids)                          # non-numeric IDs dropped
        self.assertEqual(ids[0], "100")                    # parent first
        self.assertEqual(result["related_pages"][0]["relation"], "parent")
        self.assertIn("112", ids)
        self.assertIn("500", ids)
        self.assertTrue(all(r["url"].startswith("https://wiki.trusted-corp.com/") for r in result["related_pages"]))
        self.assertTrue(any("limit=50" in p for p in seen_paths))   # clamped

    def test_unlisted_relation_types_are_ignored(self):
        client = make_client()
        with patch.object(client, "fetch_page", return_value={"page_id": "1", "title": "T", "space_key": "S"}), \
             patch.object(client, "_get_json", return_value=None) as g:
            res = client.find_related_pages("1", ["rm -rf", "evil"], 5)
        self.assertEqual(res["related_pages"], [])
        g.assert_not_called()


class TestSettings(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("CONFLUENCE_PRD_CONFIG", None)
        settings.reload_config()

    def _load(self, data):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "cfg.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            os.environ["CONFLUENCE_PRD_CONFIG"] = str(p)
            settings.reload_config()
            return settings.load_config(), settings.get_jira_base_url(), settings.get_verify_ssl(), settings.get_timeout()

    def test_placeholders_ignored_and_shipped_config_safe(self):
        os.environ["CONFLUENCE_PRD_CONFIG"] = str(ROOT / "confluence-prd-converter.config.json")
        settings.reload_config()
        self.assertEqual(settings.get_jira_base_url(), "")
        self.assertEqual(settings.jira_issue_url("A-1"), "https://jira.atlassian.com/browse/A-1")
        self.assertTrue(settings.get_verify_ssl())

    def test_real_values_apply(self):
        cfg, jira, verify, timeout = self._load({
            "confluence": {"verify_ssl": False, "timeout_seconds": 5},
            "formatting": {"jira_base_url": "https://jira.acme.io/", "table_mode": "text"},
            "related": {"default_limit": 9999, "default_relation_types": ["labels", "nope"]},
        })
        self.assertEqual(jira, "https://jira.acme.io")
        self.assertFalse(verify)
        self.assertEqual(timeout, 5.0)
        self.assertEqual(settings.get_table_mode(), "text")
        rel = settings.get_related_defaults()
        self.assertEqual(rel["limit"], 50)
        self.assertEqual(rel["relation_types"], ["labels"])

    def test_credentials_never_read_from_config(self):
        cfg, *_ = self._load({"confluence": {"url": "https://evil.example.com", "pat": "SECRET"}})
        self.assertNotIn("url", cfg["confluence"])
        self.assertNotIn("pat", cfg["confluence"])

    def test_bad_types_fall_back(self):
        self._load({"confluence": {"verify_ssl": "no", "timeout_seconds": "x"}, "formatting": {"jira_base_url": "javascript:alert(1)"}})
        self.assertTrue(settings.get_verify_ssl())
        self.assertEqual(settings.get_timeout(), 30.0)
        self.assertEqual(settings.get_jira_base_url(), "")

    def test_jira_link_uses_config(self):
        self._load({"formatting": {"jira_base_url": "https://jira.acme.io"}})
        xml = '<ac:structured-macro ac:name="jira"><ac:parameter ac:name="key">ABC-7</ac:parameter></ac:structured-macro>'
        md = ConfluencePRDParser().parse_storage_xml(xml, title="T")
        self.assertIn("https://jira.acme.io/browse/ABC-7", md)


class TestParserPageLinks(unittest.TestCase):
    XML = '<p><ac:link><ri:page ri:content-title="Security Guide" ri:space-key="SEC" /></ac:link></p>'

    def test_real_link_with_base_url(self):
        md = ConfluencePRDParser(base_url="https://wiki.corp.com", space_key="PAY").parse_storage_xml(self.XML)
        self.assertIn("(https://wiki.corp.com/display/SEC/Security+Guide)", md)

    def test_space_fallback_to_current_space(self):
        xml = '<p><ac:link><ri:page ri:content-title="A B" /></ac:link></p>'
        md = ConfluencePRDParser(base_url="https://wiki.corp.com", space_key="PAY").parse_storage_xml(xml)
        self.assertIn("(https://wiki.corp.com/display/PAY/A+B)", md)

    def test_legacy_anchor_without_base_url(self):
        md = ConfluencePRDParser().parse_storage_xml(self.XML)
        self.assertIn("(#security-guide)", md)


class TestHardening(unittest.TestCase):
    def test_security_helpers(self):
        with self.assertRaises(PermissionError):
            assert_not_sensitive_path(Path("id_rsa.pem"))
        with self.assertRaises(PermissionError):
            assert_not_sensitive_path(Path(".env"))
        assert_not_sensitive_path(Path("prd.md"))
        self.assertEqual(sanitize_subfolder_name("../../x"), "x")
        self.assertEqual(sanitize_subfolder_name(".git"), "assets")

    def test_validator_does_not_probe_outside_doc_dir(self):
        with tempfile.TemporaryDirectory() as d:
            md = "# T\n\n![x](../../../../Windows/win.ini)\n"
            report = PRDValidator().validate_content(md, doc_dir=d)
            joined = " ".join(report["warnings"])
            self.assertIn("outside the document directory", joined)
            self.assertNotIn("not found on disk", joined)
            self.assertTrue(is_within_directory(Path(d), Path(d) / "a.png"))
            self.assertFalse(is_within_directory(Path(d), Path(d) / ".." / "a.png"))

    def _run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_converter.py"), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60
        )

    def test_cli_rejects_sensitive_output_and_input(self):
        with tempfile.TemporaryDirectory() as d:
            html = Path(d) / "page.html"
            html.write_text("<html><body><h1>Hi</h1></body></html>", encoding="utf-8")
            bad_out = Path(d) / "overwrite.py"
            r = self._run_cli("--input", str(html), "--output", str(bad_out))
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse(bad_out.exists())

            secret = Path(d) / "secrets.json"
            secret.write_text("{}", encoding="utf-8")
            r2 = self._run_cli("--input", str(secret))
            self.assertNotEqual(r2.returncode, 0)

            # Test validate_output.py CLI as well
            val_proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "validate_output.py"), "--input", str(secret)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60
            )
            self.assertNotEqual(val_proc.returncode, 0)
            self.assertIn("Security Error", val_proc.stdout)

    def test_cli_local_conversion_ok_and_assets_dir_sanitized(self):
        with tempfile.TemporaryDirectory() as d:
            html = Path(d) / "page.html"
            html.write_text("<html><body><h1>Hi</h1><img src='a.png'></body></html>", encoding="utf-8")
            out = Path(d) / "out.md"
            r = self._run_cli("--input", str(html), "--output", str(out), "--assets-dir", "../../escape", "--related")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            text = out.read_text(encoding="utf-8")
            self.assertNotIn("..", text)
            self.assertNotIn("Related Confluence Documents", text)   # related only for live pages


if __name__ == "__main__":
    unittest.main()
