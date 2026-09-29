# 📑 GitHub Copilot Instructions: Confluence PRD Converter

You are equipped with the **Confluence PRD Converter** skill and FastMCP Server. Follow this protocol when transforming Confluence PRD pages or local HTML exports into pristine `prd.md` documentation with a Zero-Loss Guarantee.

---

## 🎯 When to Activate
Activate this protocol whenever the user:
- Requests converting, migrating, or fetching a PRD from Confluence into Markdown (`prd.md`).
- Provides a Confluence URL (e.g., `https://wiki.../pages/viewpage.action?pageId=12345` or `display/SPACE/Title`).
- Provides a Confluence numeric Page ID (e.g., `1776167017`).
- Provides a local Confluence exported `.html` file with an accompanying `_files/` assets directory.
- Requests a tableless plain text / narrative representation of a Confluence PRD.
- Requests integrity validation of an existing PRD Markdown file.

---

## ⚡ MCP Tool Reference

| Tool Name | Parameters | Purpose |
| :--- | :--- | :--- |
| `fetch_and_convert_from_confluence` | `page_id_or_url`, `output_md_path`, `download_images`, `include_comments`, `table_mode`, `assets_folder_name` | Live fetch Confluence page via REST API, download image attachments, extract comments, and write `prd.md`. |
| `convert_confluence_html_to_prd` | `html_file_path`, `output_md_path`, `preserve_nested_tables`, `table_mode`, `assets_folder_name` | Converts exported Confluence `.html` file with full nested table protection or tableless format. |
| `convert_confluence_storage_to_prd` | `storage_xml_content`, `output_md_path`, `table_mode`, `assets_folder_name` | Converts raw Confluence Storage XHTML (`body.storage.value`) directly to Markdown. |
| `validate_prd_markdown` | `md_file_path` | Validates table syntax, image links, Jira keys, unescaped macro tags, and outputs metrics. |

---

## 🎯 5-Stage Conversion Protocol

### Stage 1: Input Detection & Strategy Selection
1. **Live Confluence Page (URL / Page ID)**: Call `fetch_and_convert_from_confluence`.
2. **Local HTML Export File**: Call `convert_confluence_html_to_prd`.
3. **Raw Storage XML Payload**: Call `convert_confluence_storage_to_prd`.
4. **CLI Fallback**: Run `python scripts/run_converter.py --input <path_or_url> --output prd.md --table-mode <table|text>`.

### Stage 2: Table Mode Strategy Selection
- **Standard Mode (`table_mode="table"`) (Default)**: Renders strict Markdown tables (`| ... |`) with compact inline HTML sub-tables.
- **Tableless Mode (`table_mode="text"`) (Optional)**: Converts all tables into structured key-value bullet cards deterministically when the user prefers non-table representations.

### Stage 3: Zero-Loss Formatting Standards
1. **Table Handling Modes**:
   - **Standard Table Mode**: Subtables inside cells converted to compact single-line HTML `<table><tr>...</tr></table>` with `<br>` inner breaks.
   - **Tableless Plain Text Mode**: Tables converted to hierarchical bullet cards (`- **Property**: Value` or `- **Feature: Name**:\n  - **Field**: ...`) with zero data loss.
2. **Jira Issues & Status Lozenges**: Format as `• [KEY](https://jira.../browse/KEY) - Summary `Status``.
3. **Draw.io Diagrams & Mockups**: Map Draw.io diagrams to `![Draw.io Diagram: Name](./assets/Name.png)`. Discard system icons (`epic.svg`, etc.).
4. **Interactive Embeds**: Extract Figma & Miro iframes into clean direct Markdown links (`[Figma Design](url)`, `[Miro Board](url)`).
5. **Callout Alerts**: Convert note/info/warning/tip panels into GitHub Markdown alerts (`> [!NOTE]`, `> [!WARNING]`, `> [!TIP]`, `> [!CAUTION]`).
6. **Discussions & Page Comments**: Capture stakeholder comments into `## 💬 Discussions & Page Comments` with author headers and timestamps.

### Stage 4: Post-Conversion Validation
Always run `validate_prd_markdown` on the generated file to ensure 0 table errors and 0 missing assets.

### Stage 5: Summary Report Presentation
Report: Document Title, Page ID, Output Path, Total Lines/Words, Table Mode, Count of Tables/Cards, Downloaded Images, and Jira Issues.
