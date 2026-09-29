---
name: confluence-prd-converter
description: Universal skill to fetch, parse, and convert Confluence PRD pages or local HTML exports into pristine prd.md documentation with full nested table support, tableless plain text mode, Jira links, Miro/Figma embeds, and asset resolution.
---

# Confluence PRD Converter Skill (Antigravity Adapter)

This skill equips Google Antigravity Agent with the autonomous protocol and tools to extract and convert complex Confluence PRD pages or exported HTML files into production-grade `prd.md` documentation with a Zero-Loss Guarantee.

---

## 🎯 When to Use This Skill
Activate this skill whenever the user:
- Asks to convert, migrate, or fetch a PRD from Confluence into Markdown (`prd.md`).
- Provides a Confluence URL (e.g., `https://wiki.../viewpage.action?pageId=12345` or `display/SPACE/Title`).
- Provides a Confluence numeric Page ID (e.g., `1766097385`).
- Provides a local Confluence exported `.html` file with an accompanying `_files/` assets directory.
- Requests a tableless plain text / narrative representation of a Confluence PRD.
- Requests validation of a generated PRD Markdown file.

---

## ⚡ Antigravity MCP Tools

| Tool | Parameters | Purpose |
| :--- | :--- | :--- |
| `fetch_and_convert_from_confluence` | `page_id_or_url`, `output_md_path`, `download_images`, `include_comments`, `table_mode`, `assets_folder_name` | Live fetch PRD page, download image assets, extract comments, and convert to `prd.md`. |
| `convert_confluence_html_to_prd` | `html_file_path`, `output_md_path`, `preserve_nested_tables`, `table_mode`, `assets_folder_name` | Converts exported Confluence `.html` file without table breakage. |
| `convert_confluence_storage_to_prd` | `storage_xml_content`, `output_md_path`, `table_mode`, `assets_folder_name` | Converts raw Confluence Storage XHTML (`body.storage.value`). |
| `validate_prd_markdown` | `md_file_path` | Validates table integrity, image paths, Jira links, and tags. |

---

## 🎯 5-Stage Conversion SOP Protocol

### Stage 1: Input & Mode Detection
1. **Analyze User Input**:
   - **Type A (Live URL / Page ID)**: Call `fetch_and_convert_from_confluence`.
   - **Type B (Local HTML Export)**: Call `convert_confluence_html_to_prd`.
   - **Type C (Storage XML Payload)**: Call `convert_confluence_storage_to_prd`.
   - **Fallback (Standalone CLI)**: Run `python scripts/run_converter.py --input <path_or_url> --output prd.md --table-mode <table|text>`.
2. **Determine Table Mode**:
   - **Standard Mode (`table_mode="table"`) (Default)**: Renders standard Markdown tables with compact inline HTML sub-tables.
   - **Tableless Mode (`table_mode="text"`)**: Use when user requests plain text / no tables / narrative format. Converts tables into structured key-value bullet cards deterministically.

### Stage 2: Conversion Strategy Execution
- **Via MCP**:
  ```json
  {
    "tool": "fetch_and_convert_from_confluence",
    "arguments": {
      "page_id_or_url": "1766097385",
      "output_md_path": "./prd.md",
      "download_images": true,
      "table_mode": "table"
    }
  }
  ```

### Stage 3: Zero-Loss Element Formatting Standards
1. **Table Handling Modes**:
   - **Standard Table Mode**: Outer tables formatted as `| ... |`. Subtables inside cells converted to compact single-line HTML `<table><tr>...</tr></table>` with `<br>` inner breaks.
   - **Tableless Plain Text Mode**: Tables converted to hierarchical bullet cards (`- **Property**: Value` or `- **Feature: Name**:\n  - **Field**: ...`) with zero data loss.
2. **Jira Issue Macros**: Render as `• [KEY](https://jira.../browse/KEY) - Summary `Status``.
3. **Diagrams & Mockups**: Draw.io macros mapped to `![Draw.io Diagram: Name](./assets/Name.png)`. System icons (`epic.svg`, `viewavatar`, `default.svg`) are filtered out.
4. **Interactive Embeds**: Extract Figma & Miro iframes into clean direct Markdown links (`[Figma Design](url)`, `[Miro Board](url)`).
5. **Callout Alert Panels**: Convert info/warning/note/tip panels into GitHub Markdown alerts (`> [!NOTE]`, `> [!WARNING]`, `> [!TIP]`, `> [!CAUTION]`).
6. **Discussions & Page Comments**: Capture reviewer feedback into `## 💬 Discussions & Page Comments` with author badges and timestamps.

### Stage 4: Structural Validation
Always run `validate_prd_markdown` on the generated output file to verify image paths, table integrity, and compile document metrics.

### Stage 5: Summary Report
Report to the user: Document Title, Page ID, Output Path, Total Lines/Words, Table Mode used, Converted Tables/Cards, Downloaded Images, and Jira Links.
