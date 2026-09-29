#!/usr/bin/env python3
"""
Confluence PRD Converter - FastMCP Server
Universal Model Context Protocol Server providing automated Confluence PRD extraction,
transformation to pristine Markdown (prd.md), asset resolution, and structural validation.
"""

import sys
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

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

from core.confluence_client import ConfluenceClient, extract_page_id_from_url
from core.parser import ConfluencePRDParser
from core.validator import PRDValidator


@mcp.tool()
def fetch_and_convert_from_confluence(
    page_id_or_url: str,
    output_md_path: str = "./prd.md",
    download_images: bool = True,
    include_comments: bool = True,
    assets_folder_name: Optional[str] = None,
    confluence_url: Optional[str] = None,
    confluence_pat: Optional[str] = None,
    table_mode: str = "table"
) -> Dict[str, Any]:
    """
    Fetch a PRD page directly from Confluence (by URL or numeric Page ID), download all image assets,
    extract discussions and comments, and convert the document into a structured prd.md Markdown file.

    Parameters:
    - page_id_or_url: Confluence page URL or numeric Page ID (e.g. '1766097385' or 'https://wiki.../viewpage.action?pageId=1766097385')
    - output_md_path: Target path for the generated prd.md file (default: './prd.md')
    - download_images: Whether to automatically download image attachments to the local assets folder (default: true)
    - include_comments: Whether to fetch and append page discussions and comments as a Markdown section (default: true)
    - assets_folder_name: Custom subfolder name for image assets (default: auto-detected or 'assets')
    - confluence_url: Optional explicit Confluence base URL (falls back to CONFLUENCE_URL env or mcp_config.json)
    - confluence_pat: Optional explicit Personal Access Token (falls back to CONFLUENCE_PAT env or mcp_config.json)
    - table_mode: Table rendering mode: 'table' (default Markdown table) or 'text' (tableless structured text/list format)
    """
    try:
        out_file = Path(output_md_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # Determine assets directory
        if not assets_folder_name:
            assets_dir_name = f"{out_file.stem}_files" if out_file.stem != "prd" else "assets"
        else:
            assets_dir_name = assets_folder_name

        local_assets_dir = out_file.parent / assets_dir_name

        # Initialize Confluence Client
        client = ConfluenceClient(
            base_url=confluence_url,
            pat=confluence_pat
        )

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
        parser = ConfluencePRDParser(assets_folder=assets_dir_name, table_mode=table_mode)
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
            "total_lines": len(md_content.splitlines()),
            "validation": val_report
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "page_input": page_id_or_url
        }


@mcp.tool()
def convert_confluence_html_to_prd(
    html_file_path: str,
    output_md_path: Optional[str] = None,
    assets_folder_name: Optional[str] = None,
    preserve_nested_tables: bool = True,
    table_mode: str = "table"
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
        src_path = Path(html_file_path).resolve()
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
            chosen_folder = assets_folder_name

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
            "error_message": str(e),
            "html_file_path": html_file_path
        }


@mcp.tool()
def convert_confluence_storage_to_prd(
    storage_xml_content: str,
    output_md_path: Optional[str] = None,
    assets_folder_name: Optional[str] = None,
    table_mode: str = "table"
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
        assets_folder = assets_folder_name or "assets"
        parser = ConfluencePRDParser(assets_folder=assets_folder, table_mode=table_mode)
        md_content = parser.parse_storage_xml(storage_xml_content)

        output_file_str = None
        if output_md_path:
            out_file = Path(output_md_path).resolve()
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
            "error_message": str(e)
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
        validator = PRDValidator()
        return validator.validate_file(md_file_path)
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "md_file_path": md_file_path
        }


if __name__ == "__main__":
    mcp.run()
