# Kiro Steering: Confluence PRD Converter

Steering guidelines for autonomous Confluence PRD document conversions:
- **Tool Selection**: Prioritize FastMCP server tools `fetch_and_convert_from_confluence` (live pages) and `convert_confluence_html_to_prd` (local exports).
- **Nested Tables**: Guarantee zero-loss table conversions via compact inline HTML `<table>` elements with `<br>` inside cells.
- **Macros & Embeds**: Resolve Jira keys/lozenges, Draw.io diagrams, Figma/Miro embeds, and GitHub alert callouts.
- **Discussions & Comments**: Extract stakeholder discussions into `## 💬 Discussions & Page Comments`.
- **System Icons**: Discard boilerplate icons (`epic.svg`, etc.) and download/map mockups to `./assets/`.
- **Integrity Validation**: Validate generated Markdown with `validate_prd_markdown`.
