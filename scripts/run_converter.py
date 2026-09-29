#!/usr/bin/env python3
"""
Standalone CLI Runner for Confluence PRD Converter.
Supports executing conversions from any terminal, script, or non-MCP AI agent.
"""

import sys
import os
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

from core.confluence_client import ConfluenceClient, extract_page_id_from_url
from core.parser import ConfluencePRDParser
from core.validator import PRDValidator


def main():
    parser = argparse.ArgumentParser(
        description="Confluence PRD Converter - Transform Confluence Pages & HTML exports to pristine prd.md"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Confluence page URL, numeric Page ID, path to local .html export file, or XML file"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Path for output prd.md file (default: ./prd.md or [name].prd.md)"
    )
    parser.add_argument(
        "--pat",
        default=None,
        help="Confluence Personal Access Token (defaults to CONFLUENCE_PAT env or mcp_config.json)"
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Confluence Base URL (defaults to CONFLUENCE_URL env or mcp_config.json)"
    )
    parser.add_argument(
        "--assets-dir", "-a",
        default=None,
        help="Custom assets subfolder for images"
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Do not download images for live Confluence page fetch"
    )
    parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Do not include page discussions and comments"
    )
    parser.add_argument(
        "--storage-xml",
        action="store_true",
        help="Treat input file as Confluence Storage XML"
    )
    parser.add_argument(
        "--table-mode",
        choices=["table", "text"],
        default="table",
        help="Table conversion mode: 'table' (Markdown table) or 'text' (structured text/list format)"
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip post-conversion markdown validation"
    )

    args = parser.parse_args()
    input_val = args.input.strip()

    print("\n========================================================")
    print(" 🚀 Confluence PRD Converter (Universal Multi-Agent)")
    print("========================================================\n")

    input_path = Path(input_val)

    # 1. Local HTML or Storage XML File Mode
    if input_path.exists() and input_path.is_file():
        print(f"[*] Mode: Local File Processing -> '{input_path.name}' (Table Mode: {args.table_mode})")
        with open(input_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        out_file = Path(args.output) if args.output else input_path.parent / f"{input_path.stem}.prd.md"
        out_file.parent.mkdir(parents=True, exist_ok=True)

        assets_dir_name = args.assets_dir or f"{input_path.stem}_files"
        parser_engine = ConfluencePRDParser(assets_folder=assets_dir_name, table_mode=args.table_mode)

        if args.storage_xml or input_path.suffix.lower() == ".xml":
            print("[*] Parsing Confluence Storage XML...")
            md_out = parser_engine.parse_storage_xml(content, title=input_path.stem)
        else:
            print("[*] Parsing Confluence HTML Export...")
            md_out = parser_engine.parse_html(content, title=input_path.stem)

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(md_out)

        print(f"[+] Output written to: {out_file}")

    # 2. Live Confluence URL or Page ID Mode
    else:
        print(f"[*] Mode: Live Confluence Fetch -> '{input_val}' (Table Mode: {args.table_mode})")
        try:
            client = ConfluenceClient(base_url=args.url, pat=args.pat)
            if not client.base_url:
                print("[-] Error: Confluence URL not provided or found in config.")
                sys.exit(1)

            print(f"[*] Target Confluence Base URL: {client.base_url}")
            page_data = client.fetch_page(input_val)
            page_id = page_data["page_id"]
            title = page_data["title"]
            print(f"[+] Found Page: '{title}' (ID: {page_id})")

            out_file = Path(args.output) if args.output else Path.cwd() / "prd.md"
            out_file.parent.mkdir(parents=True, exist_ok=True)

            assets_dir_name = args.assets_dir or "assets"
            local_assets_dir = out_file.parent / assets_dir_name

            if not args.no_images:
                print(f"[*] Downloading image attachments to: '{local_assets_dir}'...")
                downloaded = client.download_attachments(page_id, str(local_assets_dir))
                print(f"[+] Downloaded {len(downloaded)} images.")

            parser_engine = ConfluencePRDParser(assets_folder=assets_dir_name, table_mode=args.table_mode)
            if page_data.get("storage_xml"):
                md_out = parser_engine.parse_storage_xml(page_data["storage_xml"], title=title)
            else:
                md_out = parser_engine.parse_html(page_data.get("view_html", ""), title=title)

            # Fetch comments if requested
            if not args.no_comments:
                print("[*] Fetching page discussions and comments...")
                comments = client.fetch_comments(page_id)
                if comments:
                    print(f"[+] Found {len(comments)} comments. Appending to markdown...")
                    comments_md = parser_engine.format_comments_section(comments)
                    if comments_md:
                        md_out = md_out.rstrip() + "\n\n" + comments_md

            with open(out_file, "w", encoding="utf-8") as f:
                f.write(md_out)

            print(f"[+] Output written to: {out_file}")

        except Exception as e:
            print(f"[-] Error during live fetch: {e}")
            sys.exit(1)

    # 3. Validation
    if not args.no_validate:
        print("\n[*] Validating output markdown integrity...")
        validator = PRDValidator(base_dir=str(out_file.parent))
        report = validator.validate_file(str(out_file))

        metrics = report.get("metrics", {})
        print(f"\n--- Validation Report [{report.get('status', 'unknown').upper()}] ---")
        print(f" • Total Lines   : {metrics.get('total_lines', 0)}")
        print(f" • Total Words   : {metrics.get('total_words', 0)}")
        print(f" • Tables Count  : {metrics.get('total_tables', 0)}")
        print(f" • Images Count  : {metrics.get('total_images', 0)}")
        print(f" • Jira Links    : {metrics.get('jira_links', 0)}")
        print(f" • Figma Embeds  : {metrics.get('figma_embeds', 0)}")
        print(f" • Miro Embeds   : {metrics.get('miro_embeds', 0)}")

        if report.get("warnings"):
            print("\n[!] Warnings:")
            for w in report["warnings"]:
                print(f"   - {w}")

        if report.get("errors"):
            print("\n[X] Errors:")
            for err in report["errors"]:
                print(f"   - {err}")

    print("\n✅ Conversion completed successfully!\n")


if __name__ == "__main__":
    main()
