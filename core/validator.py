"""
Validation engine for Confluence PRD Markdown outputs:
- Checks broken image paths
- Validates Markdown table formatting and column counts
- Scans for leftover unparsed Confluence XML/HTML tags
- Detects broken or empty links
- Compiles statistical summary of the PRD document
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .security import is_within_directory


class PRDValidator:
    """Validates integrity and quality of converted PRD Markdown files."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()

    def validate_file(self, md_file_path: str) -> Dict[str, Any]:
        """Validate a prd.md file on disk."""
        target_path = Path(md_file_path)
        if not target_path.is_absolute():
            if target_path.exists():
                target_path = target_path.resolve()
            else:
                target_path = (self.base_dir / target_path).resolve()

        if not target_path.exists():
            return {
                "status": "failed",
                "file_path": str(target_path).replace("\\", "/"),
                "errors": [f"File not found: '{target_path}'"],
                "warnings": [],
                "metrics": {}
            }

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {
                "status": "failed",
                "file_path": str(target_path).replace("\\", "/"),
                "errors": [f"Failed to read file: {str(e)}"],
                "warnings": [],
                "metrics": {}
            }

        return self.validate_content(content, doc_dir=str(target_path.parent))

    def validate_content(self, md_content: str, doc_dir: Optional[str] = None) -> Dict[str, Any]:
        """Validate Markdown string content and return detailed report."""
        errors: List[str] = []
        warnings: List[str] = []

        if not md_content or not md_content.strip():
            return {
                "status": "failed",
                "errors": ["PRD markdown document is completely empty."],
                "warnings": [],
                "metrics": {
                    "total_lines": 0,
                    "total_words": 0,
                    "headings": {},
                    "total_tables": 0,
                    "total_images": 0
                }
            }

        lines = md_content.splitlines()
        total_lines = len(lines)
        total_words = len(re.findall(r"\b\w+\b", md_content))

        # 1. Heading Statistics
        headings: Dict[str, int] = {}
        for line in lines:
            h_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if h_match:
                level = f"h{len(h_match.group(1))}"
                headings[level] = headings.get(level, 0) + 1

        if not headings.get("h1", 0):
            warnings.append("Document lacks a top-level H1 title heading (# Title).")

        # 2. Check for leftover/unparsed Confluence tags
        leftover_patterns = [
            (r"<ac:[a-zA-Z0-9_\-]+", "Unparsed Confluence Storage macro tag (<ac:...)"),
            (r"<ri:[a-zA-Z0-9_\-]+", "Unparsed Confluence Resource tag (<ri:...)"),
            (r'class=["\']aui-', "Unstripped Atlassian AUI CSS class"),
            (r'data-jira-key=["\']', "Unparsed data-jira-key attribute"),
            (r"floating-scrollbar", "Unstripped floating-scrollbar artifact"),
            (r"confluence-information-macro", "Unconverted confluence-information-macro div"),
        ]

        for pattern, desc in leftover_patterns:
            matches = re.findall(pattern, md_content, re.IGNORECASE)
            if matches:
                warnings.append(f"{desc} detected ({len(matches)} occurrences).")

        # 3. Check for empty links `[]()`
        empty_links = re.findall(r"\[\s*\]\(\s*\)|\[.*?\]\(\s*\)", md_content)
        if empty_links:
            warnings.append(f"Found {len(empty_links)} empty markdown links with missing URL.")

        # 4. Image validation
        image_matches = re.findall(r"!\[(.*?)\]\((.*?)\)", md_content)
        total_images = len(image_matches)
        missing_images = []
        outside_images = []

        check_dir = Path(doc_dir) if doc_dir else self.base_dir
        for alt, img_path in image_matches:
            # Skip external web URLs
            if img_path.startswith("http://") or img_path.startswith("https://") or img_path.startswith("data:"):
                continue

            # Check local file existence only inside the document directory (no path-traversal probing)
            local_img_file = check_dir / img_path
            if not is_within_directory(check_dir, local_img_file):
                outside_images.append(img_path)
                continue
            if doc_dir and not local_img_file.exists():
                missing_images.append(img_path)

        if missing_images:
            warnings.append(f"{len(missing_images)} referenced local images not found on disk (e.g. {missing_images[0]}).")
        if outside_images:
            warnings.append(f"{len(outside_images)} image paths point outside the document directory and were not checked (e.g. {outside_images[0]}).")

        # 5. Table validation
        table_count = 0
        in_table = False
        table_rows = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                if not in_table:
                    in_table = True
                    table_rows = []
                table_rows.append((i + 1, stripped))
            else:
                if in_table:
                    # Validate ended table
                    table_count += 1
                    self._validate_table_structure(table_rows, warnings, errors)
                    in_table = False
                    table_rows = []

        if in_table:
            table_count += 1
            self._validate_table_structure(table_rows, warnings, errors)

        # 6. Count Jira issues & Embeds
        jira_links = len(re.findall(r"\[[A-Z0-9]+-\d+\]\(https?://.*?/browse/[A-Z0-9]+-\d+\)", md_content))
        figma_embeds = len(re.findall(r"\[Figma Design\]\(https?://.*?figma\.com/.*?\)", md_content))
        miro_embeds = len(re.findall(r"\[Miro Board\]\(https?://.*?miro\.com/.*?\)", md_content))

        # Status determination
        if errors:
            status = "failed"
        elif warnings:
            status = "warning"
        else:
            status = "passed"

        return {
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "metrics": {
                "total_lines": total_lines,
                "total_words": total_words,
                "headings": headings,
                "total_tables": table_count,
                "total_images": total_images,
                "jira_links": jira_links,
                "figma_embeds": figma_embeds,
                "miro_embeds": miro_embeds
            }
        }

    def _validate_table_structure(
        self,
        table_rows: List[tuple],
        warnings: List[str],
        errors: List[str]
    ) -> None:
        """Validate that Markdown table has header separator and uniform column count."""
        if len(table_rows) < 2:
            start_line = table_rows[0][0]
            warnings.append(f"Table at line {start_line} has only 1 row without separator.")
            return

        # Check separator row
        sep_line_num, sep_content = table_rows[1]
        sep_cells = [c.strip() for c in sep_content.strip("|").split("|")]
        is_valid_sep = all(re.match(r"^:?-+:?$", c) for c in sep_cells if c)
        if not is_valid_sep:
            warnings.append(f"Table separator at line {sep_line_num} does not match '| --- |' standard.")

        # Check column count consistency
        header_cells = len(table_rows[0][1].strip("|").split("|"))
        for line_num, row_content in table_rows[2:]:
            cols = len(row_content.strip("|").split("|"))
            if cols != header_cells:
                warnings.append(f"Table row at line {line_num} has {cols} columns, expected {header_cells}.")
