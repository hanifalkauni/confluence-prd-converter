---
name: confluence-prd-converter
description: Universal skill to fetch, parse, and convert Confluence PRD pages or local HTML exports into pristine prd.md documentation with full nested table support, Jira links, Miro/Figma embeds, and asset resolution.
---

# Confluence PRD Converter Skill (Antigravity Adapter)

This skill equips Google Antigravity Agent with the autonomous protocol and tools to extract and convert complex Confluence PRD pages into production-ready `prd.md` documents.

---

## ⚡ Antigravity MCP Tools

| Tool | Parameters | Purpose |
| :--- | :--- | :--- |
| `fetch_and_convert_from_confluence` | `page_id_or_url`, `output_md_path`, `download_images`, `include_comments` | Live fetch PRD page, download image assets, extract comments, and convert to `prd.md`. |
| `convert_confluence_html_to_prd` | `html_file_path`, `output_md_path`, `preserve_nested_tables` | Converts exported Confluence `.html` file without table breakage. |
| `convert_confluence_storage_to_prd` | `storage_xml_content`, `output_md_path` | Converts raw Confluence Storage XHTML (`body.storage.value`). |
| `validate_prd_markdown` | `md_file_path` | Validates table integrity, image paths, Jira links, and tags. |

---

## 🎯 Conversion SOP Protocol

1. **Auto-Detect Input**:
   - If user passes URL or Page ID -> Call `fetch_and_convert_from_confluence`.
   - If user passes `.html` file -> Call `convert_confluence_html_to_prd`.
   - If non-MCP fallback -> Run `python scripts/run_converter.py --input <path> --output prd.md`.
2. **Preserve Rich Elements**:
   - Nested sub-tables are kept as compact single-line HTML `<table>` inside cells.
   - Jira issues are formatted with status badges: `• [KEY](url) - Summary `Status``.
   - Figma and Miro iframes are extracted to clean Markdown links.
   - Info/Warning panels are converted to `> [!NOTE]`, `> [!WARNING]`.
   - Discussions & comments are appended into a dedicated `## 💬 Discussions & Page Comments` section.
3. **Verify**:
   - Always run `validate_prd_markdown` on the generated file before reporting to the user.
