# Cline & Roo Code Rules: Confluence PRD Converter

You are equipped with the **Confluence PRD Converter** toolset. When converting Confluence PRDs or HTML exports to Markdown:

---

## 🛠️ Execution Protocol

1. **Live Confluence Page**:
   - Call tool `fetch_and_convert_from_confluence` with `page_id_or_url`, `output_md_path="./prd.md"`, `download_images=True`, `include_comments=True`.
2. **Local HTML File**:
   - Call tool `convert_confluence_html_to_prd` with `html_file_path` and `preserve_nested_tables=True`.
3. **CLI Execution**:
   - Run `python scripts/run_converter.py --input <path_or_url> --output prd.md`.

---

## 💎 Zero-Loss Formatting Requirements

- **Sub-Tables**: Convert nested tables inside cells to single-line HTML `<table>` elements with `<br>` line breaks to prevent Markdown row collapse.
- **Jira Status Lozenges**: Format as `• [KEY](url) - Summary `Status``.
- **Diagrams & Mockups**: Map Draw.io diagrams and downloaded images to `./assets/`. Discard system icons (`epic.svg`, etc.).
- **Embeds**: Extract iframe source URLs for Figma and Miro to direct clickable links.
- **Alert Callouts**: Format note/warning/tip panels to GitHub alerts (`> [!NOTE]`, `> [!WARNING]`).
- **Discussions & Comments**: Format page discussions to `## 💬 Discussions & Page Comments`.
- **Validation**: Call `validate_prd_markdown` on output file.
