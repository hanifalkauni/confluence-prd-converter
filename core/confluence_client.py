"""
Confluence REST API Client & Live Fetcher:
- Zero in-band credential exposure (resolved strictly from env / local config)
- Strict Same-Origin Authorization Guard (prevents cross-origin token exfiltration)
- SSRF protection against cloud metadata & loopback probing
- Attachment filename sanitization & directory confinement (prevents CWE-22 path traversal)
- Automatic secret redaction in error messages
"""

import os
import re
import json
import ipaddress
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import httpx
from .clean import is_system_icon
from .settings import get_verify_ssl, get_timeout

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}


def sanitize_secret(text: str, pat: Optional[str] = None) -> str:
    """Redact Personal Access Tokens, Bearer/Basic headers, and URL credentials from text."""
    if not text:
        return ""
    sanitized = str(text)
    if pat and len(pat.strip()) >= 4:
        sanitized = sanitized.replace(pat.strip(), "[REDACTED_PAT]")
    env_pat = os.environ.get("CONFLUENCE_PAT", "").strip()
    if env_pat and len(env_pat) >= 4:
        sanitized = sanitized.replace(env_pat, "[REDACTED_PAT]")
    sanitized = re.sub(r"(?i)(Bearer\s+)[^\s\"'<>]+", r"\1[REDACTED]", sanitized)
    sanitized = re.sub(r"(?i)(Basic\s+)[A-Za-z0-9+/=]+", r"\1[REDACTED]", sanitized)
    sanitized = re.sub(r"(https?://)([^/\s:@]+:[^/\s@]+)(@)", r"\1[REDACTED]\3", sanitized)
    return sanitized


def _extract_origin(url: str) -> Tuple[str, str, Optional[int]]:
    """Return normalized (scheme, hostname, port) tuple for origin comparison."""
    parsed = urllib.parse.urlparse(url.strip())
    scheme = (parsed.scheme or "").lower()
    hostname = (parsed.hostname or "").lower()
    port = parsed.port
    if port is None:
        if scheme == "https":
            port = 443
        elif scheme == "http":
            port = 80
    return scheme, hostname, port


def is_same_origin(url_a: str, url_b: str) -> bool:
    """Check if two URLs share the exact same scheme, hostname, and port."""
    if not url_a or not url_b:
        return False
    orig_a = _extract_origin(url_a)
    orig_b = _extract_origin(url_b)
    return bool(orig_a[0] and orig_a[1] and orig_a == orig_b)


def validate_safe_base_url(url: str) -> str:
    """Validate Confluence base URL against SSRF metadata targets and invalid schemes."""
    if not url or not url.strip():
        raise ValueError("Confluence Base URL cannot be empty.")
    cleaned = url.strip().rstrip("/")
    parsed = urllib.parse.urlparse(cleaned)
    scheme = (parsed.scheme or "").lower()
    hostname = (parsed.hostname or "").lower()

    if scheme not in ("https", "http"):
        raise ValueError(f"Invalid Confluence URL scheme '{scheme}'. Only 'https' or 'http' is allowed.")
    if not hostname:
        raise ValueError("Confluence Base URL must include a valid hostname.")

    # Block cloud metadata domains
    if hostname.endswith(".internal") or hostname.endswith(".goog"):
        raise PermissionError(f"Blocked potential SSRF metadata host: '{hostname}'.")

    # Block link-local (cloud IMDS), unspecified, multicast, and reserved IP ranges
    try:
        ip_obj = ipaddress.ip_address(hostname.strip("[]"))
        if ip_obj.is_link_local or ip_obj.is_unspecified or ip_obj.is_multicast or ip_obj.is_reserved:
            raise PermissionError(f"Blocked potential SSRF IP address: '{hostname}'.")
    except ValueError:
        pass

    return cleaned


def sanitize_attachment_filename(filename: str, target_dir: Path) -> Optional[Path]:
    """
    Sanitize attachment filename to prevent Path Traversal (CWE-22), hidden file overwrites,
    and non-image file writes. Returns resolved destination Path strictly confined inside target_dir.
    """
    if not filename:
        return None
    raw_name = filename.replace("\x00", "").replace("\\", "/").split("/")[-1].strip()
    safe_name = Path(raw_name).name
    if not safe_name or safe_name in (".", "..") or safe_name.startswith("."):
        return None
    safe_name = re.sub(r'[<>:"|?*]', "_", safe_name)
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return None
    resolved_dir = target_dir.resolve()
    dest_file = (resolved_dir / safe_name).resolve()
    try:
        dest_file.relative_to(resolved_dir)
    except ValueError:
        return None
    if dest_file.parent != resolved_dir:
        return None
    return dest_file


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


def _discover_configured_credentials() -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve configured Confluence URL and PAT from environment variables
    or local mcp_config.json files.
    """
    url = os.environ.get("CONFLUENCE_URL")
    pat = os.environ.get("CONFLUENCE_PAT")

    if url and pat:
        return url.rstrip("/"), pat

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

                for s_key in ["confluence-prd-converter", "confluence", "atlassian-confluence"]:
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


def discover_confluence_credentials(
    explicit_url: Optional[str] = None,
    explicit_pat: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Discover Confluence URL and PAT safely:
    - Prevents Cross-Origin Fallback Auth Inheritance: if explicit_url is provided
      without explicit_pat, the fallback PAT from environment/config is ONLY inherited
      if explicit_url has the exact same origin as the configured CONFLUENCE_URL.
    """
    cfg_url, cfg_pat = _discover_configured_credentials()

    if explicit_url and explicit_pat:
        return explicit_url.rstrip("/"), explicit_pat

    if explicit_url and not explicit_pat:
        clean_explicit = explicit_url.rstrip("/")
        if cfg_url and is_same_origin(clean_explicit, cfg_url):
            return clean_explicit, cfg_pat
        # Do NOT attach configured PAT to an unverified cross-origin URL override
        return clean_explicit, None

    if not explicit_url and explicit_pat:
        return (cfg_url.rstrip("/") if cfg_url else None), explicit_pat

    return cfg_url, cfg_pat


class ConfluenceClient:
    """Client for Confluence Cloud / Server REST API with strict origin and SSRF guards."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        pat: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
        timeout: Optional[float] = None
    ):
        discovered_url, discovered_pat = discover_confluence_credentials(base_url, pat)
        raw_url = (discovered_url or "").rstrip("/")
        self.base_url = validate_safe_base_url(raw_url) if raw_url else ""
        self.pat = discovered_pat or ""
        self.verify_ssl = get_verify_ssl() if verify_ssl is None else verify_ssl
        self.timeout = get_timeout() if timeout is None else timeout

    def _get_headers(self, target_url: Optional[str] = None) -> Dict[str, str]:
        """
        Build HTTP request headers.
        Authorization Bearer token is strictly attached ONLY if target_url matches self.base_url origin.
        """
        headers = {
            "Accept": "application/json",
            "User-Agent": "Confluence-PRD-Converter/1.0.0"
        }
        if self.pat:
            if target_url is None or (self.base_url and is_same_origin(self.base_url, target_url)):
                headers["Authorization"] = f"Bearer {self.pat}"
        return headers

    def fetch_page(self, page_id_or_url: str) -> Dict[str, Any]:
        """Fetch Confluence page content (Storage format and View format) and metadata."""
        if not self.base_url:
            raise ValueError(
                "Confluence Base URL is not configured. Set CONFLUENCE_URL environment variable."
            )

        validate_safe_base_url(self.base_url)
        page_id = extract_page_id_from_url(page_id_or_url)
        endpoint = f"{self.base_url}/rest/api/content/{page_id}?expand=body.storage,body.view,version,space,metadata"

        try:
            with httpx.Client(
                verify=self.verify_ssl,
                timeout=self.timeout,
                follow_redirects=False
            ) as client:
                response = client.get(endpoint, headers=self._get_headers(endpoint))

                if response.status_code == 401:
                    raise PermissionError("Confluence API Authentication Failed (401). Check CONFLUENCE_PAT token.")
                elif response.status_code == 403:
                    raise PermissionError("Access to Confluence page forbidden (403).")
                elif response.status_code == 404:
                    raise FileNotFoundError(f"Confluence page with ID '{page_id}' not found (404).")
                elif response.status_code in (301, 302, 303, 307, 308):
                    raise PermissionError(
                        f"Confluence API returned unexpected redirect ({response.status_code}). Check CONFLUENCE_URL."
                    )

                response.raise_for_status()
                data = response.json()
        except Exception as e:
            if isinstance(e, (PermissionError, FileNotFoundError, ValueError)):
                raise type(e)(sanitize_secret(str(e), self.pat)) from None
            raise RuntimeError(sanitize_secret(str(e), self.pat)) from None

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
        }

    def fetch_attachments(self, page_id: str) -> List[Dict[str, Any]]:
        """Fetch list of attachments for a given page."""
        if not self.base_url:
            return []

        safe_page_id = extract_page_id_from_url(page_id)
        endpoint = f"{self.base_url}/rest/api/content/{safe_page_id}/child/attachment?limit=200"
        try:
            with httpx.Client(
                verify=self.verify_ssl,
                timeout=self.timeout,
                follow_redirects=False
            ) as client:
                response = client.get(endpoint, headers=self._get_headers(endpoint))
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
        Enforces path traversal confinement and same-origin credential protection.
        Returns list of downloaded file info dicts: [{'filename': ..., 'path': ..., 'size_bytes': ...}].
        """
        attachments = self.fetch_attachments(page_id)
        if not attachments:
            return []

        out_path = Path(target_dir).resolve()
        out_path.mkdir(parents=True, exist_ok=True)

        downloaded = []
        with httpx.Client(
            verify=self.verify_ssl,
            timeout=self.timeout,
            follow_redirects=False
        ) as client:
            for att in attachments:
                title = att.get("title", "")
                if not title or is_system_icon(title):
                    continue

                dest_file = sanitize_attachment_filename(title, out_path)
                if dest_file is None:
                    continue

                # Filter image extensions
                lower_title = dest_file.name.lower()
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

                # Block SSRF or cross-origin attachment exfiltration
                if not is_same_origin(self.base_url, full_download_url):
                    continue

                try:
                    res = client.get(full_download_url, headers=self._get_headers(full_download_url))
                    if res.status_code == 200:
                        with open(dest_file, "wb") as f:
                            f.write(res.content)
                        downloaded.append({
                            "filename": dest_file.name,
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

        safe_page_id = extract_page_id_from_url(page_id)
        endpoint = f"{self.base_url}/rest/api/content/{safe_page_id}/child/comment?expand=body.storage,body.view,history,version&limit=100"
        try:
            with httpx.Client(
                verify=self.verify_ssl,
                timeout=self.timeout,
                follow_redirects=False
            ) as client:
                response = client.get(endpoint, headers=self._get_headers(endpoint))
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

    # ------------------------------------------------------------------
    # Related pages discovery
    # ------------------------------------------------------------------
    def _get_json(self, path_or_query: str) -> Optional[Dict[str, Any]]:
        """GET a JSON payload from the configured Confluence base URL (same-origin only)."""
        if not self.base_url:
            raise ValueError(
                "Confluence Base URL is not configured. Set CONFLUENCE_URL environment variable."
            )
        endpoint = f"{self.base_url}{path_or_query}"
        try:
            with httpx.Client(
                verify=self.verify_ssl,
                timeout=self.timeout,
                follow_redirects=False
            ) as client:
                response = client.get(endpoint, headers=self._get_headers(endpoint))
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass
        return None

    def page_url(self, page_id: str) -> str:
        """Build a canonical viewpage URL for a page ID."""
        return f"{self.base_url}/pages/viewpage.action?pageId={page_id}"

    @staticmethod
    def _cql_escape(value: str) -> str:
        """Escape a value for safe embedding in a double-quoted CQL string (prevents CQL injection)."""
        cleaned = re.sub(r"[\x00-\x1f]", " ", str(value))
        return cleaned.replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def _clamp_limit(limit: Any, default: int = 10, maximum: int = 50) -> int:
        try:
            return max(1, min(int(limit), maximum))
        except (TypeError, ValueError):
            return default

    def _brief(self, item: Dict[str, Any], relation: str) -> Dict[str, Any]:
        raw_id = str(item.get("id", ""))
        pid = raw_id if raw_id.isdigit() else ""
        return {
            "relation": relation,
            "page_id": pid,
            "title": item.get("title", ""),
            "space_key": (item.get("space") or {}).get("key", ""),
            "url": self.page_url(pid) if pid else "",
        }

    def fetch_child_pages(self, page_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        pid = extract_page_id_from_url(page_id)
        data = self._get_json(f"/rest/api/content/{pid}/child/page?limit={self._clamp_limit(limit)}")
        return [self._brief(i, "child") for i in (data or {}).get("results", [])]

    def fetch_parent_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        pid = extract_page_id_from_url(page_id)
        data = self._get_json(f"/rest/api/content/{pid}?expand=ancestors")
        ancestors = (data or {}).get("ancestors", [])
        return self._brief(ancestors[-1], "parent") if ancestors else None

    def fetch_labels(self, page_id: str) -> List[str]:
        pid = extract_page_id_from_url(page_id)
        data = self._get_json(f"/rest/api/content/{pid}/label")
        return [r.get("name", "") for r in (data or {}).get("results", []) if r.get("name")]

    def search_cql(self, cql: str, limit: int = 10, relation: str = "search") -> List[Dict[str, Any]]:
        q = urllib.parse.quote(cql, safe="")
        data = self._get_json(f"/rest/api/content/search?cql={q}&limit={self._clamp_limit(limit)}&expand=space")
        return [self._brief(i, relation) for i in (data or {}).get("results", [])]

    def resolve_page_by_title(self, title: str, space_key: str = "") -> Optional[Dict[str, Any]]:
        q = f'title = "{self._cql_escape(title)}" AND type = page'
        if space_key:
            q += f' AND space = "{self._cql_escape(space_key)}"'
        res = self.search_cql(q, limit=1, relation="content_link")
        return res[0] if res else None

    def find_related_pages(
        self,
        page_id_or_url: str,
        relation_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Discover related pages. relation_types: parent, children, linked (outbound links),
        backlinks (inbound links), labels (shared labels), similar (title keyword match).
        """
        allowed = {"parent", "children", "linked", "backlinks", "labels", "similar"}
        types = (set(relation_types) & allowed) if relation_types else {"parent", "children", "linked", "backlinks", "labels"}
        limit = self._clamp_limit(limit)
        page = self.fetch_page(page_id_or_url)
        pid, space = page["page_id"], page.get("space_key", "")
        related: List[Dict[str, Any]] = []

        if "parent" in types:
            parent = self.fetch_parent_page(pid)
            if parent:
                related.append(parent)
        if "children" in types:
            related.extend(self.fetch_child_pages(pid, limit))
        if "linked" in types:
            seen = set()
            for ref in extract_internal_page_refs(page.get("storage_xml") or page.get("view_html") or "")[:limit * 3]:
                if ref.get("page_id"):
                    found = {"relation": "content_link", "page_id": ref["page_id"],
                             "title": ref.get("title", ""), "space_key": space,
                             "url": self.page_url(ref["page_id"])}
                else:
                    found = self.resolve_page_by_title(ref["title"], ref.get("space_key") or space)
                if found and found["page_id"] != pid and found["page_id"] not in seen:
                    seen.add(found["page_id"])
                    related.append(found)
                if len(seen) >= limit:
                    break
        if "backlinks" in types:
            related.extend(self.search_cql(f'link = "{pid}" AND type = page', limit, "backlink"))
        labels = self.fetch_labels(pid) if ("labels" in types) else []
        if labels:
            lab = ",".join('"' + self._cql_escape(l) + '"' for l in labels[:5])
            cql = f'label IN ({lab}) AND type = page AND id != "{pid}"'
            if space:
                cql += f' AND space = "{self._cql_escape(space)}"'
            related.extend(self.search_cql(cql, limit, "shared_label"))
        if "similar" in types:
            words = [w for w in re.findall(r"\w{4,}", page["title"])][:3]
            if words:
                cond = " OR ".join('title ~ "' + self._cql_escape(w) + '"' for w in words)
                cql = f'({cond}) AND type = page AND id != "{pid}"'
                if space:
                    cql += f' AND space = "{self._cql_escape(space)}"'
                related.extend(self.search_cql(cql, limit, "similar_title"))

        # De-duplicate by page_id, keeping the first (most specific) relation
        unique, ids = [], set()
        for r in related:
            if r["page_id"] and r["page_id"] not in ids:
                ids.add(r["page_id"])
                unique.append(r)
        return {
            "base_page": {"page_id": pid, "title": page["title"], "space_key": space,
                          "url": self.page_url(pid), "labels": labels},
            "related_pages": unique,
        }


def extract_internal_page_refs(content: str) -> List[Dict[str, str]]:
    """Extract Confluence page references (ac:link ri:page and pageId hrefs) from storage XML / HTML."""
    refs: List[Dict[str, str]] = []
    if not content:
        return refs
    for m in re.finditer(r'<ri:page\b([^>]*?)/?>', content):
        attrs = m.group(1)
        t = re.search(r'ri:content-title="([^"]*)"', attrs)
        s = re.search(r'ri:space-key="([^"]*)"', attrs)
        if t:
            refs.append({"title": t.group(1), "space_key": s.group(1) if s else ""})
    for m in re.finditer(r'href="[^"]*?pageId=(\d+)[^"]*"', content):
        refs.append({"page_id": m.group(1), "title": ""})
    return refs
