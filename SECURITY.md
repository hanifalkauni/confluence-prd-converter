# 🛡️ Security Policy — Confluence PRD Converter

## Supported Versions

We actively maintain and provide security patches for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0.0 | :x:                |

---

## 🔒 Defense-in-Depth Security Controls

1. **Zero In-Band Credential Exposure**:
   - MCP tools (`fetch_and_convert_from_confluence`, etc.) and the CLI runner never accept Personal Access Tokens (`CONFLUENCE_PAT`) as tool or command-line arguments. This guarantees that tokens can never be passed through the AI model context window, chat logs, or OS process argument tables.
   - **Never hardcode tokens in git repositories**. Always supply credentials via operating system environment variables (`CONFLUENCE_URL`, `CONFLUENCE_PAT`) or protect runtime sessions with [Samar MCP](https://github.com/hanifalkauni/samar-mcp) privacy middleware.

2. **Strict Same-Origin Authorization Guard & Anti-SSRF**:
   - The `Authorization: Bearer` header is strictly bound to the configured `CONFLUENCE_URL` origin (scheme, hostname, and port).
   - Cross-origin URL overrides do not inherit fallback credentials, HTTP redirects (`301`/`302`/`307`/`308`) are disabled on authenticated API calls, and link-local cloud instance metadata endpoints as well as internal `.internal`/`.goog` domains are explicitly blocked.

3. **Path Traversal Confinement & Document Allowlist (`CWE-22`)**:
   - Downloaded Confluence image attachments are strictly sanitized and confined to the target `assets` directory, blocking directory traversal sequences, hidden dotfiles, and non-image extensions.
   - File read/write tools enforce a strict document extension allowlist (`.md`, `.markdown`, `.html`, `.htm`, `.xml`, `.xhtml`), blocking access to any configuration, credential, or key files.

4. **Automatic Secret Redaction & DOM Sanitization**:
   - All exception and error messages are automatically scrubbed by `sanitize_secret()` to redact any `Bearer`, `Basic`, URL userinfo, or token values before returning to the caller.
   - The core parser sanitizes incoming HTML/XML content, stripping executable scripts (`<script>`), untrusted iframes, tracking pixels, and inline event handlers (`onclick`, `onhover`).

5. **Opt-In Related Pages & Shared Path Policy**:
   - Related-page discovery (`find_related_confluence_pages`, `include_related_pages`, CLI `--related`) is OFF by default and runs only on explicit user request, starting solely from the page the user supplied. It returns metadata only; related page content is never fetched automatically.
   - All CQL values are escaped, result counts are clamped, relation types are allowlisted, page IDs must be numeric, and remote titles are Markdown-escaped before being written to `prd.md`.
   - The CLI runner enforces the same document-extension allowlist and assets-subfolder sanitization as the MCP server (`core/security.py`). The validator never probes files outside the document directory.
   - `confluence-prd-converter.config.json` never supplies credentials; `url`/`pat` entries are ignored and placeholder values are discarded (`core/settings.py`).
---

## 🚨 Reporting a Vulnerability

If you discover a potential security vulnerability in `confluence-prd-converter`:

1. **Do NOT open a public GitHub Issue** for unpatched vulnerabilities.
2. Report the vulnerability privately via **[GitHub Private Vulnerability Reporting](https://github.com/hanifalkauni/confluence-prd-converter/security/advisories/new)** or contact the maintainer directly.
3. The maintainer team will acknowledge your report within **24 hours** and coordinate a fix and release.
