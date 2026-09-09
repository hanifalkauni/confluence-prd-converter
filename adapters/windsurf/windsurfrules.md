# Windsurf Cascade Rules: Confluence PRD Converter

When converting Confluence PRDs or exported HTML documents into Markdown (`prd.md`):

---

## 🚀 Execution Protocol

1. **Live Confluence Page**:
   - Use MCP tool `fetch_and_convert_from_confluence(page_id_or_url=..., output_md_path="./prd.md", download_images=True, include_comments=True)`.
2. **Local HTML File**:
   - Use MCP tool `convert_confluence_html_to_prd(html_file_path=..., output_md_path="./prd.md", preserve_nested_tables=True)`.
3. **Storage XML**:
   - Use MCP tool `convert_confluence_storage_to_prd(storage_xml_content=..., output_md_path="./prd.md")`.
4. **CLI Fallback**:
   - Run `python scripts/run_converter.py --input <path_or_url> --output prd.md`.

---

## 💎 Zero-Loss Rules

- **Nested Tables**: Convert nested sub-tables into compact single-line HTML `<table>` elements with `<br>` inside cells to preserve outer Markdown table rows.
- **Jira Lozenges**: Format as `• [KEY](url) - Summary `Status``.
- **Diagrams & Mockups**: Map Draw.io diagrams and images to `./assets/`, while discarding small system icons (`epic.svg`, etc.).
- **Interactive Embeds**: Extract Figma & Miro iframes into direct Markdown links.
- **Discussions & Comments**: Format page discussions into `## 💬 Discussions & Page Comments`.
- **Validation**: Verify output via `validate_prd_markdown`.
