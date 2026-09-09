"""
DOM and text sanitizer for Confluence HTML / XML pages.
Removes boilerplate UI, navigation, scripts, and normalizes characters.
"""

import re
from bs4 import BeautifulSoup, Comment, Tag


# Classes and IDs to strip completely from DOM
BOILERPLATE_SELECTORS = [
    "script",
    "style",
    "noscript",
    "meta",
    "link",
    "#floating-scrollbar",
    ".floating-scrollbar",
    ".aui-dropdown2",
    ".copy-heading-link",
    ".toc-macro",
    ".edit-section",
    ".breadcrumbs",
    ".page-metadata",
    ".page-metadata-modification-info",
    "#header-container",
    "#footer-container",
    ".likes-section",
    ".ia-fixed-sidebar",
    ".confluence-quick-edit",
    ".quick-comment-prompt",
    ".navigation",
    ".plugin_pagetree",
    ".noprint",
    ".aui-nav-container",
    ".aui-header",
    "#navigation",
    "#footer",
    "#sidebar",
    ".hidden",
    ".assistive",
    ".user-logo-container",
]

# Unwanted small system icon filenames that should not be converted to images
SYSTEM_ICON_PATTERNS = [
    r"epic\.svg",
    r"story\.svg",
    r"task\.svg",
    r"bug\.svg",
    r"subtask\.svg",
    r"viewavatar",
    r"default\.svg",
    r"icon-section",
    r"favicon",
    r"jira-favicon",
    r"emoticon",
    r"s_icon",
    r"star_off",
    r"star_on",
    r"confluence-logo",
    r"space-logo",
]


def clean_text(text: str) -> str:
    """Normalize text characters, remove zero-width chars and clean whitespaces."""
    if not text:
        return ""
    # Remove zero-width spaces & BOM
    text = text.replace("\u200b", "").replace("\ufeff", "").replace("\u200e", "").replace("\u200f", "")
    # Normalize non-breaking spaces
    text = text.replace("\u00a0", " ")
    # Fix common unicode quotation issues if any
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def is_system_icon(src_or_filename: str) -> bool:
    """Check if the image source is a tiny Confluence/Jira system icon."""
    if not src_or_filename:
        return False
    lower = src_or_filename.lower()
    for pattern in SYSTEM_ICON_PATTERNS:
        if re.search(pattern, lower):
            return True
    return False


def clean_dom(soup: BeautifulSoup) -> BeautifulSoup:
    """Clean unwanted UI elements, comments, and boilerplate from BeautifulSoup object."""
    # Remove HTML comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove boilerplate selectors
    for selector in BOILERPLATE_SELECTORS:
        for el in soup.select(selector):
            el.decompose()

    # Remove inline onclick/onhover attributes
    for el in soup.find_all(True):
        if isinstance(el, Tag):
            for attr in list(el.attrs.keys()):
                if attr.lower().startswith("on") or attr.lower() in ["data-tooltip", "data-rendered"]:
                    del el.attrs[attr]

    return soup


def sanitize_html(html_content: str) -> str:
    """Sanitize raw HTML string before parsing."""
    if not html_content:
        return ""
    cleaned = clean_text(html_content)
    return cleaned
