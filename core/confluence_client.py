"""
Confluence REST API Client & Live Fetcher:
- Automatic token resolution (explicit -> env -> mcp_config.json fallback)
- Page ID extraction from various URL patterns
- Fetching page body (Storage XML and View HTML) + metadata
- Live image attachment downloading and local caching
"""

import os
import re
import json
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import httpx
from .clean import is_system_icon


def extract_page_id_from_url(page_id_or_url: str) -> str:
    """Extract numeric page ID from string, URL, or URI."""
    if not page_id_or_url:
        raise ValueError("page_id_or_url cannot be empty")

    page_str = str(page_id_or_url).strip()

    # If it's already purely numeric
    if page_str.isdigit():
        return page_str

    # Look for pageId=12345 in query parameters
    parsed = urllib.parse.urlparse(page_str)
    qs = urllib.parse.parse_qs(parsed.query)
    if "pageId" in qs and qs["pageId"]:
        return qs["pageId"][0]

    # Look for /pages/viewpage.action?pageId=12345
    match_qid = re.search(r"[?&]pageId=(\d+)", page_str, re.IGNORECASE)
    if match_qid:
        return match_qid.group(1)

    # Look for /rest/api/content/12345
    match_api = re.search(r"/rest/api/content/(\d+)", page_str)
    if match_api:
        return match_api.group(1)

    # Look for trailing digits at path end /pages/12345
    match_path = re.search(r"/pages(?:/viewpage\.action)?/(\d+)", page_str)
    if match_path:
        return match_path.group(1)

    # General regex for consecutive digits (minimum 6 digits typically used for confluence IDs)
    match_digits = re.search(r"\b(\d{6,14})\b", page_str)
    if match_digits:
        return match_digits.group(1)

    raise ValueError(f"Could not extract numeric Confluence Page ID from input: '{page_id_or_url}'")


def discover_confluence_credentials(
    explicit_url: Optional[str] = None,
    explicit_pat: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Discover Confluence URL and PAT from:
    1. Explicit parameters
    2. Environment variables (CONFLUENCE_URL, CONFLUENCE_PAT)
    3. Global mcp_config.json (~/.gemini/config/mcp_config.json or workspace mcp_config.json)
    """
    url = explicit_url or os.environ.get("CONFLUENCE_URL")
    pat = explicit_pat or os.environ.get("CONFLUENCE_PAT")

    if url and pat:
        return url.rstrip("/"), pat

    # Search common mcp_config.json locations
    config_candidates = [
        Path.home() / ".gemini" / "config" / "mcp_config.json",
        Path.home() / ".config" / "antigravity" / "mcp_config.json",
        Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
        Path.cwd() / "mcp_config.json",
        Path.cwd().parent / "mcp_config.json"
    ]

    for candidate in config_candidates:
        try:
            if candidate.exists():
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)
                servers = data.get("mcpServers", {})
                
                # Check confluence or confluence-prd-converter server env
                for s_key in ["confluence", "confluence-prd-converter", "atlassian-confluence"]:
                    if s_key in servers and "env" in servers[s_key]:
                        s_env = servers[s_key]["env"]
                        if not url and "CONFLUENCE_URL" in s_env:
                            url = s_env["CONFLUENCE_URL"]
                        if not pat and "CONFLUENCE_PAT" in s_env:
                            pat = s_env["CONFLUENCE_PAT"]

                if url and pat:
                    break
        except Exception:
            continue

    return (url.rstrip("/") if url else None), pat


class ConfluenceClient:
    """Client for Confluence Cloud / Server REST API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        pat: Optional[str] = None,
        verify_ssl: bool = True,
        timeout: float = 30.0
    ):
        discovered_url, discovered_pat = discover_confluence_credentials(base_url, pat)
        self.base_url = (discovered_url or "").rstrip("/")
        self.pat = discovered_pat or ""
        self.verify_ssl = verify_ssl
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "Confluence-PRD-Converter/1.0.0"
        }
        if self.pat:
            headers["Authorization"] = f"Bearer {self.pat}"
        return headers

    def fetch_page(self, page_id_or_url: str) -> Dict[str, Any]:
        """Fetch Confluence page content (Storage format and View format) and metadata."""
        if not self.base_url:
            raise ValueError(
                "Confluence Base URL is not configured. Set CONFLUENCE_URL environment variable or configure in mcp_config.json."
            )

        page_id = extract_page_id_from_url(page_id_or_url)
        endpoint = f"{self.base_url}/rest/api/content/{page_id}?expand=body.storage,body.view,version,space,metadata"

        with httpx.Client(verify=self.verify_ssl, timeout=self.timeout) as client:
            response = client.get(endpoint, headers=self._get_headers())
            
            if response.status_code == 401:
                raise PermissionError("Confluence API Authentication Failed (401). Check CONFLUENCE_PAT token.")
            elif response.status_code == 403:
                raise PermissionError("Access to Confluence page forbidden (403).")
            elif response.status_code == 404:
                raise FileNotFoundError(f"Confluence page with ID '{page_id}' not found (404).")
            
            response.raise_for_status()
            data = response.json()

        title = data.get("title", f"Confluence Page {page_id}")
        storage_xml = data.get("body", {}).get("storage", {}).get("value", "")
        view_html = data.get("body", {}).get("view", {}).get("value", "")
        space_key = data.get("space", {}).get("key", "")
        version_num = data.get("version", {}).get("number", 1)

        return {
            "page_id": page_id,
            "title": title,
            "space_key": space_key,
            "version": version_num,
            "storage_xml": storage_xml,
            "view_html": view_html,
            "raw_response": data
        }

    def fetch_attachments(self, page_id: str) -> List[Dict[str, Any]]:
        """Fetch list of attachments for a given page."""
        if not self.base_url:
            return []

        endpoint = f"{self.base_url}/rest/api/content/{page_id}/child/attachment?limit=200"
        try:
            with httpx.Client(verify=self.verify_ssl, timeout=self.timeout) as client:
                response = client.get(endpoint, headers=self._get_headers())
                if response.status_code == 200:
                    data = response.json()
                    return data.get("results", [])
        except Exception:
            pass
        return []

    def download_attachments(
        self,
        page_id: str,
        target_dir: str
    ) -> List[Dict[str, str]]:
        """
        Download image attachments from page to target local directory.
        Returns list of downloaded file info dicts: [{'filename': ..., 'path': ..., 'size': ...}].
        """
        attachments = self.fetch_attachments(page_id)
        if not attachments:
            return []

        out_path = Path(target_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        downloaded = []
        with httpx.Client(verify=self.verify_ssl, timeout=self.timeout) as client:
            for att in attachments:
                title = att.get("title", "")
                if not title or is_system_icon(title):
                    continue

                # Filter image extensions
                lower_title = title.lower()
                if not any(lower_title.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"]):
                    continue

                links = att.get("_links", {})
                download_url = links.get("download", "")
                if not download_url:
                    continue

                if download_url.startswith("/"):
                    full_download_url = f"{self.base_url}{download_url}"
                else:
                    full_download_url = download_url

                dest_file = out_path / title
                try:
                    res = client.get(full_download_url, headers=self._get_headers())
                    if res.status_code == 200:
                        with open(dest_file, "wb") as f:
                            f.write(res.content)
                        downloaded.append({
                            "filename": title,
                            "path": str(dest_file).replace("\\", "/"),
                            "size_bytes": len(res.content)
                        })
                except Exception:
                    continue

        return downloaded

    def fetch_comments(self, page_id: str) -> List[Dict[str, Any]]:
        """
        Fetch discussion comments for a given page.
        Returns list of comment dicts with author, timestamp, body storage/view content.
        """
        if not self.base_url:
            return []

        endpoint = f"{self.base_url}/rest/api/content/{page_id}/child/comment?expand=body.storage,body.view,history,version&limit=100"
        try:
            with httpx.Client(verify=self.verify_ssl, timeout=self.timeout) as client:
                response = client.get(endpoint, headers=self._get_headers())
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    parsed_comments = []
                    for item in results:
                        created_by = item.get("history", {}).get("createdBy", {})
                        author = created_by.get("displayName") or created_by.get("username")
                        if not author:
                            version_by = item.get("version", {}).get("by", {})
                            author = version_by.get("displayName") or version_by.get("username") or "Anonymous"

                        date_str = item.get("history", {}).get("createdDate") or item.get("version", {}).get("when", "")
                        body_storage = item.get("body", {}).get("storage", {}).get("value", "")
                        body_view = item.get("body", {}).get("view", {}).get("value", "")

                        parsed_comments.append({
                            "id": str(item.get("id", "")),
                            "author": author,
                            "date": date_str,
                            "body_storage": body_storage,
                            "body_view": body_view
                        })
                    return parsed_comments
        except Exception:
            pass
        return []
