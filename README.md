<div align="center">

# 📑 Confluence PRD Converter

**Universal AI Agent Skill & Custom MCP Server for Automated, Zero-Loss Confluence PRD Conversion to Production Markdown (`prd.md`)**

[![MCP Protocol](https://img.shields.io/badge/MCP-2.0-blue.svg?style=flat-square)](https://modelcontextprotocol.io/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Cross Agent](https://img.shields.io/badge/Cross--Agent-Compatible-7aa2f7?style=flat-square)](https://github.com/hanifalkauni/confluence-prd-converter)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=flat-square)](LICENSE)

[English](README.md) • [Bahasa Indonesia](README.id.md)

</div>

---

## 🌟 Overview & Problem Statement

In agile software development, **PRD (Product Requirement Document)** pages in Confluence contain complex, multi-layered information:
- **Jira Issue macros** with dynamic status lozenges (`IN PROGRESS`, `DONE`, `BACKLOG`)
- **Nested tables** (tables inside cells for acceptance criteria, data tracking schemas, and master config)
- **Embedded interactive prototypes** from Figma and Miro
- **Dozens of mockup diagrams** and architecture screenshots
- **Security matrices** (ITPF / STRIDE Threat Modeling)

When exporting or migrating these documents to standard Markdown manually or via basic converters:
1. ❌ **Broken Tables**: Markdown lacks native nested table syntax; cell linebreaks shatter outer table rows.
2. ❌ **Lost Metadata**: Jira lozenges and macros turn into ugly HTML tags or disappear.
3. ❌ **Unclickable Embeds**: Figma and Miro iframes fail to extract clean URLs.
4. ❌ **Broken Assets**: Image links fail to resolve to local asset directories.
5. ❌ **Repetitive Scratch Scripts**: Agents spend valuable context windows repeatedly writing Python scripts for conversion.

**`confluence-prd-converter`** solves this permanently by combining an **Open FastMCP Server** and a **Universal Agent Skill** that execute zero-loss, deterministic conversions in a single prompt across any AI assistant.

---

## 🏗️ Architecture & Execution Flow

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#7aa2f7', 'primaryBorderColor': '#3d59a1', 'actorBkg': '#24283b', 'actorBorder': '#7aa2f7', 'lineColor': '#bb9af7', 'altBkg': '#1f2335' }}}%%
graph TD
    UserReq["User Prompt: 'Fetch and convert Confluence PRD to prd.md'"] --> AgentSkill["Universal Agent Skill (SKILL.md)"]
    AgentSkill --> Platform{"Target Agent Platform:<br>• Google Antigravity<br>• Claude Code / Desktop<br>• Cursor / Windsurf<br>• Cline / Roo Code / Terminal"}
    
    Platform --> DetectInput{"Input Detection:<br>1. Live Confluence URL / Page ID<br>2. Local HTML Export<br>3. Confluence Storage XML"}
    
    DetectInput -->|URL / Page ID| LiveTool["fetch_and_convert_from_confluence"]
    DetectInput -->|Local HTML| HtmlTool["convert_confluence_html_to_prd"]
    DetectInput -->|Storage XML| XmlTool["convert_confluence_storage_to_prd"]

    subgraph "Custom MCP Server & Engine"
        LiveTool --> ConfluenceClient["Confluence REST Client<br>(Auth via CONFLUENCE_PAT)"]
        HtmlTool --> CoreParser["Core DOM & AST Parser"]
        XmlTool --> CoreParser
        ConfluenceClient --> CoreParser
        
        CoreParser --> DOMCleaner["DOM & UI Cleaner"]
        CoreParser --> TableEngine["Nested Table Formatter<br>(Compact Single-Line HTML)"]
        CoreParser --> MacroEngine["Jira, Miro, Figma Extractor"]
        CoreParser --> AssetMapper["Asset & Image Resolver"]
    end

    CoreParser --> FinalMD["Output: prd.md (Zero-Loss)"]
    AgentSkill --> Validator["validate_prd_markdown (Integrity Report)"]
```

---

## ✨ Key Capabilities & Zero-Loss Standards

### 1. 📊 Compact Nested Table & Tableless Text Engine
- **Standard Table Mode (`table_mode="table"`)**: Sub-tables inside table cells are converted into compact single-line HTML `<table>` elements with inner linebreaks converted to `<br>`, preserving strict Markdown table rows.
- **Tableless Text Mode (`table_mode="text"`)**: For users preferring non-table plain text representations, all tables and nested matrices are deterministically converted into structured key-value bullet cards without losing any data or context.

### 2. 🎫 Jira Macro & Lozenge Resolution
Extracts Jira keys, summaries, URLs, and status badges into clean Markdown:
```markdown
• [CITA-1042](https://jira.../browse/CITA-1042) - Profile Revamp `IN PROGRESS`
```

### 3. 🎨 Figma & Miro Embed Extraction
Decodes complex iframe source URLs to direct links:
```markdown
[Figma Design](https://www.figma.com/file/...)
[Miro Board](https://miro.com/app/board/...)
```

### 4. 🖼️ Smart Asset Mapping & Icon Filtering
Automatically downloads attachments from live pages or maps local `./[name]_files/` directories while stripping noisy system icons (`epic.svg`, `viewavatar`, `default.svg`).

### 5. 💡 GitHub Alert Panels
Transforms Confluence info/warning/note/tip panels into standard GitHub callouts:
```markdown
> [!NOTE]
> **Document Status**
> This PRD is currently under active review.
```

### 6. 💬 Discussion & Comment Extraction
Automatically captures stakeholder feedback, reviewer comments, and architectural decisions into a structured `## 💬 Discussions & Page Comments` section, preserving author names, timestamps, user mentions, and formatting.

### 7. 🔗 Opt-In Related Page Discovery (Zero Content Leak)
When explicitly requested, discovers connected documents (parent context, child specs, outbound links in content, backlinks, and shared-space labels). Only lightweight titles and URLs are listed (no automatic page fetching), protecting LLM context tokens and bandwidth.

---

## 🛠️ MCP Tool Reference

| Tool Name | Description | Key Parameters |
| :--- | :--- | :--- |
| `fetch_and_convert_from_confluence` | Live fetch from Confluence by URL or Page ID, downloads image attachments, extracts comments, and outputs `prd.md`. | `page_id_or_url`, `output_md_path`, `download_images`, `include_comments`, `table_mode`, `assets_folder_name`, `include_related_pages` (opt-in, default `false`) |
| `convert_confluence_html_to_prd` | Converts local Confluence exported `.html` file to structured Markdown. | `html_file_path`, `output_md_path`, `assets_folder_name`, `preserve_nested_tables`, `table_mode` |
| `convert_confluence_storage_to_prd` | Converts raw XML/XHTML Storage Format (`body.storage.value`) directly to Markdown. | `storage_xml_content`, `output_md_path`, `assets_folder_name`, `table_mode` |
| `validate_prd_markdown` | Inspects `prd.md` for broken tables, missing images, unparsed tags, and compiles statistics. | `md_file_path` |
| `find_related_confluence_pages` | **Opt-in only** — runs only when you explicitly ask for related pages. Lists parent, child, linked, backlinked and shared-label pages of the link you provided (titles/links only; related content is never fetched). | `page_id_or_url`, `relation_types`, `limit` |

---

## 🔌 Multi-Agent Integration Guide

### 💬 Method A: Universal MCP Server (Recommended for Tool Calling)

1. Set your credentials in your OS Environment Variables (so no plaintext token is stored in `mcp_config.json`):
   ```bash
   # Linux / macOS
   export CONFLUENCE_URL="https://wiki.yourcompany.com"
   export CONFLUENCE_PAT="your_token_here"

   # Windows PowerShell (User Scope)
   [Environment]::SetEnvironmentVariable("CONFLUENCE_URL", "https://wiki.yourcompany.com", "User")
   [Environment]::SetEnvironmentVariable("CONFLUENCE_PAT", "your_token_here", "User")
   ```

2. Add `confluence-prd-converter` to your AI IDE (Google Antigravity, Claude Desktop, Cursor, Windsurf, Cline, Continue.dev, Kiro) via MCP:
   ```json
   {
     "mcpServers": {
       "confluence-prd-converter": {
         "command": "npx",
         "args": [
           "-y",
           "github:hanifalkauni/confluence-prd-converter",
           "--mcp"
         ]
       }
     }
   }
   ```

---

### 📄 Method B: Pure Skill Agent / Rule File (No MCP Server Required)

If you prefer installing the skill instructions directly into your workspace for native agent reasoning:

#### 🌐 Option 1: Automatic via skills.sh (Recommended — 30+ AI Agents)
Install with a single command into Cursor, Claude Code, Windsurf, Copilot, or Gemini CLI:
```bash
npx skills add hanifalkauni/confluence-prd-converter
```

#### ⚡ Option 2: Automatic Adapter Injection via CLI
Export all agent adapter files into your current workspace root:
```bash
npx -y github:hanifalkauni/confluence-prd-converter init
```

#### 📦 Option 3: Manual Installation per AI Agent

<details>
<summary><b>🤖 Google Antigravity & Gemini CLI</b></summary>

Copy adapter to local workspace skill directory:
```bash
mkdir -p .agents/skills/confluence-prd-converter
cp adapters/antigravity/SKILL.md .agents/skills/confluence-prd-converter/SKILL.md
```
*Or install globally for all workspaces at:* `~/.gemini/config/skills/confluence-prd-converter/SKILL.md`.

</details>

<details>
<summary><b>🧠 Claude Code & Claude Desktop</b></summary>

Add to project root `CLAUDE.md`:
```bash
cp adapters/claude/CLAUDE.md ./CLAUDE.md
```

</details>

<details>
<summary><b>⚡ Cursor IDE</b></summary>

Add rule file to `.cursor/rules/`:
```bash
mkdir -p .cursor/rules
cp adapters/cursor/confluence-prd-converter.mdc .cursor/rules/confluence-prd-converter.mdc
```

</details>

<details>
<summary><b>🌊 Windsurf IDE</b></summary>

Add rule to `.windsurf/rules/`:
```bash
mkdir -p .windsurf/rules
cp adapters/windsurf/windsurfrules.md .windsurf/rules/confluence-prd-converter.md
```

</details>

<details>
<summary><b>🤖 Cline & Roo Code</b></summary>

Add rule to `.clinerules/`:
```bash
mkdir -p .clinerules
cp adapters/cline/clinerules.md .clinerules/confluence-prd-converter.md
```

</details>

<details>
<summary><b>🐙 GitHub Copilot</b></summary>

Add to `.github/copilot-instructions.md`:
```bash
mkdir -p .github
cp adapters/copilot/copilot-instructions.md .github/copilot-instructions.md
```

</details>

<details>
<summary><b>🎯 Kiro</b></summary>

Add steering instructions to `.kiro/steering/`:
```bash
mkdir -p .kiro/steering
cp adapters/kiro/steering.md .kiro/steering/confluence-prd-converter.md
```

</details>

<details>
<summary><b>⏩ Continue.dev</b></summary>

Add prompt rule to `.continue/rules/`:
```bash
mkdir -p .continue/rules
cp adapters/continue/prompt.md .continue/rules/confluence-prd-converter.md
```

</details>

---

### 💻 Method C: Standalone Terminal CLI Runner

Convert local HTML export:
```bash
npx -y github:hanifalkauni/confluence-prd-converter --input ./PRD_Export.html --output ./prd.md
```

Live fetch from Confluence URL:
```bash
npx -y github:hanifalkauni/confluence-prd-converter --input "https://wiki.yourcompany.com/pages/viewpage.action?pageId=1766097385" --output ./prd.md
```

Live fetch **plus related-page links** (opt-in; off by default, titles/links only):
```bash
npx -y github:hanifalkauni/confluence-prd-converter --input "https://wiki.yourcompany.com/pages/viewpage.action?pageId=1766097385" --related --related-types parent,children,linked
```

Validate markdown integrity:
```bash
python scripts/validate_output.py --input ./prd.md
```

---

## 📂 Repository Layout

```
confluence-prd-converter/
├── server.py                        # FastMCP Server (stdio JSON-RPC for AI IDEs)
├── SKILL.md                         # Universal Agent Skill definition
├── core/                            # Core parsing & transformation engine
│   ├── confluence_client.py         # REST API client & attachment/comment fetcher
│   ├── parser.py                    # Unified AST parser (Storage XML & View HTML)
│   ├── formatters.py                # Nested tables, Jira lozenges, embeds, alert callouts
│   ├── clean.py                     # DOM sanitizer & system icon filter
│   └── validator.py                 # Structural Markdown integrity validator
├── adapters/                        # Rule & skill adapters for 8+ AI Agent IDEs
│   ├── antigravity/                 # Google Antigravity & Gemini CLI
│   ├── claude/                      # Claude Code & Claude Desktop
│   ├── cursor/                      # Cursor IDE (.cursor/rules/)
│   ├── windsurf/                    # Windsurf Cascade (.windsurf/rules/)
│   ├── cline/                       # Cline & Roo Code (.clinerules/)
│   ├── copilot/                     # GitHub Copilot (.github/)
│   ├── kiro/                        # Kiro Steering (.kiro/steering/)
│   └── continue/                    # Continue.dev (.continue/rules/)
├── evaluations/                     # Evaluation & Feedback Hub (RFCs & study cases)
├── scripts/                         # Standalone CLI tools (run_converter, validate_output)
├── tests/                           # Unit test suite & generalized sample fixtures
├── schema.json                      # Configuration JSON Schema
└── confluence-prd-converter.config.json # Runtime defaults (verify_ssl, timeout, Jira base URL, table mode, related defaults). Credentials are never read from it
```

---

## 🧪 Testing & Verification

Run the full unit test suite:

```bash
python tests/test_all.py
```

---

## 📄 License

SPDX-License-Identifier: [Apache-2.0](LICENSE)

This project is licensed under the [Apache License 2.0](LICENSE).
