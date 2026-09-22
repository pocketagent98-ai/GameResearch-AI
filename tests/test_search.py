"""Search-layer tests: parsing, SSRF guard, graceful degradation."""

import pytest

from gameres.search import (
    CannedSearch,
    DuckDuckGoSearch,
    SearchHit,
    UnsafeUrlError,
    assert_safe_url,
    parse_ddg_lite,
)

LITE_HTML = """
<table>
<tr><td class="result-snippet">Official site of Temple Run by Imangi Studios.</td></tr>
<tr>
  <td><a rel="nofollow" class="result-link" href="https://www.imangistudios.com/">Imangi Studios</a></td>
  <td class="result-snippet">Creators of Temple Run.</td>
</tr>
<tr>
  <td><a rel="nofollow" class="result-link" href="http://192.168.0.1/admin">Bad internal link</a></td>
  <td class="result-snippet">private panel</td>
</tr>
</table>
"""


def test_parse_ddg_lite_extracts_results():
    hits = parse_ddg_lite(LITE_HTML)
    urls = [h.url for h in hits]
    assert "https://www.imangistudios.com/" in urls
    assert any(h.snippet for h in hits)


def test_parse_ddg_lite_dedupes():
    html = LITE_HTML + LITE_HTML
    hits = parse_ddg_lite(html)
    urls = [h.url for h in hits]
    assert len(urls) == len(set(urls))


def test_assert_safe_url_blocks_private_and_internal():
    for url in (
        "http://127.0.0.1/x",
        "http://192.168.0.1/admin",
        "http://localhost/x",
        "http://169.254.169.254/meta",
        "http://db.internal/x",
        "file:///etc/passwd",
        "https://example.com:22/",
    ):
        with pytest.raises(UnsafeUrlError):
            assert_safe_url(url)


def test_assert_safe_url_allows_public_https():
    assert_safe_url("https://www.imangistudios.com/")
    assert_safe_url("http://example.com/page")


def test_canned_search_substring_match():
    s = CannedSearch({"temple run": [SearchHit("TR wiki", "https://example.com/tr")]})
    assert s.search("Temple Run 2 developer") == [SearchHit("TR wiki", "https://example.com/tr")]
    assert s.search("unrelated") == []


def test_ddg_search_never_raises_on_network_failure():
    from unittest.mock import patch

    s = DuckDuckGoSearch(timeout=0.001)
    with patch("urllib.request.urlopen", side_effect=OSError("down")):
        assert s.search("anything") == []
    assert s.last_error is not None
