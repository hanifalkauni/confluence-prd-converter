"""
Shared path-safety guards (used by MCP server AND CLI runner so both enforce the same policy):
- Document extension allowlist (blocks reading/writing config, credential, or key files)
- Subfolder-name sanitization (prevents traversal out of the output directory)
- Confinement check for paths referenced from generated Markdown
"""

from pathlib import Path
from typing import Optional

ALLOWED_DOC_EXTENSIONS = {".md", ".markdown", ".html", ".htm", ".xml", ".xhtml"}


def sanitize_subfolder_name(folder_name: Optional[str], default_name: str = "assets") -> str:
    """Ensure a subfolder name cannot traverse outside the parent output directory."""
    if not folder_name or not folder_name.strip():
        return default_name
    cleaned = folder_name.replace("\x00", "").replace("\\", "/").strip("/")
    safe_name = Path(cleaned).name
    if not safe_name or safe_name in (".", "..") or safe_name.startswith("."):
        return default_name
    return safe_name


def assert_not_sensitive_path(file_path: Path) -> None:
    """Strictly allow only non-hidden Markdown, HTML, or XML document files."""
    name_lower = file_path.name.lower()
    suffix_lower = file_path.suffix.lower()
    if name_lower.startswith(".") or suffix_lower not in ALLOWED_DOC_EXTENSIONS:
        raise PermissionError(
            f"Access to file '{file_path.name}' is restricted. "
            f"Only document files ({', '.join(sorted(ALLOWED_DOC_EXTENSIONS))}) are permitted."
        )


def is_within_directory(base_dir: Path, candidate: Path) -> bool:
    """True if candidate resolves inside base_dir."""
    try:
        candidate.resolve().relative_to(base_dir.resolve())
        return True
    except (ValueError, OSError):
        return False
