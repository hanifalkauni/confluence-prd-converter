"""
Specialized Markdown and HTML formatters for Confluence elements:
- Compact nested tables inside Markdown cells
- Jira issue lozenges and links
- Miro and Figma embed iframes
- Info/Note/Warning/Tip callout panels
- Expanders (<details><summary>)
- Code blocks with syntax highlighting
- Image path mapping and icon filtering
"""

import re
import urllib.parse
from typing import Optional, Tuple
from bs4 import BeautifulSoup, Tag
from .clean import is_system_icon, clean_text


def format_nested_table_to_html(table_tag: Tag) -> str:
    """
    Convert a nested subtable into a clean, compact inline HTML table string.
    Ensures all inner newlines are removed or replaced with <br> so the parent
    Markdown table row remains on a single line.
    """
    if not table_tag:
        return ""

    rows_html = []
    
    # Process thead or initial th rows
    thead = table_tag.find("thead")
    header_rows = thead.find_all("tr") if thead else []
    
    tbody = table_tag.find("tbody") or table_tag
    body_rows = [tr for tr in tbody.find_all("tr", recursive=False) if tr not in header_rows]
    
    # Check if first row of tbody contains th
    if not header_rows and body_rows:
        first_row_ths = body_rows[0].find_all("th", recursive=False)
        if first_row_ths:
            header_rows = [body_rows.pop(0)]

    for tr in header_rows:
        cells = []
        for th in tr.find_all(["th", "td"], recursive=False):
            cell_text = inline_clean_html(th)
            cells.append(f"<th>{cell_text}</th>")
        rows_html.append(f"<tr>{''.join(cells)}</tr>")

    for tr in body_rows:
        cells = []
        for td in tr.find_all(["td", "th"], recursive=False):
            cell_text = inline_clean_html(td)
            cells.append(f"<td>{cell_text}</td>")
        rows_html.append(f"<tr>{''.join(cells)}</tr>")

    table_content = "".join(rows_html)
    return f"<table>{table_content}</table>"


def inline_clean_html(tag: Tag) -> str:
    """Format the contents of an inline cell into single-line HTML without breaking lines."""
    parts = []
    for child in tag.children:
        if isinstance(child, str):
            text = clean_text(child).strip()
            if text:
                parts.append(text)
        elif isinstance(child, Tag):
            tag_name = child.name.lower()
            if tag_name in ["script", "style"]:
                continue
            if tag_name == "br":
                parts.append("<br>")
            elif tag_name in ["b", "strong"]:
                parts.append(f"<b>{inline_clean_html(child)}</b>")
            elif tag_name in ["i", "em"]:
                parts.append(f"<i>{inline_clean_html(child)}</i>")
            elif tag_name == "code":
                parts.append(f"<code>{clean_text(child.get_text()).strip()}</code>")
            elif tag_name == "a":
                href = child.get("href", "#")
                link_text = inline_clean_html(child) or href
                parts.append(f'<a href="{href}">{link_text}</a>')
            elif tag_name == "span" and "jira-issue" in child.get("class", []):
                jira_formatted = format_jira_macro(child, inline_mode=True)
                parts.append(jira_formatted)
            elif tag_name == "span" and any(c in child.get("class", []) for c in ["aui-lozenge", "status-macro", "jira-status-lozenge"]):
                status_text = clean_text(child.get_text()).strip()
                parts.append(f"<code>{status_text}</code>")
            elif tag_name == "table":
                parts.append(format_nested_table_to_html(child))
            else:
                child_text = inline_clean_html(child)
                if child_text:
                    parts.append(child_text)
                    
    # Join with single space and remove any real line breaks
    combined = " ".join(parts).replace("\n", " ").replace("\r", " ")
    combined = re.sub(r"\s+", " ", combined).strip()
    return combined


def format_jira_macro(tag: Tag, inline_mode: bool = False) -> str:
    """
    Extract Jira Issue details (Key, URL, Summary, Status).
    Outputs: `• [KEY](https://jira.../browse/KEY) - Summary `Status`` or inline equivalent.
    """
    key = tag.get("data-jira-key")
    jira_url = ""
    summary = ""
    status = ""

    # Look for key link
    link_tag = tag.find("a", class_=re.compile(r"jira-issue-key|issue-link"))
    if not link_tag:
        link_tag = tag.find("a")
    if link_tag:
        jira_url = link_tag.get("href", "")
        if not key:
            key = link_tag.get_text().strip()

    # Look for summary
    summary_tag = tag.find("span", class_=re.compile(r"summary"))
    if summary_tag:
        summary = clean_text(summary_tag.get_text()).strip()

    # Look for status lozenge
    status_tag = tag.find("span", class_=re.compile(r"aui-lozenge|status|jira-status-lozenge"))
    if status_tag:
        status = clean_text(status_tag.get_text()).strip()

    if not key:
        key = clean_text(tag.get_text()).strip() or "JIRA-ISSUE"

    url_target = jira_url if jira_url else f"https://jira.atlassian.com/browse/{key}"

    if inline_mode:
        if status:
            return f'<a href="{url_target}">{key}</a> <code>{status}</code>'
        return f'<a href="{url_target}">{key}</a>'

    # Full bullet or reference mode
    components = [f"[{key}]({url_target})"]
    if summary:
        components.append(f"- {summary}")
    if status:
        components.append(f"`{status}`")

    return " ".join(components)


def format_embed_iframe(iframe_tag: Tag) -> str:
    """
    Extract Figma / Miro embed iframe source URL into clean markdown links.
    """
    src = iframe_tag.get("src", "")
    if not src:
        return ""

    # Check Figma
    if "figma.com" in src:
        parsed = urllib.parse.urlparse(src)
        qs = urllib.parse.parse_qs(parsed.query)
        if "url" in qs:
            actual_url = qs["url"][0]
        else:
            actual_url = src.replace("/embed?embed_host=confluence&url=", "")
            actual_url = urllib.parse.unquote(actual_url)
        return f"[Figma Design]({actual_url})"

    # Check Miro
    if "miro.com" in src:
        # Convert live-embed to board view URL
        board_url = src.replace("/app/live-embed/", "/app/board/").replace("/live-embed/", "/app/board/")
        board_url = board_url.split("?")[0]
        return f"[Miro Board]({board_url})"

    # Generic Iframe
    title = iframe_tag.get("title") or iframe_tag.get("name") or "Embedded Content"
    return f"[{title}]({src})"


def format_callout_panel(panel_tag: Tag, content_markdown: str, title: Optional[str] = None) -> str:
    """
    Convert Confluence info, note, tip, warning panels into GitHub Markdown alerts:
    > [!NOTE] / > [!WARNING] / > [!TIP] / > [!IMPORTANT]
    """
    raw_class = panel_tag.get("class", [])
    classes = (" ".join(raw_class) if isinstance(raw_class, list) else str(raw_class)).lower()
    
    alert_type = "NOTE"
    if "warning" in classes:
        alert_type = "WARNING"
    elif "note" in classes or "caution" in classes:
        alert_type = "CAUTION"
    elif "tip" in classes or "success" in classes:
        alert_type = "TIP"
    elif "info" in classes or "information" in classes:
        alert_type = "NOTE"
    elif "error" in classes or "alert" in classes:
        alert_type = "IMPORTANT"

    lines = [l for l in content_markdown.strip().split("\n") if l.strip()]
    formatted_lines = [f"> [!{alert_type}]"]
    if title and title.strip():
        formatted_lines.append(f"> **{title.strip()}**")
    for line in lines:
        # Strip redundant leading >
        clean_line = re.sub(r"^>\s*", "", line).strip()
        if clean_line:
            formatted_lines.append(f"> {clean_line}")

    return "\n".join(formatted_lines)


def format_code_block(code_tag: Tag) -> str:
    """
    Extract language and code content and format as fenced code block.
    """
    params = code_tag.get("data-syntaxhighlighter-params", "")
    language = "text"
    if params:
        match = re.search(r"brush:\s*([a-zA-Z0-9_\-]+)", params)
        if match:
            language = match.group(1).lower()
            if language == "js":
                language = "javascript"
            elif language == "py":
                language = "python"
            elif language == "sh" or language == "bash":
                language = "bash"

    code_text = code_tag.get_text()
    code_text = code_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    return f"```{language}\n{code_text}\n```"


def format_expand_macro(title: str, content_markdown: str) -> str:
    """
    Convert Confluence expand macro into HTML5 <details><summary>.
    """
    clean_title = title.strip() if title else "Details"
    return f"<details>\n<summary>{clean_title}</summary>\n\n{content_markdown.strip()}\n\n</details>"


def resolve_image_tag(img_tag: Tag, assets_folder: str = "assets") -> Optional[str]:
    """
    Resolve image source, filter out system icons, and map to local assets folder.
    Returns Markdown image string `![Alt](assets/filename.png)` or None if filtered.
    """
    src = img_tag.get("src", "")
    if not src:
        src = img_tag.get("data-image-src", "")
    if not src:
        return None

    # Check if system icon
    if is_system_icon(src):
        return None

    alt = clean_text(img_tag.get("alt", "")).strip()
    title = clean_text(img_tag.get("title", "")).strip()
    label = alt or title or "Mockup / Diagram"

    # Extract clean filename
    unquoted = urllib.parse.unquote(src)
    path_part = unquoted.split("?")[0]
    filename = path_part.split("/")[-1]
    
    if not filename:
        filename = "image.png"

    if is_system_icon(filename):
        return None

    # Map to local assets folder path
    if assets_folder.startswith("./") or assets_folder.startswith("../") or "/" in assets_folder or "\\" in assets_folder:
        clean_assets_dir = assets_folder.replace("\\", "/").rstrip("/")
        mapped_path = f"{clean_assets_dir}/{filename}"
    else:
        mapped_path = f"./{assets_folder}/{filename}"

    return f"![{label}]({mapped_path})"
