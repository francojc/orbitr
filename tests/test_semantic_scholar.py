"""Unit tests for lumen.clients.semantic_scholar.SemanticScholarClient."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from lumen.clients.semantic_scholar import SemanticScholarClient
from lumen.exceptions import SourceError

FIXTURES = Path(__file__).parent / "fixtures"


def _json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# ---------------------------------------------------------------------------
# Transport helpers (same pattern as test_arxiv.py)
# ---------------------------------------------------------------------------


class _JsonTransport(httpx.AsyncBaseTransport):
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self._status_code = status_code

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            self._status_code,
            json=self._payload,
        )


def _client_with_json(payload: dict) -> SemanticScholarClient:
    client = SemanticScholarClient()

    async def _patched_get(url, params=None, headers=None):
        async with httpx.AsyncClient(
            transport=_JsonTransport(payload), timeout=15.0
        ) as c:
            resp = await c.get(url, params=params or {})
            resp.raise_for_status()
            return resp

    client._get = _patched_get  # type: ignore[method-assign]
    return client


# ---------------------------------------------------------------------------
# _parse_paper
# ---------------------------------------------------------------------------


class TestParsePaper:
    def test_full_record(self):
        data = _json("ss_get_by_id.json")
        client = SemanticScholarClient()
        p = client._parse_paper(data)

        assert p.id == f"ss:{data['paperId']}"
        assert p.title == "Attention is All you Need"
        assert p.source == "semantic_scholar"
        assert p.arxiv_id == "1706.03762"
        assert p.citation_count == 171767
        assert len(p.authors) > 0
        assert p.url.startswith("https://")

    def test_year_fallback_when_no_publication_date(self):
        data = {
            "paperId": "abc",
            "title": "Test Paper",
            "authors": [],
            "year": 2019,
            "publicationDate": None,
            "venue": None,
            "externalIds": {},
            "citationCount": 0,
            "url": "https://example.com",
            "openAccessPdf": None,
            "abstract": None,
        }
        client = SemanticScholarClient()
        p = client._parse_paper(data)
        assert p.published_date is not None
        assert p.published_date.year == 2019

    def test_no_date_no_year_gives_none(self):
        data = {
            "paperId": "abc",
            "title": "Test",
            "authors": [],
            "year": None,
            "publicationDate": None,
            "venue": None,
            "externalIds": {},
            "citationCount": None,
            "url": None,
            "openAccessPdf": None,
            "abstract": None,
        }
        client = SemanticScholarClient()
        p = client._parse_paper(data)
        assert p.published_date is None

    def test_pdf_url_from_open_access(self):
        data = _json("ss_search.json")["data"][1]  # paper with openAccessPdf
        client = SemanticScholarClient()
        p = client._parse_paper(data)
        assert p.pdf_url is not None
        assert p.pdf_url.startswith("http")

    def test_pdf_url_none_when_absent(self):
        data = _json("ss_search.json")["data"][2]  # openAccessPdf: null
        client = SemanticScholarClient()
        p = client._parse_paper(data)
        assert p.pdf_url is None

    def test_doi_extracted(self):
        data = _json("ss_search.json")["data"][1]
        client = SemanticScholarClient()
        p = client._parse_paper(data)
        assert p.doi is not None

    def test_author_affiliation(self):
        data = {
            "paperId": "abc",
            "title": "Test",
            "authors": [
                {"authorId": "1", "name": "Alice Smith", "affiliations": ["MIT"]}
            ],
            "year": 2021,
            "publicationDate": "2021-05-01",
            "venue": None,
            "externalIds": {},
            "citationCount": None,
            "url": None,
            "openAccessPdf": None,
            "abstract": None,
        }
        client = SemanticScholarClient()
        p = client._parse_paper(data)
        assert p.authors[0].affiliation == "MIT"


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------


class TestSSSearch:
    @pytest.mark.asyncio
    async def test_returns_search_result(self):
        client = _client_with_json(_json("ss_search.json"))
        result = await client.search("attention transformer", max_results=3)

        assert result.query == "attention transformer"
        assert result.sources == ["semantic_scholar"]
        assert len(result.papers) == 3

    @pytest.mark.asyncio
    async def test_total_count(self):
        client = _client_with_json(_json("ss_search.json"))
        result = await client.search("attention transformer", max_results=3)
        assert result.total_count == 3991951

    @pytest.mark.asyncio
    async def test_empty_response(self):
        client = _client_with_json({"total": 0, "offset": 0, "next": None, "data": []})
        result = await client.search("nothing here", max_results=5)
        assert result.papers == []
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_api_key_injected_in_header(self):
        captured = {}

        class _CapturingTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(
                self, request: httpx.Request
            ) -> httpx.Response:
                captured["headers"] = dict(request.headers)
                return httpx.Response(200, json={"data": [], "total": 0})

        client = SemanticScholarClient(api_key="test-key-123")

        async def _patched_get(url, params=None, headers=None):
            h = client._default_headers()
            async with httpx.AsyncClient(
                transport=_CapturingTransport(), timeout=15.0
            ) as c:
                return await c.get(url, params=params or {}, headers=h)

        client._get = _patched_get  # type: ignore[method-assign]
        await client.search("test")
        assert captured["headers"].get("x-api-key") == "test-key-123"


# ---------------------------------------------------------------------------
# get_by_id()
# ---------------------------------------------------------------------------


class TestSSGetById:
    @pytest.mark.asyncio
    async def test_returns_paper(self):
        client = _client_with_json(_json("ss_get_by_id.json"))
        paper = await client.get_by_id("204e3073870fae3d05bcbc2f6a8e263d9b72e776")
        assert paper.title == "Attention is All you Need"
        assert paper.arxiv_id == "1706.03762"

    @pytest.mark.asyncio
    async def test_raises_on_error_response(self):
        client = _client_with_json({"error": "Paper not found"})
        with pytest.raises(SourceError, match="No Semantic Scholar paper found"):
            await client.get_by_id("bad-id")


# ---------------------------------------------------------------------------
# get_citations()
# ---------------------------------------------------------------------------


class TestSSGetCitations:
    @pytest.mark.asyncio
    async def test_returns_citing_papers(self):
        client = _client_with_json(_json("ss_citations.json"))
        papers = await client.get_citations("204e3073870fae3d05bcbc2f6a8e263d9b72e776")
        assert len(papers) == 3
        for p in papers:
            assert p.source == "semantic_scholar"


# ---------------------------------------------------------------------------
# get_recommendations()
# ---------------------------------------------------------------------------


class TestSSGetRecommendations:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        client = _client_with_json(_json("ss_recommendations.json"))
        papers = await client.get_recommendations(
            "204e3073870fae3d05bcbc2f6a8e263d9b72e776"
        )
        # fixture may be empty (API returned 0); just assert no crash and correct type
        assert isinstance(papers, list)
