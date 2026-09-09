---
name: confluence-prd-converter
description: Universal skill to fetch, parse, and convert Confluence PRD pages or local HTML exports into pristine prd.md documentation with full nested table support, Jira links, Miro/Figma embeds, and asset resolution.
---

# Confluence PRD Converter Skill

This skill equips any AI Coding Agent (Google Antigravity, Claude Code, Cursor, Windsurf, Cline, Roo Code, etc.) with the exact multi-agent SOP and tools to transform complex Confluence PRD pages or exported HTML files into clean, professional, and zero-loss `prd.md` documentation.

---

## 🎯 When to Use This Skill
Activate this skill whenever the user:
- Asks to convert, migrate, or fetch a PRD from Confluence into Markdown (`prd.md`).
- Provides a Confluence URL (e.g., `https://wiki.../viewpage.action?pageId=12345` or `display/SPACE/Title`).
- Provides a Confluence numeric Page ID (e.g., `1766097385`).
- Provides a local Confluence exported `.html` file with an accompanying `_files/` assets directory.
- Requests validation of a generated PRD Markdown file.

---

## ⚡ Execution Pipeline (5-Stage Protocol)

### Stage 1: Input Type & Environment Detection
1. **Analyze User Input**:
   - **Type A (Live Confluence URL or Page ID)**: User provided a web URL or numeric ID.
   - **Type B (Local HTML Export File)**: User provided a path to `.html` or `.htm` file.
   - **Type C (Raw XML / Storage XHTML)**: User provided raw XML payload from Confluence REST API.
2. **Detect Available Execution Mechanism**:
   - **MCP Tools Available**: Check if MCP tool `fetch_and_convert_from_confluence` or `convert_confluence_html_to_prd` is available.
   - **Fallback (Standalone CLI)**: If MCP tools are not registered, execute standalone CLI script: `python scripts/run_converter.py`.

---

### Stage 2: Conversion Strategy Execution

#### Option 1: Live Fetch from Confluence (URL / Page ID)
- **Via MCP**:
  ```json
  {
    "tool": "fetch_and_convert_from_confluence",
    "arguments": {
      "page_id_or_url": "1766097385",
      "output_md_path": "./prd.md",
      "download_images": true
    }
  }
  ```
- **Via CLI Runner**:
  ```bash
  python scripts/run_converter.py --input "https://wiki.yourcompany.com/pages/viewpage.action?pageId=1766097385" --output prd.md
  ```

#### Option 2: Local HTML File Conversion
- **Via MCP**:
  ```json
  {
    "tool": "convert_confluence_html_to_prd",
    "arguments": {
      "html_file_path": "./PRD_Export.html",
      "output_md_path": "./prd.md",
      "preserve_nested_tables": true
    }
  }
  ```
- **Via CLI Runner**:
  ```bash
  python scripts/run_converter.py --input "./PRD_Export.html" --output prd.md
  ```

#### Option 3: Raw Storage XML Conversion
- **Via MCP**:
  ```json
  {
    "tool": "convert_confluence_storage_to_prd",
    "arguments": {
      "storage_xml_content": "<ac:structured-macro ...>...</ac:structured-macro>",
      "output_md_path": "./prd.md"
    }
  }
  ```

---

### Stage 3: Element Handling Standards (Zero-Loss Guarantee)

1. **Nested Tables**:
   - Subtables inside table cells MUST be converted to compact inline HTML (`<table><thead>...</thead><tbody>...</tbody></table>`).
   - Inner newlines MUST be replaced with `<br>` to maintain strict single-line outer Markdown table rows.
2. **Jira Issue Macros**:
   - Converted to `• [KEY](https://jira.../browse/KEY) - Summary `Status``.
3. **Figma & Miro Embeds**:
   - Iframe URLs are extracted and converted into clickable links: `[Figma Design](url)` and `[Miro Board](url)`.
4. **Callout / Info Panels**:
   - Converted into GitHub Markdown alerts: `> [!NOTE]`, `> [!WARNING]`, `> [!TIP]`, `> [!CAUTION]`.
5. **Image Attachments**:
   - System icons (`epic.svg`, `viewavatar`, `default.svg`) are filtered out.
   - Mockup diagrams are mapped to `./[name]_files/image.png` or `./assets/image.png`.
6. **Discussions & Page Comments**:
   - User feedback, InfoSec notes, and architectural decisions are extracted into a dedicated `## 💬 Discussions & Page Comments` section with author badges (`> 👤 **Author** — *Date*`) and blockquoted message bodies.

---

### Stage 4: Integrity & Structural Validation

Always validate the generated Markdown file:
- **Via MCP**:
  ```json
  {
    "tool": "validate_prd_markdown",
    "arguments": {
      "md_file_path": "./prd.md"
    }
  }
  ```
- **Via CLI Runner**:
  ```bash
  python scripts/validate_output.py --input prd.md
  ```

---

### Stage 5: Summary Report Presentation
Present a structured summary to the user:
- **Document Title & Page ID**
- **Output File Path**
- **Total Lines & Words**
- **Count of Converted Tables & Subtables**
- **Count of Downloaded / Mapped Mockup Images**
- **Count of Jira Issues & Embed Links**
