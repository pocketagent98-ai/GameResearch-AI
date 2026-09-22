"""Search providers for the research pipeline.

- ``DuckDuckGoSearch``: real, best-effort web search via DuckDuckGo's
  HTML endpoints (no API key). Failures degrade gracefully — the pipeline
  continues and marks affected findings [UNVERIFIED].
- ``CannedSearch``: deterministic results for offline runs and tests.

Every URL is checked with a minimal SSRF guard before any fetch.
"""

from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class UnsafeUrlError(ValueError):
    pass


def assert_safe_url(url: str) -> None:
    """Minimal SSRF guard for search-result URLs: http/https only, no
    private/loopback hosts, no odd ports."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError(f"scheme not allowed: {parsed.scheme!r}")
    host = (parsed.hostname or "").lower().strip(".")
    if not host:
        raise UnsafeUrlError("no host")
    if host in ("localhost", "metadata.google.internal") or host.endswith((".local", ".internal")):
        raise UnsafeUrlError(f"forbidden host: {host}")
    bad = ("127.", "10.", "192.168.", "169.254.", "0.0.0.0", "::1", "[::1]")
    if any(host.startswith(b) or host == b for b in bad):
        raise UnsafeUrlError(f"forbidden address: {host}")
    if parsed.port is not None and parsed.port not in (80, 443):
        raise UnsafeUrlError(f"port not allowed: {parsed.port}")


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str = ""


class SearchProvider(Protocol):
    def search(self, query: str, *, limit: int = 5) -> List[SearchHit]: ...


_RESULT_RE = re.compile(
    r'<a[^>]+class="result-link"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
    r'.*?<td[^>]*class="result-snippet"[^>]*>(.*?)</td>',
    re.DOTALL,
)
_HREF_RE = re.compile(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return html.unescape(_TAG_RE.sub("", text)).strip()


def parse_ddg_lite(html_text: str) -> List[SearchHit]:
    """Parse DuckDuckGo HTML results (lite and standard layouts)."""
    hits: List[SearchHit] = []
    for m in _RESULT_RE.finditer(html_text):
        url, title, snippet = m.group(1), _clean(m.group(2)), _clean(m.group(3))
        if url.startswith("http"):
            hits.append(SearchHit(title=title, url=url, snippet=snippet))
    if not hits:
        for m in _HREF_RE.finditer(html_text):
            url, title = m.group(1), _clean(m.group(2))
            if url.startswith("http") and title and "duckduckgo.com" not in url:
                hits.append(SearchHit(title=title, url=url))
    # de-dup by url
    seen: set = set()
    out = []
    for h in hits:
        if h.url not in seen:
            seen.add(h.url)
            out.append(h)
    return out


class DuckDuckGoSearch:
    """Best-effort, keyless web search. Never raises: on failure it returns
    [] and records the error in ``last_error`` so callers can degrade."""

    def __init__(self, *, timeout: float = 15.0) -> None:
        self.timeout = timeout
        self.last_error: Optional[str] = None

    def _get(self, url: str) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return resp.read().decode("utf-8", "replace")

    def search(self, query: str, *, limit: int = 5) -> List[SearchHit]:
        self.last_error = None
        try:
            page = self._get(
                "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
            )
        except Exception as exc:
            self.last_error = f"search failed: {exc}"
            return []
        hits = parse_ddg_lite(page)
        safe_hits: List[SearchHit] = []
        for h in hits:
            try:
                assert_safe_url(h.url)
                safe_hits.append(h)
            except UnsafeUrlError:
                continue
        return safe_hits[:limit]


class CannedSearch:
    """Deterministic search for offline runs: substring-matched canned hits."""

    def __init__(self, index: Optional[Dict[str, List[SearchHit]]] = None) -> None:
        self.index = {k.lower(): v for k, v in (index or {}).items()}
        self.queries: List[str] = []

    def search(self, query: str, *, limit: int = 5) -> List[SearchHit]:
        self.queries.append(query)
        low = query.lower()
        for key, hits in self.index.items():
            if key in low:
                return hits[:limit]
        return []
