# Continue.dev Prompt: Confluence PRD Converter

Use the Confluence PRD Converter engine to transform Confluence pages and HTML exports into pristine `prd.md` documentation:
- **Execution**: Use FastMCP server tools or CLI runner `python scripts/run_converter.py --input <path_or_url> --output prd.md`.
- **Zero-Loss Tables**: Keep nested subtables inside cells valid and compact via single-line HTML `<table>` elements with `<br>`.
- **Jira & Diagrams**: Format Jira macros with status lozenges and Draw.io diagrams to `./assets/`.
- **Embeds & Callouts**: Extract Figma/Miro iframes and format panels to GitHub Markdown alerts (`> [!NOTE]`, `> [!WARNING]`).
- **Comments**: Capture stakeholder discussions into `## 💬 Discussions & Page Comments`.
- **Verification**: Run `validate_prd_markdown` on output.
