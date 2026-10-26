#!/usr/bin/env python3
"""
Standalone CLI Validator for PRD Markdown files.
"""

import sys
import os
import json
import argparse
from pathlib import Path

# Configure UTF-8 encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.validator import PRDValidator
from core.security import assert_not_sensitive_path


def main():
    parser = argparse.ArgumentParser(
        description="PRD Markdown Validator - Verify tables, images, Jira links, and tags"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to prd.md file to validate"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON report"
    )

    args = parser.parse_args()
    file_path = Path(args.input).resolve()

    try:
        assert_not_sensitive_path(file_path)
    except PermissionError as e:
        print(f"[-] Security Error: {e}")
        sys.exit(1)

    validator = PRDValidator(base_dir=str(file_path.parent))
    report = validator.validate_file(str(file_path))

    if args.json:
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["status"] != "failed" else 1)

    print("\n========================================================")
    print(f" 🔍 PRD Markdown Integrity Report [{report['status'].upper()}]")
    print("========================================================\n")
    print(f"Target File: {file_path}")

    metrics = report.get("metrics", {})
    print(f" • Total Lines       : {metrics.get('total_lines', 0)}")
    print(f" • Total Words       : {metrics.get('total_words', 0)}")
    print(f" • Tables Count      : {metrics.get('total_tables', 0)}")
    print(f" • Images Count      : {metrics.get('total_images', 0)}")
    print(f" • Jira Links        : {metrics.get('jira_links', 0)}")
    print(f" • Figma Embeds      : {metrics.get('figma_embeds', 0)}")
    print(f" • Miro Embeds       : {metrics.get('miro_embeds', 0)}")

    if report.get("warnings"):
        print("\n⚠️ Warnings:")
        for w in report["warnings"]:
            print(f"  - {w}")

    if report.get("errors"):
        print("\n❌ Errors:")
        for err in report["errors"]:
            print(f"  - {err}")
        sys.exit(1)

    print("\n✅ Document validation passed successfully!\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
