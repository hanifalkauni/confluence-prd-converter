"""
Runtime settings loader for confluence-prd-converter.config.json.

Security notes:
- Credentials (confluence.url / confluence.pat) are intentionally NEVER read from this file;
  they come only from environment variables (CONFLUENCE_URL / CONFLUENCE_PAT) or mcp_config.json.
- Placeholder values shipped in the example config (e.g. 'yourcompany.com', '${VAR}') are ignored.
- Related-pages discovery is opt-in per request and cannot be enabled globally from config.

Search order: $CONFLUENCE_PRD_CONFIG, ./confluence-prd-converter.config.json, project root.
"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

CONFIG_FILENAME = "confluence-prd-converter.config.json"

DEFAULTS: Dict[str, Dict[str, Any]] = {
    "confluence": {"verify_ssl": True, "timeout_seconds": 30.0},
    "output": {"assets_folder": "assets", "download_images": True, "include_comments": True},
    "formatting": {"table_mode": "table", "jira_base_url": ""},
    "related": {"default_limit": 10, "default_relation_types": ["parent", "children", "linked", "backlinks", "labels"]},
}

_VALID_RELATIONS = {"parent", "children", "linked", "backlinks", "labels", "similar"}


def _candidates() -> List[Path]:
    paths: List[Path] = []
    env_path = os.environ.get("CONFLUENCE_PRD_CONFIG")
    if env_path:
        paths.append(Path(env_path))
    paths.append(Path.cwd() / CONFIG_FILENAME)
    paths.append(Path(__file__).resolve().parent.parent / CONFIG_FILENAME)
    return paths


def _is_placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return "yourcompany.com" in value or "${" in value


@lru_cache(maxsize=1)
def load_config() -> Dict[str, Dict[str, Any]]:
    """Load config merged over defaults. Invalid or missing files fall back to defaults silently."""
    merged = {k: dict(v) for k, v in DEFAULTS.items()}
    for candidate in _candidates():
        try:
            if not candidate.is_file():
                continue
            with open(candidate, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                continue
            for section, defaults in DEFAULTS.items():
                user_section = data.get(section)
                if not isinstance(user_section, dict):
                    continue
                for key, default in defaults.items():
                    val = user_section.get(key)
                    if val is None or _is_placeholder(val):
                        continue
                    if isinstance(default, bool) and not isinstance(val, bool):
                        continue
                    if isinstance(default, float) and (isinstance(val, bool) or not isinstance(val, (int, float))):
                        continue
                    if isinstance(default, int) and not isinstance(default, bool) and (isinstance(val, bool) or not isinstance(val, int)):
                        continue
                    if isinstance(default, str) and not isinstance(val, str):
                        continue
                    if isinstance(default, list) and not isinstance(val, list):
                        continue
                    merged[section][key] = val
            break
        except Exception:
            continue
    return merged


def reload_config() -> None:
    load_config.cache_clear()


def get_verify_ssl() -> bool:
    return bool(load_config()["confluence"]["verify_ssl"])


def get_timeout() -> float:
    try:
        return max(1.0, min(float(load_config()["confluence"]["timeout_seconds"]), 300.0))
    except (TypeError, ValueError):
        return 30.0


def get_table_mode() -> str:
    mode = str(load_config()["formatting"]["table_mode"]).lower()
    return mode if mode in ("table", "text") else "table"


def get_jira_base_url() -> str:
    """Return validated http(s) Jira base URL without trailing slash, or '' if unset/invalid."""
    url = str(load_config()["formatting"]["jira_base_url"] or "").strip().rstrip("/")
    return url if url.lower().startswith(("http://", "https://")) else ""


def jira_issue_url(key: str) -> str:
    base = get_jira_base_url() or "https://jira.atlassian.com"
    return f"{base}/browse/{key}"


def get_related_defaults() -> Dict[str, Any]:
    rel = load_config()["related"]
    types = [t for t in rel["default_relation_types"] if t in _VALID_RELATIONS] or DEFAULTS["related"]["default_relation_types"]
    try:
        limit = max(1, min(int(rel["default_limit"]), 50))
    except (TypeError, ValueError):
        limit = 10
    return {"limit": limit, "relation_types": types}
