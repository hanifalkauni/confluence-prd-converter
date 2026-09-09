# 🛡️ Security Policy — Confluence PRD Converter

## Supported Versions

We actively maintain and provide security patches for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0.0 | :x:                |

---

## 🔒 Handling Credentials & Access Tokens

1. **Personal Access Tokens (PAT)**:
   - `confluence-prd-converter` uses Confluence Personal Access Tokens (`CONFLUENCE_PAT`) or API tokens to authenticate with Confluence REST API.
   - **Never hardcode tokens in git repositories**. Tokens should always be supplied via environment variables (`CONFLUENCE_PAT`), `.env` files (which are git-ignored by default), or configured inside secure local MCP settings (`mcp_config.json`).
   - The converter discovers credentials in a safe hierarchical order: Explicit parameters -> Process Environment -> Local MCP configuration.

2. **DOM Sanitization & Safe Parsing**:
   - The core parser sanitizes all incoming HTML/XML content, stripping executable scripts (`<script>`), untrusted iframe sources outside configured embeds, tracking pixels, and inline event handlers (`onclick`, `onhover`).

---

## 🚨 Reporting a Vulnerability

If you discover a potential security vulnerability in `confluence-prd-converter`:

1. **Do NOT open a public GitHub Issue** for unpatched vulnerabilities.
2. Report the vulnerability privately via **[GitHub Private Vulnerability Reporting](https://github.com/hanifalkauni/confluence-prd-converter/security/advisories/new)** or contact the maintainer directly.
3. The maintainer team will acknowledge your report within **24 hours** and coordinate a fix and release.
