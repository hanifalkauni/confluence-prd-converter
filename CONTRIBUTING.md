# 🤝 Contributing to Confluence PRD Converter

Thank you for your interest in contributing to **Confluence PRD Converter**! This project is an open-source Universal AI Agent Skill and Model Context Protocol (MCP) server dedicated to automated, zero-loss transformation of Confluence PRD pages and HTML exports into clean, production-grade Markdown (`prd.md`).

---

## 🏛️ Architectural Principles

1. **Zero-Loss Document Fidelity**: Every critical PRD element—nested tables, Jira lozenges, draw.io diagrams, Figma/Miro prototypes, and stakeholder comments—must be preserved with clean Markdown/HTML structures.
2. **Universal Cross-Agent Compatibility**: The core MCP server and Skill adapters are designed to run seamlessly across all major AI coding agents (Google Antigravity, Claude Code, Cursor, Windsurf, Cline, Roo Code, GitHub Copilot).
3. **Deterministic Output**: Identical Confluence inputs must produce 100% deterministic, formatted Markdown.
4. **Safe Credential Handling**: Secrets and PATs are never logged, persisted in repositories, or hardcoded.
5. **Robust Local Fallback**: The package provides both an MCP Server interface and a standalone CLI runner (`python scripts/run_converter.py` / `npx confluence-prd-converter`).

---

## 📂 Project Structure

```
confluence-prd-converter/
├── bin/
│   └── confluence-prd-converter.js # Node.js CLI runner
├── core/
│   ├── clean.py                    # DOM & text sanitizer, system icon filter
│   ├── confluence_client.py        # Confluence REST API client & attachment downloader
│   ├── formatters.py               # Nested tables, Jira lozenges, Figma/Miro embeds, alerts
│   ├── parser.py                   # Unified AST & DOM parser (Storage XML & View HTML)
│   └── validator.py                # Markdown structural integrity & link validator
├── adapters/                       # Agent-specific skill adapters & rule files
│   ├── antigravity/                # Google Antigravity SKILL.md
│   ├── claude/                     # Claude Code CLAUDE.md
│   ├── cursor/                     # Cursor .mdc rule
│   ├── windsurf/                   # Windsurf rules
│   ├── cline/                      # Cline / Roo Code rules
│   ├── copilot/                    # GitHub Copilot instructions
│   ├── kiro/                       # Kiro steering instructions
│   └── continue/                   # Continue.dev prompt
├── evaluations/                    # Evaluation & Feedback Hub (RFCs & Study Cases)
│   ├── README.md                   # Bilingual evaluation guide
│   ├── TEMPLATE_FEEDBACK.md        # Reusable RFC template
│   └── archive/                    # Fulfilled evaluation study cases
├── scripts/
│   ├── run_converter.py            # Standalone CLI converter runner
│   └── validate_output.py          # Standalone CLI output validator
├── tests/                          # Automated unit test suite & sample fixtures
│   ├── sample_prd.html             # Generalized Confluence HTML export fixture
│   ├── sample_storage.xml          # Generalized Confluence Storage XML fixture
│   ├── test_converter.py           # Core conversion unit tests
│   └── test_all.py                 # Test suite aggregator
├── confluence-prd-converter.config.json # Project configuration file
├── schema.json                     # JSON Schema for configuration
├── server.py                       # FastMCP Server implementation (5 tools)
├── requirements.txt                # Python runtime dependencies
├── package.json                    # NPM package definition & CLI entry point
├── SKILL.md                        # Master Agent Skill definition
├── README.md                       # Comprehensive English documentation
├── README.id.md                    # Comprehensive Indonesian documentation
└── LICENSE                         # Apache License 2.0
```

---

## 🛠️ Development Setup & Running Tests

### Prerequisites
- Python 3.10+
- Node.js 18.0+ (optional, for `npx` / npm runner)

### Setup Virtual Environment
```bash
# Clone the repository
git clone https://github.com/hanifalkauni/confluence-prd-converter.git
cd confluence-prd-converter

# Install Python dependencies
pip install -r requirements.txt
```

### Running Test Suite
```bash
python tests/test_all.py
```

---

## 🧩 Adding Support for New Macros & Formats

If you need to support a new Confluence macro (e.g., custom Atlassian plugins, Lucidchart, PlantUML macros):

1. **Add DOM Transformation**:
   - In `core/parser.py`, handle the macro name in `parse_storage_xml` or `_process_node`.
2. **Add Unit Test**:
   - Add a test case in `tests/test_converter.py` and a fixture snippet in `tests/sample_prd.html` or `tests/sample_storage.xml`.
3. **Verify Integrity**:
   - Run `python tests/test_all.py` to ensure all tests pass.

---

## 📋 Evaluation & Feedback Hub (RFCs)

If you encounter real-world PRD pages with edge cases (broken layouts, unparsed custom macros, complex nested structures):

1. Copy [`evaluations/TEMPLATE_FEEDBACK.md`](./evaluations/TEMPLATE_FEEDBACK.md).
2. Name your file descriptively, e.g., `evaluations/FEEDBACK_LUCIDCHART_MACRO.md`.
3. Fill in the summary, sample XML/HTML snippet, expected output, and submit a PR!

---

## 📜 Pull Request Guidelines

1. Ensure all tests pass: `python tests/test_all.py`.
2. Keep code clean, modular, and typed.
3. Update both `README.md` and `README.id.md` if introducing new MCP tools or CLI flags.
4. Keep commit messages clear and concise (e.g., `feat(parser): add support for drawio macro`).
