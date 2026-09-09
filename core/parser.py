"""
Confluence PRD Parser Engine:
Converts Confluence View HTML and Storage XML into clean, professional Markdown.
"""

import re
import warnings
from bs4 import BeautifulSoup, Tag, NavigableString, XMLParsedAsHTMLWarning
from typing import Optional, List, Dict, Any

# Suppress XMLParsedAsHTMLWarning when handling Confluence payloads
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from .clean import clean_dom, clean_text, sanitize_html, is_system_icon
from .formatters import (
    format_nested_table_to_html,
    format_jira_macro,
    format_embed_iframe,
    format_callout_panel,
    format_code_block,
    format_expand_macro,
    resolve_image_tag
)


class ConfluencePRDParser:
    """Core parser transforming Confluence HTML and XML storage formats into Markdown."""

    def __init__(self, assets_folder: str = "assets", preserve_nested_tables: bool = True):
        self.assets_folder = assets_folder
        self.preserve_nested_tables = preserve_nested_tables

    def parse_html(self, html_content: str, title: Optional[str] = None) -> str:
        """Parse Confluence View/Export HTML content into Markdown."""
        if not html_content or not html_content.strip():
            return ""

        sanitized = sanitize_html(html_content)
        soup = BeautifulSoup(sanitized, "html.parser")
        soup = clean_dom(soup)

        # Locate main content container if present
        content_container = (
            soup.find("div", id="main-content")
            or soup.find("div", id="content")
            or soup.find("div", class_="pageSection")
            or soup.find("div", class_="wiki-content")
            or soup.body
            or soup
        )

        md_output = self._process_node(content_container).strip()

        # Add top title if provided and document does not already begin with an H1 heading
        if title:
            clean_t = clean_text(title).strip()
            if not re.match(r"^#\s+", md_output.strip()):
                md_output = f"# {clean_t}\n\n{md_output}"

        # Clean trailing and repetitive whitespace
        md_output = re.sub(r"\n{3,}", "\n\n", md_output).strip() + "\n"
        return md_output

    def parse_storage_xml(self, xml_content: str, title: Optional[str] = None) -> str:
        """Parse Confluence Storage XML format (<ac:structured-macro> etc.) into Markdown."""
        if not xml_content or not xml_content.strip():
            return ""

        # Wrap in root to handle partial xml fragments
        wrapped_xml = f"<storage_root>{xml_content}</storage_root>"
        soup = BeautifulSoup(wrapped_xml, "xml")

        # 1. Transform <ac:structured-macro> or <structured-macro>
        for macro in soup.find_all(lambda t: t.name in ["structured-macro", "ac:structured-macro"]):
            macro_name = (macro.get("ac:name") or macro.get("name") or "").lower()

            # Jira Issue Macro
            if macro_name in ["jira", "jiraissues"]:
                key = ""
                key_param = macro.find(lambda t: t.name.endswith("parameter") and (t.get("ac:name") == "key" or t.get("name") == "key"))
                if key_param:
                    key = key_param.get_text().strip()

                span_jira = soup.new_tag("span")
                span_jira["class"] = "jira-issue"
                if key:
                    span_jira["data-jira-key"] = key
                    a_link = soup.new_tag("a")
                    a_link["href"] = f"https://jira.atlassian.com/browse/{key}"
                    a_link["class"] = "jira-issue-key"
                    a_link.string = key
                    span_jira.append(a_link)
                macro.replace_with(span_jira)

            # Info / Note / Warning / Tip Panels
            elif macro_name in ["info", "note", "tip", "warning", "panel"]:
                panel_div = soup.new_tag("div")
                panel_div["class"] = f"confluence-information-macro confluence-information-macro-{macro_name}"
                body = macro.find(lambda t: t.name.endswith("rich-text-body") or t.name.endswith("body"))
                if body:
                    body_div = soup.new_tag("div")
                    body_div["class"] = "confluence-information-macro-body"
                    for child in list(body.children):
                        body_div.append(child.extract())
                    panel_div.append(body_div)
                macro.replace_with(panel_div)

            # Code Block Macro
            elif macro_name in ["code", "noformat"]:
                pre_tag = soup.new_tag("pre")
                lang_param = macro.find(lambda t: t.name.endswith("parameter") and (t.get("ac:name") == "language" or t.get("name") == "language"))
                lang = lang_param.get_text().strip() if lang_param else "text"
                pre_tag["data-syntaxhighlighter-params"] = f"brush: {lang};"
                body = macro.find(lambda t: t.name.endswith("plain-text-body") or t.name.endswith("body"))
                pre_tag.string = body.get_text() if body else ""
                macro.replace_with(pre_tag)

            # Expand Macro
            elif macro_name == "expand":
                expand_div = soup.new_tag("div")
                expand_div["class"] = "expand-container"
                title_param = macro.find(lambda t: t.name.endswith("parameter") and (t.get("ac:name") == "title" or t.get("name") == "title"))
                title_span = soup.new_tag("span")
                title_span["class"] = "expand-control-text"
                title_span.string = title_param.get_text().strip() if title_param else "Details"
                expand_div.append(title_span)
                body = macro.find(lambda t: t.name.endswith("rich-text-body") or t.name.endswith("body"))
                if body:
                    content_div = soup.new_tag("div")
                    content_div["class"] = "expand-content"
                    for child in list(body.children):
                        content_div.append(child.extract())
                    expand_div.append(content_div)
                macro.replace_with(expand_div)

            # Status Macro
            elif macro_name == "status":
                title_param = macro.find(lambda t: t.name.endswith("parameter") and (t.get("ac:name") == "title" or t.get("name") == "title"))
                status_title = title_param.get_text().strip() if title_param else "STATUS"
                span_status = soup.new_tag("span")
                span_status["class"] = "aui-lozenge status-macro"
                span_status.string = status_title
                macro.replace_with(span_status)

            # Draw.io Diagram Macro
            elif macro_name in ["drawio", "inc-drawio", "drawio-viewer"]:
                name_param = macro.find(lambda t: t.name.endswith("parameter") and (t.get("ac:name") in ["diagramName", "name", "diagramDisplayName"] or t.get("name") in ["diagramName", "name", "diagramDisplayName"]))
                diagram_name = name_param.get_text().strip() if name_param else "Diagram"
                img_filename = f"{diagram_name}.png" if not diagram_name.lower().endswith((".png", ".jpg", ".svg")) else diagram_name
                img_tag = soup.new_tag("img")
                img_tag["src"] = img_filename
                img_tag["alt"] = f"Draw.io Diagram: {diagram_name}"
                macro.replace_with(img_tag)

            # Widget / Iframe Macro (Figma, Miro)
            elif macro_name in ["widget", "iframe", "html"]:
                url_param = macro.find(lambda t: t.name.endswith("parameter") and (t.get("ac:name") == "url" or t.get("name") == "url" or t.get("ac:name") == "src"))
                url = url_param.get_text().strip() if url_param else ""
                if not url:
                    body = macro.find(lambda t: t.name.endswith("plain-text-body") or t.name.endswith("body"))
                    if body and "<iframe" in body.get_text():
                        match_src = re.search(r'src=["\'](.*?)["\']', body.get_text())
                        if match_src:
                            url = match_src.group(1)

                if url:
                    iframe_tag = soup.new_tag("iframe")
                    iframe_tag["src"] = url
                    macro.replace_with(iframe_tag)
                else:
                    macro.decompose()
            else:
                body = macro.find(lambda t: t.name.endswith("rich-text-body") or t.name.endswith("body"))
                if body:
                    div = soup.new_tag("div")
                    for child in list(body.children):
                        div.append(child.extract())
                    macro.replace_with(div)
                else:
                    macro.decompose()

        # 2. Transform <ac:image> / <image>
        for img_macro in soup.find_all(lambda t: t.name in ["image", "ac:image"]):
            att = img_macro.find(lambda t: t.name.endswith("attachment"))
            url_res = img_macro.find(lambda t: t.name.endswith("url"))
            filename = ""
            if att:
                filename = att.get("ri:filename") or att.get("filename") or ""
            elif url_res:
                filename = url_res.get("ri:value") or url_res.get("value") or ""

            if filename:
                img_tag = soup.new_tag("img")
                img_tag["src"] = filename
                img_tag["alt"] = filename
                img_macro.replace_with(img_tag)
            else:
                img_macro.decompose()

        # 3. Transform <ac:task-list> / <task-list>
        for task_list in soup.find_all(lambda t: t.name in ["task-list", "ac:task-list"]):
            ul_tag = soup.new_tag("ul")
            ul_tag["class"] = "inline-task-list"
            for task in task_list.find_all(lambda t: t.name in ["task", "ac:task"]):
                status = task.find(lambda t: t.name.endswith("task-status"))
                body = task.find(lambda t: t.name.endswith("task-body"))
                is_complete = status and status.get_text().strip().lower() == "complete"
                li_tag = soup.new_tag("li")
                if is_complete:
                    li_tag["class"] = "checked"
                if body:
                    for child in list(body.children):
                        li_tag.append(child.extract())
                ul_tag.append(li_tag)
            task_list.replace_with(ul_tag)

        # 4. Transform <ac:link>
        for link_macro in soup.find_all(lambda t: t.name in ["link", "ac:link"]):
            page_ref = link_macro.find(lambda t: t.name.endswith("page"))
            user_ref = link_macro.find(lambda t: t.name.endswith("user"))
            body = link_macro.find(lambda t: t.name.endswith("link-body") or t.name.endswith("plain-text-link-body"))
            link_text = body.get_text().strip() if body else ""

            if page_ref:
                target = page_ref.get("ri:content-title") or page_ref.get("content-title") or "Page"
                text = link_text or target
                a_tag = soup.new_tag("a")
                a_tag["href"] = f"#{target.lower().replace(' ', '-')}"
                a_tag.string = text
                link_macro.replace_with(a_tag)
            elif user_ref:
                user = user_ref.get("ri:userkey") or user_ref.get("userkey") or "User"
                span_user = soup.new_tag("span")
                span_user.string = f"@{link_text or user}"
                link_macro.replace_with(span_user)
            else:
                if link_text:
                    span_text = soup.new_tag("span")
                    span_text.string = link_text
                    link_macro.replace_with(span_text)
                else:
                    link_macro.decompose()

        # Process AST root directly
        root = soup.find("storage_root") or soup
        md_output = self._process_node(root).strip()

        if title:
            clean_t = clean_text(title).strip()
            if not re.match(r"^#\s+", md_output.strip()):
                md_output = f"# {clean_t}\n\n{md_output}"

        md_output = re.sub(r"\n{3,}", "\n\n", md_output).strip() + "\n"
        return md_output

    def format_comments_section(self, comments: List[Dict[str, Any]]) -> str:
        """
        Format a list of discussion comments into a structured Markdown section.
        """
        if not comments:
            return ""

        sections = [
            "---",
            "## 💬 Discussions & Page Comments",
            ""
        ]

        for c in comments:
            author = c.get("author", "Unknown Author")
            date_str = c.get("date", "")
            if "T" in date_str:
                date_display = date_str.replace("T", " ").split(".")[0]
                if not date_display.endswith("UTC"):
                    date_display += " UTC"
            else:
                date_display = date_str

            header = f"> 👤 **{author}**"
            if date_display:
                header += f" — *{date_display}*"

            body_storage = c.get("body_storage", "")
            body_view = c.get("body_view", "")
            body_raw = body_storage or body_view or c.get("body", "")

            if body_storage:
                body_md = self.parse_storage_xml(body_storage).strip()
            elif body_view:
                body_md = self.parse_html(body_view).strip()
            elif body_raw:
                body_md = clean_text(str(body_raw)).strip()
            else:
                body_md = ""

            # Remove leading H1/H2 heading if it was mistakenly parsed as title
            body_md = re.sub(r"^#+\s*.*?\n+", "", body_md).strip()

            body_lines = [f"> {line}" if line.strip() else ">" for line in body_md.split("\n")]
            sections.append(header)
            sections.append(">")
            sections.extend(body_lines)
            sections.append("")

        return "\n".join(sections).strip() + "\n"

    def _process_node(self, node: Any, depth: int = 0) -> str:
        """Recursively process DOM nodes and generate Markdown."""
        if isinstance(node, NavigableString):
            text = clean_text(str(node))
            return text

        if not isinstance(node, Tag):
            return ""

        tag_name = node.name.lower()

        # Headings
        if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(tag_name[1])
            heading_text = self._process_children_inline(node).strip()
            if heading_text:
                return f"\n\n{'#' * level} {heading_text}\n\n"
            return ""

        # Paragraphs & Containers
        elif tag_name in ["p", "div", "section", "article", "storage_root"]:
            raw_classes = node.get("class", [])
            class_str = " ".join(raw_classes) if isinstance(raw_classes, list) else str(raw_classes)
            classes_list = raw_classes if isinstance(raw_classes, list) else class_str.split()

            # Specialized Callout Macro
            if "confluence-information-macro" in class_str:
                title_tag = node.find(class_=re.compile(r"title|confluence-information-macro-title"))
                title_text = title_tag.get_text().strip() if title_tag else ""
                
                body_tag = node.find(class_=re.compile(r"confluence-information-macro-body|body")) or node
                inner_parts = []
                for child in body_tag.children:
                    if child != title_tag:
                        inner_parts.append(self._process_node(child))
                inner_md = "".join(inner_parts).strip()
                return f"\n\n{format_callout_panel(node, inner_md, title=title_text)}\n\n"

            # Specialized Expand Macro
            if "expand-container" in class_str:
                title_tag = node.find(class_=re.compile(r"expand-control-text|title"))
                title_text = title_tag.get_text().strip() if title_tag else "Details"
                content_tag = node.find(class_=re.compile(r"expand-content|body")) or node
                inner_parts = []
                for child in content_tag.children:
                    child_cls = str(child.get("class", "")) if isinstance(child, Tag) else ""
                    if "expand-control" not in child_cls:
                        inner_parts.append(self._process_node(child))
                inner_md = "".join(inner_parts).strip()
                return f"\n\n{format_expand_macro(title_text, inner_md)}\n\n"

            # Specialized Code Panel
            if "code" in classes_list and "panel" in classes_list:
                pre = node.find("pre")
                if pre:
                    return f"\n\n{format_code_block(pre)}\n\n"

            # Specialized Comments Section (Static HTML exports)
            if node.get("id") == "comments-section" or "comments-section" in class_str:
                comments_list = node.find_all("div", class_="comment")
                if not comments_list:
                    comments_list = node.find_all("div", class_="pageSection")
                extracted_comments = []
                for c_tag in comments_list:
                    author_tag = c_tag.find(class_=re.compile(r"url|fn|author|userLogoLink"))
                    date_tag = c_tag.find(class_=re.compile(r"comment-date|date"))
                    body_tag = c_tag.find(class_=re.compile(r"comment-body|wiki-content")) or c_tag
                    
                    author = author_tag.get_text().strip() if author_tag else "Commenter"
                    date_val = date_tag.get_text().strip() if date_tag else ""
                    body_html = ""
                    if body_tag:
                        body_parts = []
                        for child in body_tag.children:
                            if child not in [author_tag, date_tag]:
                                body_parts.append(self._process_node(child))
                        body_html = "".join(body_parts).strip()

                    if body_html:
                        extracted_comments.append({
                            "author": author,
                            "date": date_val,
                            "body": body_html
                        })
                if extracted_comments:
                    return "\n\n" + self.format_comments_section(extracted_comments) + "\n\n"

            inner_content = self._process_children_block(node).strip()
            if inner_content:
                return f"\n\n{inner_content}\n\n"
            return ""

        # Preformatted Code Block
        elif tag_name == "pre":
            return f"\n\n{format_code_block(node)}\n\n"

        # Blockquote
        elif tag_name == "blockquote":
            inner_md = self._process_children_block(node).strip()
            quoted_lines = [f"> {line}" if line.strip() else ">" for line in inner_md.split("\n")]
            return f"\n\n{chr(10).join(quoted_lines)}\n\n"

        # Lists
        elif tag_name in ["ul", "ol"]:
            is_ordered = (tag_name == "ol")
            raw_ul_cls = node.get("class", "")
            ul_cls_str = " ".join(raw_ul_cls) if isinstance(raw_ul_cls, list) else str(raw_ul_cls)
            is_task_list = "inline-task-list" in ul_cls_str
            items = []
            
            counter = 1
            for li in node.find_all("li", recursive=False):
                raw_li_cls = li.get("class", "")
                li_cls_str = " ".join(raw_li_cls) if isinstance(raw_li_cls, list) else str(raw_li_cls)
                if is_task_list or "checked" in li_cls_str or "task" in li_cls_str:
                    is_checked = "checked" in li_cls_str or "complete" in li_cls_str
                    prefix = "- [x] " if is_checked else "- [ ] "
                elif is_ordered:
                    prefix = f"{counter}. "
                    counter += 1
                else:
                    prefix = "- "

                li_text = self._process_children_block(li).strip()
                lines = li_text.split("\n")
                if lines:
                    formatted_item = f"{prefix}{lines[0]}"
                    if len(lines) > 1:
                        indent = "   " if is_ordered else "  "
                        formatted_item += "\n" + "\n".join(f"{indent}{l}" for l in lines[1:])
                    items.append(formatted_item)

            if items:
                return "\n\n" + "\n".join(items) + "\n\n"
            return ""

        # Tables
        elif tag_name == "table":
            return self._render_markdown_table(node)

        # Jira Issue Span
        elif tag_name == "span" and "jira-issue" in (node.get("class", "") if isinstance(node.get("class", ""), str) else " ".join(node.get("class", []))):
            return format_jira_macro(node)

        # Status Lozenge Span
        elif tag_name == "span" and any(c in (node.get("class", "") if isinstance(node.get("class", ""), str) else " ".join(node.get("class", []))) for c in ["aui-lozenge", "status-macro", "jira-status-lozenge"]):
            status_text = clean_text(node.get_text()).strip()
            return f"`{status_text}`"

        # Images
        elif tag_name == "img":
            img_md = resolve_image_tag(node, self.assets_folder)
            return f"\n\n{img_md}\n\n" if img_md else ""

        # Iframes (Figma / Miro)
        elif tag_name == "iframe":
            embed_md = format_embed_iframe(node)
            return f"\n\n{embed_md}\n\n" if embed_md else ""

        # Horizontal Rule
        elif tag_name == "hr":
            return "\n\n---\n\n"

        # Line Break
        elif tag_name == "br":
            return "\n"

        # Links
        elif tag_name == "a":
            href = node.get("href", "#")
            text = self._process_children_inline(node).strip() or href
            return f"[{text}]({href})"

        # Formatting tags
        elif tag_name in ["b", "strong"]:
            text = self._process_children_inline(node)
            return f"**{text}**" if text else ""
        elif tag_name in ["i", "em"]:
            text = self._process_children_inline(node)
            return f"*{text}*" if text else ""
        elif tag_name in ["del", "s", "strike"]:
            text = self._process_children_inline(node)
            return f"~~{text}~~" if text else ""
        elif tag_name == "code":
            text = clean_text(node.get_text()).strip()
            return f"`{text}`" if text else ""

        # Fallback for container tags
        else:
            return self._process_children_block(node)

    def _process_children_block(self, tag: Tag) -> str:
        """Process all children of a container node and join result."""
        result = []
        for child in tag.children:
            res = self._process_node(child)
            if res:
                result.append(res)
        return "".join(result)

    def _process_children_inline(self, tag: Tag) -> str:
        """Process children in inline mode."""
        result = []
        for child in tag.children:
            if isinstance(child, NavigableString):
                result.append(clean_text(str(child)))
            elif isinstance(child, Tag):
                t_name = child.name.lower()
                if t_name in ["b", "strong"]:
                    result.append(f"**{self._process_children_inline(child)}**")
                elif t_name in ["i", "em"]:
                    result.append(f"*{self._process_children_inline(child)}*")
                elif t_name == "code":
                    result.append(f"`{clean_text(child.get_text()).strip()}`")
                elif t_name == "a":
                    classes = child.get("class", [])
                    class_str = " ".join(classes) if isinstance(classes, list) else str(classes)
                    inline_text = self._process_children_inline(child).strip()
                    if "user-mention" in class_str or "confluence-userlink" in class_str:
                        result.append(f"@{inline_text}")
                    else:
                        href = child.get("href", "#")
                        result.append(f"[{inline_text or href}]({href})")
                elif t_name == "img":
                    img_md = resolve_image_tag(child, self.assets_folder)
                    if img_md:
                        result.append(f" {img_md} ")
                elif t_name == "span" and "jira-issue" in (child.get("class", "") if isinstance(child.get("class", ""), str) else " ".join(child.get("class", []))):
                    result.append(format_jira_macro(child))
                elif t_name == "span" and any(c in (child.get("class", "") if isinstance(child.get("class", ""), str) else " ".join(child.get("class", []))) for c in ["aui-lozenge", "status-macro", "jira-status-lozenge"]):
                    result.append(f"`{clean_text(child.get_text()).strip()}`")
                else:
                    result.append(self._process_children_inline(child))
        return clean_text("".join(result)).strip()

    def _render_markdown_table(self, table: Tag) -> str:
        """
        Convert a <table> into a Markdown table.
        Nested subtables are transformed into compact HTML <table> inside the cell.
        """
        thead = table.find("thead")
        header_trs = thead.find_all("tr", recursive=False) if thead else []
        
        tbody = table.find("tbody") or table
        body_trs = [tr for tr in tbody.find_all("tr", recursive=False) if tr not in header_trs]

        headers = []
        if header_trs:
            header_cells = header_trs[0].find_all(["th", "td"], recursive=False)
            headers = [self._render_cell_content(c) for c in header_cells]
        elif body_trs:
            first_cells = body_trs[0].find_all(["th", "td"], recursive=False)
            if all(c.name == "th" for c in first_cells):
                headers = [self._render_cell_content(c) for c in first_cells]
                body_trs.pop(0)

        data_rows = []
        for tr in body_trs:
            cells = tr.find_all(["td", "th"], recursive=False)
            data_rows.append([self._render_cell_content(c) for c in cells])

        if not headers and data_rows:
            col_count = max(len(r) for r in data_rows) if data_rows else 1
            headers = [f"Col {i+1}" for i in range(col_count)]

        if not headers and not data_rows:
            return ""

        max_cols = max(len(headers), max((len(r) for r in data_rows), default=0))
        while len(headers) < max_cols:
            headers.append("")

        for r in data_rows:
            while len(r) < max_cols:
                r.append("")

        header_line = "| " + " | ".join(headers) + " |"
        sep_line = "| " + " | ".join(["---"] * max_cols) + " |"
        
        row_lines = []
        for r in data_rows:
            row_lines.append("| " + " | ".join(r) + " |")

        table_md = "\n\n" + "\n".join([header_line, sep_line] + row_lines) + "\n\n"
        return table_md

    def _render_cell_content(self, cell_tag: Tag) -> str:
        """Format table cell content, escaping pipes and preserving nested tables."""
        if not cell_tag:
            return ""

        nested_table = cell_tag.find("table")
        if nested_table and self.preserve_nested_tables:
            return format_nested_table_to_html(nested_table)

        cell_parts = []
        for child in cell_tag.children:
            if isinstance(child, NavigableString):
                t = clean_text(str(child)).strip()
                if t:
                    cell_parts.append(t)
            elif isinstance(child, Tag):
                c_name = child.name.lower()
                if c_name == "br":
                    cell_parts.append("<br>")
                elif c_name in ["b", "strong"]:
                    cell_parts.append(f"**{self._process_children_inline(child)}**")
                elif c_name in ["i", "em"]:
                    cell_parts.append(f"*{self._process_children_inline(child)}*")
                elif c_name == "code":
                    cell_parts.append(f"`{clean_text(child.get_text()).strip()}`")
                elif c_name == "a":
                    href = child.get("href", "#")
                    text = self._process_children_inline(child) or href
                    cell_parts.append(f"[{text}]({href})")
                elif c_name == "span" and "jira-issue" in child.get("class", []):
                    cell_parts.append(format_jira_macro(child))
                elif c_name == "span" and any(c in child.get("class", []) for c in ["aui-lozenge", "status-macro", "jira-status-lozenge"]):
                    status_text = clean_text(child.get_text()).strip()
                    cell_parts.append(f"`{status_text}`")
                elif c_name == "img":
                    img_md = resolve_image_tag(child, self.assets_folder)
                    if img_md:
                        cell_parts.append(img_md)
                elif c_name in ["ul", "ol"]:
                    list_items = [f"• {self._process_children_inline(li)}" for li in child.find_all("li")]
                    cell_parts.append("<br>".join(list_items))
                else:
                    txt = self._process_children_inline(child)
                    if txt:
                        cell_parts.append(txt)

        content = " ".join(cell_parts)
        content = content.replace("|", "\\|")
        content = content.replace("\n", "<br>").replace("\r", "")
        content = re.sub(r"\s+", " ", content).strip()
        return content or " "
