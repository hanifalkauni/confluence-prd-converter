"""
Confluence PRD Converter - Core Module
Universal Parser, Transformer, and Validator for Confluence PRD documents.
"""

from .clean import clean_dom, clean_text, sanitize_html
from .formatters import (
    format_nested_table_to_html,
    format_jira_macro,
    format_embed_iframe,
    format_callout_panel,
    format_code_block,
    format_expand_macro,
    resolve_image_tag
)
from .confluence_client import ConfluenceClient
from .parser import ConfluencePRDParser
from .validator import PRDValidator
from .security import assert_not_sensitive_path, sanitize_subfolder_name, ALLOWED_DOC_EXTENSIONS
from .related import format_related_section, md_safe
from .settings import load_config, get_table_mode, get_related_defaults

__all__ = [
    "clean_dom",
    "clean_text",
    "sanitize_html",
    "format_nested_table_to_html",
    "format_jira_macro",
    "format_embed_iframe",
    "format_callout_panel",
    "format_code_block",
    "format_expand_macro",
    "resolve_image_tag",
    "ConfluenceClient",
    "ConfluencePRDParser",
    "PRDValidator",
    "assert_not_sensitive_path",
    "sanitize_subfolder_name",
    "ALLOWED_DOC_EXTENSIONS",
    "format_related_section",
    "md_safe",
    "load_config",
    "get_table_mode",
    "get_related_defaults"
]
