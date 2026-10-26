#!/usr/bin/env python3
"""
Confluence PRD Converter - FastMCP Server
Universal Model Context Protocol Server providing automated Confluence PRD extraction,
transformation to pristine Markdown (prd.md), asset resolution, and structural validation.
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List

# Universal MCP import supporting mcp 1.x, mcp 2.x, and fastmcp
try:
    from mcp.server.mcpserver import MCPServer
    mcp = MCPServer("confluence-prd-converter")
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
        mcp = FastMCP("confluence-prd-converter")
    except ImportError:
        from fastmcp import FastMCP
        mcp = FastMCP("confluence-prd-converter")

# Ensure local core packages can be imported
sys.path.insert(0, str(Path(__file__).parent))

from core.confluence_client import (
    ConfluenceClient,
    extract_page_id_from_url,
    sanitize_secret
)
from core.parser import ConfluencePRDParser
from core.validator import PRDValidator
from core.security import (
    ALLOWED_DOC_EXTENSIONS,
    sanitize_subfolder_name as _sanitize_subfolder_name,
    assert_not_sensitive_path as _assert_not_sensitive_path,
)
from core.related import format_related_section as _format_related_section
from core.settings import (
    get_table_mode,
    get_related_defaults,
    load_config,
)




@mcp.tool()
def fetch_and_convert_from_confluence(
    page_id_or_url: str,
    output_md_path: str = "./prd.md",
    download_images: Optional[bool] = None,
    include_comments: Optional[bool] = None,
    assets_folder_name: Optional[str] = None,
    table_mode: Optional[str] = None,
    include_related_pages: bool = False
) -> Dict[str, Any]:
    """
    Fetch a PRD page directly from Confluence (by URL or numeric Page ID), download all image assets,
    extract discussions and comments, and convert the document into a structured prd.md Markdown file.
    Credentials (CONFLUENCE_URL and CONFLUENCE_PAT) are resolved securely from the server environment
    and never passed through LLM tool arguments.

    Parameters:
    - page_id_or_url: Confluence page URL or numeric Page ID (e.g. '1766097385' or 'https://wiki.../viewpage.action?pageId=1766097385')
    - output_md_path: Target path for the generated prd.md file (default: './prd.md')
    - download_images: Whether to automatically download image attachments to the local assets folder (default: true)
    - include_comments: Whether to fetch and append page discussions and comments as a Markdown section (default: true)
    - assets_folder_name: Custom subfolder name for image assets (default: auto-detected or 'assets')
    - table_mode: Table rendering mode: 'table' (default Markdown table) or 'text' (tableless structured text/list format)
    - include_related_pages: Append a '## 🔗 Related Confluence Documents' section (parent, children, linked, backlinks, shared labels) (default: false). OPT-IN ONLY: set true solely when the user explicitly asks for related pages. Only titles/links are listed; related pages' content is never fetched.
    """
    try:
        cfg_out = load_config()["output"]
        download_images = cfg_out["download_images"] if download_images is None else download_images
        include_comments = cfg_out["include_comments"] if include_comments is None else include_comments
        table_mode = table_mode or get_table_mode()
        out_file = Path(output_md_path).resolve()
        _assert_not_sensitive_path(out_file)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # Determine assets directory safely confined inside out_file.parent
        default_assets = f"{out_file.stem}_files" if out_file.stem != "prd" else "assets"
        assets_dir_name = _sanitize_subfolder_name(assets_folder_name, default_name=default_assets)
        local_assets_dir = (out_file.parent / assets_dir_name).resolve()

        # Initialize Confluence Client strictly from server environment / local config
        client = ConfluenceClient()

        # Fetch page from Confluence
        page_data = client.fetch_page(page_id_or_url)
        page_id = page_data["page_id"]
        title = page_data["title"]
        storage_xml = page_data.get("storage_xml")
        view_html = page_data.get("view_html")

        total_downloaded = 0
        if download_images:
            downloaded = client.download_attachments(page_id, str(local_assets_dir))
            total_downloaded = len(downloaded)

        # Parse document (prefer Storage XML if available, fallback to View HTML)
        parser = ConfluencePRDParser(
            assets_folder=assets_dir_name,
            table_mode=table_mode,
            base_url=client.base_url,
            space_key=page_data.get("space_key", "")
        )
        if storage_xml:
            md_content = parser.parse_storage_xml(storage_xml, title=title)
        else:
            md_content = parser.parse_html(view_html, title=title)

        # Fetch and format discussion comments if requested
        total_comments = 0
        if include_comments:
            comments = client.fetch_comments(page_id)
            if comments:
                comments_md = parser.format_comments_section(comments)
                if comments_md:
                    md_content = md_content.rstrip() + "\n\n" + comments_md
                    total_comments = len(comments)

        # Related pages section
        total_related = 0
        if include_related_pages:
            rel_defaults = get_related_defaults()
            rel = client.find_related_pages(page_id, rel_defaults["relation_types"], rel_defaults["limit"])
            if rel["related_pages"]:
                md_content = md_content.rstrip() + "\n\n" + _format_related_section(rel["related_pages"])
                total_related = len(rel["related_pages"])

        # Write output file
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(md_content)

        # Validate result
        validator = PRDValidator(base_dir=str(out_file.parent))
        val_report = validator.validate_content(md_content, doc_dir=str(out_file.parent))

        return {
            "status": "success",
            "page_id": page_id,
            "title": title,
            "output_file": str(out_file).replace("\\", "/"),
            "assets_folder": str(local_assets_dir).replace("\\", "/"),
            "table_mode": table_mode,
            "total_images_downloaded": total_downloaded,
            "total_comments_included": total_comments,
            "total_related_pages": total_related,
            "total_lines": len(md_content.splitlines()),
            "validation": val_report
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": sanitize_secret(str(e)),
            "page_input": sanitize_secret(str(page_id_or_url))
        }




@mcp.tool()
def find_related_confluence_pages(
    page_id_or_url: str,
    relation_types: Optional[List[str]] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Find Confluence pages related to a given page URL or Page ID. OPT-IN ONLY: call this tool ONLY when the user explicitly asks for related/linked/child/parent pages. Returns metadata (title, id, link) only, never page content. Credentials are resolved from the server environment.

    Parameters:
    - page_id_or_url: Confluence page URL or numeric Page ID
    - relation_types: Any of 'parent', 'children', 'linked' (outbound links in content), 'backlinks' (inbound links),
      'labels' (pages sharing labels in the same space), 'similar' (title keyword match).
      Default: parent, children, linked, backlinks, labels
    - limit: Max results per relation type (default: 10)
    """
    try:
        defaults = get_related_defaults()
        client = ConfluenceClient()
        result = client.find_related_pages(
            page_id_or_url,
            relation_types or defaults["relation_types"],
            limit or defaults["limit"]
        )
        return {"status": "success", "total_related": len(result["related_pages"]), **result}
    except Exception as e:
        return {
            "status": "error",
            "error_message": sanitize_secret(str(e)),
            "page_input": sanitize_secret(str(page_id_or_url))
        }


@mcp.tool()
def convert_confluence_html_to_prd(
    html_file_path: str,
    output_md_path: Optional[str] = None,
    assets_folder_name: Optional[str] = None,
    preserve_nested_tables: bool = True,
    table_mode: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convert an exported local Confluence HTML file into a clean, production-grade prd.md file.

    Parameters:
    - html_file_path: Absolute or relative path to the Confluence .html export file
    - output_md_path: Target path for the generated prd.md (default: 'prd.md' in the same folder)
    - assets_folder_name: Relative assets folder name (auto-detected from HTML name or 'assets' if omitted)
    - preserve_nested_tables: Whether to convert sub-tables into compact inline HTML tables (default: true)
    - table_mode: Table rendering mode: 'table' (default Markdown table) or 'text' (tableless structured text/list format)
    """
    try:
        table_mode = table_mode or get_table_mode()
        src_path = Path(html_file_path).resolve()
        _assert_not_sensitive_path(src_path)
        if not src_path.exists():
            return {
                "status": "error",
                "error_message": f"Source HTML file not found: '{html_file_path}'"
            }

        with open(src_path, "r", encoding="utf-8", errors="replace") as f:
            html_content = f.read()

        # Determine output path
        if not output_md_path:
            out_file = src_path.parent / f"{src_path.stem}.prd.md"
        else:
            out_file = Path(output_md_path).resolve()

        _assert_not_sensitive_path(out_file)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # Auto-detect assets folder if not given
        if not assets_folder_name:
            candidates = [
                f"{src_path.stem}_files",
                f"{src_path.stem}.files",
                "assets",
                "images",
                "attachments"
            ]
            chosen_folder = "assets"
            for c in candidates:
                if (src_path.parent / c).exists():
                    chosen_folder = c
                    break
        else:
            chosen_folder = _sanitize_subfolder_name(assets_folder_name, default_name="assets")

        # Parse HTML
        parser = ConfluencePRDParser(
            assets_folder=chosen_folder,
            preserve_nested_tables=preserve_nested_tables,
            table_mode=table_mode
        )
        md_content = parser.parse_html(html_content, title=src_path.stem)

        # Write output file
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(md_content)

        # Validate
        validator = PRDValidator(base_dir=str(out_file.parent))
        val_report = validator.validate_content(md_content, doc_dir=str(out_file.parent))

        return {
            "status": "success",
            "source_html": str(src_path).replace("\\", "/"),
            "output_file": str(out_file).replace("\\", "/"),
            "assets_folder": chosen_folder,
            "table_mode": table_mode,
            "total_lines": len(md_content.splitlines()),
            "validation": val_report
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": sanitize_secret(str(e)),
            "html_file_path": html_file_path
        }


@mcp.tool()
def convert_confluence_storage_to_prd(
    storage_xml_content: str,
    output_md_path: Optional[str] = None,
    assets_folder_name: Optional[str] = None,
    table_mode: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convert raw Confluence Storage Format (XHTML payload from Confluence API body.storage.value) into Markdown.

    Parameters:
    - storage_xml_content: The raw XML/XHTML string from Confluence API response
    - output_md_path: Optional file path to write the result (if omitted, returned directly in response)
    - assets_folder_name: Subfolder name for image references (default: 'assets')
    - table_mode: Table rendering mode: 'table' (default Markdown table) or 'text' (tableless structured text/list format)
    """
    try:
        table_mode = table_mode or get_table_mode()
        assets_folder = _sanitize_subfolder_name(assets_folder_name, default_name="assets")
        parser = ConfluencePRDParser(assets_folder=assets_folder, table_mode=table_mode)
        md_content = parser.parse_storage_xml(storage_xml_content)

        output_file_str = None
        if output_md_path:
            out_file = Path(output_md_path).resolve()
            _assert_not_sensitive_path(out_file)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(md_content)
            output_file_str = str(out_file).replace("\\", "/")

        validator = PRDValidator()
        val_report = validator.validate_content(md_content)

        return {
            "status": "success",
            "output_file": output_file_str,
            "table_mode": table_mode,
            "markdown_content": md_content if not output_file_str else None,
            "total_lines": len(md_content.splitlines()),
            "validation": val_report
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": sanitize_secret(str(e))
        }


@mcp.tool()
def validate_prd_markdown(
    md_file_path: str
) -> Dict[str, Any]:
    """
    Exhaustively check a prd.md file for broken image paths, malformed tables, unparsed Confluence macro tags,
    empty links, and generate a structural health report.

    Parameters:
    - md_file_path: Path to the prd.md file to inspect
    """
    try:
        resolved = Path(md_file_path).resolve()
        _assert_not_sensitive_path(resolved)
        validator = PRDValidator()
        return validator.validate_file(md_file_path)
    except Exception as e:
        return {
            "status": "error",
            "error_message": sanitize_secret(str(e)),
            "md_file_path": md_file_path
        }


if __name__ == "__main__":
    mcp.run()
