"""
Rendering helpers for the opt-in 'Related Confluence Documents' section (shared by MCP server and CLI).
Titles come from remote pages and are treated as untrusted data (Markdown-escaped).
"""

import re
from typing import Any, Dict, List

RELATION_LABELS = {
    "parent": "Parent",
    "child": "Sub-pages",
    "content_link": "Linked from content",
    "backlink": "Pages linking here",
    "shared_label": "Shared labels",
    "similar_title": "Similar titles",
}


def md_safe(text: str) -> str:
    """Neutralize Markdown/HTML injection coming from remote page titles."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    return re.sub(r"([\\\[\]<>`*_|])", r"\\\1", t)


def format_related_section(pages: List[Dict[str, Any]]) -> str:
    lines = ["---", "## 🔗 Related Confluence Documents", ""]
    for rel, label in RELATION_LABELS.items():
        group = [p for p in pages if p["relation"] == rel]
        if group:
            lines.append(f"**{label}**")
            lines.extend(f"- [{md_safe(p['title']) or p['page_id']}]({p['url']}) (`{p['page_id']}`)" for p in group)
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
