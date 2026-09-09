# 📑 Claude Code Rules: Confluence PRD Converter

You are equipped with the **Confluence PRD Converter** skill and MCP Server. Follow this protocol when fetching, converting, or migrating Confluence PRDs and technical requirement documents into Markdown (`prd.md`).

---

## 🎯 5-Stage Conversion SOP Protocol

### Stage 1: Input Detection & Selection
1. **Live Confluence Page (URL / Page ID)**:
   - Identify URL (e.g., `https://wiki.../pages/viewpage.action?pageId=12345` or `display/SPACE/Title`) or numeric ID (e.g., `1776167017`).
   - Use MCP tool `fetch_and_convert_from_confluence`.
2. **Local HTML Export**:
   - Identify `.html` export path and use MCP tool `convert_confluence_html_to_prd`.
3. **Raw Storage XML Payload**:
   - Use MCP tool `convert_confluence_storage_to_prd`.
4. **CLI Fallback**:
   - If MCP tools are unavailable, run: `python scripts/run_converter.py --input <path_or_url> --output prd.md`.

---

## ⚡ MCP Tool Reference

| Tool | Key Parameters | Purpose |
| :--- | :--- | :--- |
| `fetch_and_convert_from_confluence` | `page_id_or_url`, `output_md_path`, `download_images`, `include_comments` | Live fetch Confluence page, download image attachments, extract comments, and write `prd.md`. |
| `convert_confluence_html_to_prd` | `html_file_path`, `output_md_path`, `preserve_nested_tables` | Converts exported Confluence `.html` file with nested table protection. |
| `convert_confluence_storage_to_prd` | `storage_xml_content`, `output_md_path` | Converts raw Confluence Storage XHTML (`body.storage.value`). |
| `validate_prd_markdown` | `md_file_path` | Validates table syntax, image links, Jira keys, and unescaped tags. |

---

## 💎 Zero-Loss Formatting Standards

1. **Nested Tables in Table Cells**:
   - Convert subtables into compact single-line HTML `<table>` elements (`<table><thead>...</thead><tbody>...</tbody></table>`).
   - Convert cell line breaks to `<br>` to maintain strict single-line outer Markdown table rows without column breakage.
2. **Jira Issues & Status Lozenges**:
   - Render as `• [KEY](https://jira.../browse/KEY) - Summary `STATUS``.
3. **Draw.io Diagrams**:
   - Transform `drawio` macros into `![Draw.io Diagram: Name](./assets/Name.png)`.
4. **Figma & Miro Interactive Embeds**:
   - Extract raw iframe URLs into clean Markdown links: `[Figma Design](url)` & `[Miro Board](url)`.
5. **Callout Alerts**:
   - Convert Confluence note/info/warning/tip panels into GitHub Markdown alerts (`> [!NOTE]`, `> [!WARNING]`, `> [!TIP]`, `> [!CAUTION]`).
6. **Discussions & Page Comments**:
   - Extract stakeholder comments into `## 💬 Discussions & Page Comments` with author headers (`> 👤 **Author** — *Date UTC*`) and blockquoted message bodies.
7. **System Icon Filtering**:
   - Filter out small system icon assets (`epic.svg`, `viewavatar`, `default.svg`, `star_off.png`).

---

## 🧪 Verification
Always call `validate_prd_markdown` on the generated file to ensure 0 table errors and 0 missing assets.
