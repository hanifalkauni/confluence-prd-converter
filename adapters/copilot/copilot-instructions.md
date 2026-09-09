# GitHub Copilot Instructions: Confluence PRD Converter

When converting Confluence PRDs or exported HTML documents into Markdown (`prd.md`):

1. **Conversion Strategy**:
   - Use MCP tool `fetch_and_convert_from_confluence` or `convert_confluence_html_to_prd`.
   - For CLI invocation: `python scripts/run_converter.py --input <input_file_or_url> --output prd.md`.
2. **Zero-Loss Formatting**:
   - Format nested subtables inside cells as compact single-line HTML `<table>` elements with `<br>` inside cells.
   - Convert Jira macros into `• [KEY](https://jira.../browse/KEY) - Summary `Status``.
   - Map Draw.io macros and diagrams to `./assets/{name}.png`.
   - Convert Figma and Miro iframes into clean Markdown links.
   - Format panels as GitHub alerts: `> [!NOTE]`, `> [!WARNING]`, `> [!TIP]`.
   - Preserve page discussions in a `## 💬 Discussions & Page Comments` section.
3. **Validation**:
   - Validate output using `validate_prd_markdown` or `python scripts/validate_output.py --input prd.md`.
