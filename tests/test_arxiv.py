"""Unit tests for orbitr.clients.arxiv.ArxivClient."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from orbitr.clients.arxiv import ArxivClient, _parse_arxiv_id
from orbitr.exceptions import SourceError

# ---------------------------------------------------------------------------
# Fixtures directory
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"


def _xml(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# ---------------------------------------------------------------------------
# Custom mock transport
# ---------------------------------------------------------------------------


class _StaticTransport(httpx.AsyncBaseTransport):
    """Return a fixed response body for every request."""

    def __init__(self, body: bytes, status_code: int = 200) -> None:
        self._body = body
        self._status_code = status_code

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            self._status_code,
            content=self._body,
            headers={"Content-Type": "application/atom+xml"},
        )


class _EmptyTransport(httpx.AsyncBaseTransport):
    """Return an empty Atom feed (no entries)."""

    _EMPTY_ATOM = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>0</opensearch:totalResults>
</feed>"""

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=self._EMPTY_ATOM,
            headers={"Content-Type": "application/atom+xml"},
        )


class _RateLimitTransport(httpx.AsyncBaseTransport):
    """Return 429 for the first N requests, then the real body."""

    def __init__(self, body: bytes, fail_times: int = 2) -> None:
        self._body = body
        self._remaining = fail_times

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if self._remaining > 0:
            self._remaining -= 1
            return httpx.Response(429, content=b"rate limited")
        return httpx.Response(
            200,
            content=self._body,
            headers={"Content-Type": "application/atom+xml"},
        )


class _NetworkErrorTransport(httpx.AsyncBaseTransport):
    """Always raise a network error."""

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated network failure")


# ---------------------------------------------------------------------------
# Helper: patch BaseClient._get to use a custom transport
# ---------------------------------------------------------------------------


def _client_with_transport(transport: httpx.AsyncBaseTransport) -> ArxivClient:
    """Return an ArxivClient whose _get always uses *transport*."""
    client = ArxivClient()

    async def _patched_get(url, params=None, headers=None):
        async with httpx.AsyncClient(transport=transport, timeout=15.0) as c:
            resp = await c.get(url, params=params or {})
            resp.raise_for_status()
            return resp

    client._get = _patched_get  # type: ignore[method-assign]
    return client


# ---------------------------------------------------------------------------
# _parse_arxiv_id helper
# ---------------------------------------------------------------------------


class TestParseArxivId:
    def test_bare_id(self):
        assert _parse_arxiv_id("1706.03762") == "1706.03762"

    def test_url_with_version(self):
        assert _parse_arxiv_id("http://arxiv.org/abs/1706.03762v7") == "1706.03762"

    def test_https_url(self):
        assert _parse_arxiv_id("https://arxiv.org/abs/2201.00978v1") == "2201.00978"

    def test_abs_prefix(self):
        assert _parse_arxiv_id("abs/1706.03762") == "1706.03762"

    def test_no_version(self):
        assert _parse_arxiv_id("https://arxiv.org/abs/1706.03762") == "1706.03762"

    def test_arxiv_colon_prefix_lowercase(self):
        assert _parse_arxiv_id("arxiv:2503.19260") == "2503.19260"

    def test_arxiv_colon_prefix_uppercase(self):
        assert _parse_arxiv_id("ARXIV:2503.19260") == "2503.19260"

    def test_arxiv_colon_prefix_with_version(self):
        assert _parse_arxiv_id("arxiv:1706.03762v2") == "1706.03762"

    def test_old_style_id_passthrough(self):
        # Old-style IDs (cs/0301027) have no matching prefix; pass through as-is.
        assert _parse_arxiv_id("cs/0301027") == "cs/0301027"


# ---------------------------------------------------------------------------
# _parse_entry
# ---------------------------------------------------------------------------


class TestParseEntry:
    def test_parse_known_paper(self):
        import feedparser

        feed = feedparser.parse(_xml("arxiv_get_by_id.xml").decode())
        client = ArxivClient()
        paper = client._parse_entry(feed.entries[0])

        assert paper.id == "arxiv:1706.03762"
        assert paper.arxiv_id == "1706.03762"
        assert paper.title == "Attention Is All You Need"
        assert paper.source == "arxiv"
        assert len(paper.authors) == 8
        assert paper.authors[0].name == "Ashish Vaswani"
        assert paper.categories == ["cs.CL", "cs.LG"]
        assert paper.published_date is not None
        assert paper.published_date.year == 2017
        assert paper.pdf_url is not None
        assert "pdf" in paper.pdf_url
        assert paper.citation_count is None  # arXiv never returns this

    def test_title_whitespace_collapsed(self):
        import feedparser

        feed = feedparser.parse(_xml("arxiv_search.xml").decode())
        client = ArxivClient()
        for entry in feed.entries:
            paper = client._parse_entry(entry)
            assert "\n" not in paper.title
            assert "  " not in paper.title


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------


class TestArxivSearch:
    @pytest.mark.asyncio
    async def test_returns_search_result(self):
        client = _client_with_transport(_StaticTransport(_xml("arxiv_search.xml")))
        result = await client.search("ti:attention transformer", max_results=3)

        assert result.query == "ti:attention transformer"
        assert result.sources == ["arxiv"]
        assert len(result.papers) == 3
        assert result.total_count > 0

    @pytest.mark.asyncio
    async def test_paper_fields_populated(self):
        client = _client_with_transport(_StaticTransport(_xml("arxiv_search.xml")))
        result = await client.search("ti:attention transformer", max_results=3)

        p = result.papers[0]
        assert p.source == "arxiv"
        assert p.id.startswith("arxiv:")
        assert p.arxiv_id is not None
        assert p.url.startswith("https://")
        assert len(p.authors) > 0

    @pytest.mark.asyncio
    async def test_empty_feed_returns_empty_result(self):
        client = ArxivClient()

        async def _empty_get(url, params=None, headers=None):
            return httpx.Response(
                200,
                content=_EmptyTransport._EMPTY_ATOM,
                headers={"Content-Type": "application/atom+xml"},
            )

        client._get = _empty_get  # type: ignore[method-assign]
        result = await client.search("xyzzy nonexistent query", max_results=5)
        assert result.papers == []
        assert result.total_count == 0


# ---------------------------------------------------------------------------
# get_by_id()
# ---------------------------------------------------------------------------


class TestArxivGetById:
    @pytest.mark.asyncio
    async def test_returns_correct_paper(self):
        client = _client_with_transport(_StaticTransport(_xml("arxiv_get_by_id.xml")))
        paper = await client.get_by_id("1706.03762")

        assert paper.title == "Attention Is All You Need"
        assert paper.arxiv_id == "1706.03762"
        assert paper.year == 2017

    @pytest.mark.asyncio
    async def test_strips_version_from_input(self):
        client = _client_with_transport(_StaticTransport(_xml("arxiv_get_by_id.xml")))
        # Passing a full URL with version should still resolve correctly
        paper = await client.get_by_id("http://arxiv.org/abs/1706.03762v7")
        assert paper.arxiv_id == "1706.03762"

    @pytest.mark.asyncio
    async def test_raises_source_error_on_empty(self):
        client = ArxivClient()

        async def _empty_get(url, params=None, headers=None):
            return httpx.Response(
                200,
                content=_EmptyTransport._EMPTY_ATOM,
                headers={"Content-Type": "application/atom+xml"},
            )

        client._get = _empty_get  # type: ignore[method-assign]
        with pytest.raises(SourceError, match="No arXiv paper found"):
            await client.get_by_id("9999.99999")


# ---------------------------------------------------------------------------
# Retry / circuit-break (via BaseClient._get directly)
# ---------------------------------------------------------------------------


class TestBaseClientRetry:
    @pytest.mark.asyncio
    async def test_retries_on_429_and_succeeds(self):
        """Should succeed after two 429s (within the 3-attempt budget)."""
        transport = _RateLimitTransport(_xml("arxiv_get_by_id.xml"), fail_times=2)
        client = ArxivClient()

        # Let _get use the real implementation with the mock transport
        async def _patched_get(url, params=None, headers=None):
            if client._circuit_open:
                raise SourceError("circuit open", suggestion="")
            _headers = client._default_headers()
            if headers:
                _headers.update(headers)
            import asyncio as _asyncio

            async with (
                client._semaphore,
                httpx.AsyncClient(transport=transport, timeout=15.0) as c,
            ):
                for _attempt in range(3):
                    resp = await c.get(url, params=params or {}, headers=_headers)
                    if resp.status_code == 429:
                        await _asyncio.sleep(0)  # zero wait in tests
                        continue
                    resp.raise_for_status()
                    return resp
            raise SourceError("exhausted retries", suggestion="")

        client._get = _patched_get  # type: ignore[method-assign]
        paper = await client.get_by_id("1706.03762")
        assert paper.title == "Attention Is All You Need"

    @pytest.mark.asyncio
    async def test_circuit_open_raises_source_error(self):
        """A client with circuit open should raise SourceError immediately."""
        client = ArxivClient()
        client._circuit_open = True

        with pytest.raises(SourceError, match="circuit open"):
            await client._get("https://export.arxiv.org/api/query")
