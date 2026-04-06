"""Semantic Scholar REST API client.

Rate limits (as of 2025):
  Without API key: ~1 request/second
  With API key:    ~10 requests/second

orbitr enforces these proactively via a per-request sleep so that normal
usage stays within budget without relying purely on reactive 429 backoff.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone

from orbitr.clients.base import BaseClient
from orbitr.core.models import Author, Paper, SearchResult
from orbitr.exceptions import SourceError

_PAPER_FIELDS = (
    "paperId,title,authors,abstract,year,publicationDate,"
    "venue,externalIds,citationCount,url,openAccessPdf"
)
_AUTHOR_FIELDS = "authorId,name,affiliations"


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse an ISO date string (YYYY-MM-DD) into an aware UTC datetime."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# Minimum seconds between requests for each tier.
_SS_DELAY_NO_KEY = 1.1  # ~1 req/s without an API key (conservative)
_SS_DELAY_WITH_KEY = 0.12  # ~8 req/s with an API key (safely under 10/s)


class SemanticScholarClient(BaseClient):
    """Client for the Semantic Scholar Graph API v1."""

    # One concurrent request at a time so the per-request delay is
    # effective as an inter-request delay even under asyncio.gather.
    _semaphore_limit = 1
    _BASE_URL = "https://api.semanticscholar.org/graph/v1"
    _REC_URL = "https://api.semanticscholar.org/recommendations/v1"

    @property
    def _request_delay(self) -> float:
        """Proactive delay before each request to stay within SS rate limits.

        Returns ``_SS_DELAY_WITH_KEY`` when an API key is configured,
        ``_SS_DELAY_NO_KEY`` otherwise.
        """
        return _SS_DELAY_WITH_KEY if self.api_key else _SS_DELAY_NO_KEY

    def _default_headers(self) -> dict[str, str]:
        headers = super()._default_headers()
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    async def search(self, query: str, max_results: int = 10, **kwargs) -> SearchResult:
        """Search Semantic Scholar for papers matching a query.

        Args:
            query: Keyword search string.
            max_results: Maximum results to return.
            **kwargs: Unused; reserved for future filters.

        Returns:
            SearchResult with matched papers.
        """
        params = {
            "query": query,
            "limit": min(max_results, 100),  # API cap per request
            "fields": _PAPER_FIELDS,
        }
        resp = await self._get(f"{self._BASE_URL}/paper/search", params=params)
        data = resp.json()

        papers = [self._parse_paper(p) for p in data.get("data", [])]
        total = data.get("total") or len(papers)

        return SearchResult(
            papers=papers,
            total_count=total,
            query=query,
            sources=["semantic_scholar"],
        )

    async def get_by_id(self, paper_id: str) -> Paper:
        """Fetch a paper by Semantic Scholar ID, DOI, or arXiv ID.

        Accepts prefixes: "DOI:", "ARXIV:", or bare Semantic Scholar paper ID.

        Args:
            paper_id: Paper identifier with optional prefix.

        Returns:
            Paper with Semantic Scholar metadata.

        Raises:
            SourceError: If the paper is not found.
        """
        resp = await self._get(
            f"{self._BASE_URL}/paper/{paper_id}",
            params={"fields": _PAPER_FIELDS},
        )
        data = resp.json()

        if "error" in data or not data.get("paperId"):
            raise SourceError(
                f"No Semantic Scholar paper found for ID '{paper_id}'.",
                suggestion="Verify the ID and try with an ARXIV: or DOI: prefix.",
            )
        return self._parse_paper(data)

    async def get_citations(self, paper_id: str, limit: int = 100) -> list[Paper]:
        """Retrieve papers that cite a given paper.

        Args:
            paper_id: Semantic Scholar paper ID.
            limit: Maximum number of citing papers.

        Returns:
            List of citing Paper instances.
        """
        resp = await self._get(
            f"{self._BASE_URL}/paper/{paper_id}/citations",
            params={
                "fields": _PAPER_FIELDS,
                "limit": min(limit, 1000),
            },
        )
        data = resp.json()
        return [
            self._parse_paper(item["citingPaper"])
            for item in data.get("data", [])
            if item.get("citingPaper", {}).get("paperId")
        ]

    async def get_recommendations(self, paper_id: str, limit: int = 10) -> list[Paper]:
        """Retrieve recommended papers from the Recommendations API.

        Args:
            paper_id: Seed Semantic Scholar paper ID.
            limit: Number of recommendations.

        Returns:
            List of recommended Paper instances.
        """
        resp = await self._get(
            f"{self._REC_URL}/papers/forpaper/{paper_id}",
            params={
                "fields": _PAPER_FIELDS,
                "limit": min(limit, 500),
            },
        )
        data = resp.json()
        return [
            self._parse_paper(p)
            for p in data.get("recommendedPapers", [])
            if p.get("paperId")
        ]

    async def search_authors(self, name: str, limit: int = 10) -> list[Paper]:
        """Search for an author by name and return their papers.

        Uses the first matching result from the /author/search endpoint,
        then fetches that author's full paper list.

        Args:
            name: Author name query string.
            limit: Maximum number of papers to return.

        Returns:
            List of Paper instances from the best-matching author.

        Raises:
            SourceError: If no author is found or the API returns an error.
        """
        # Step 1: find the author
        resp = await self._get(
            f"{self._BASE_URL}/author/search",
            params={"query": name, "limit": 1, "fields": "authorId,name"},
        )
        data = resp.json()
        authors = data.get("data", [])
        if not authors or not authors[0].get("authorId"):
            raise SourceError(
                f"No author found for '{name}'.",
                suggestion="Check the spelling or try a surname only.",
            )

        author_id = authors[0]["authorId"]

        # Step 2: fetch their papers
        resp2 = await self._get(
            f"{self._BASE_URL}/author/{author_id}/papers",
            params={"fields": _PAPER_FIELDS, "limit": min(limit, 1000)},
        )
        data2 = resp2.json()
        papers = [
            self._parse_paper(p) for p in data2.get("data", []) if p.get("paperId")
        ]
        return papers[:limit]

    def _parse_paper(self, data: dict) -> Paper:
        """Parse a Semantic Scholar API paper dict into a Paper model.

        Args:
            data: Raw API response dict for a single paper.

        Returns:
            Paper instance.
        """
        paper_id = data.get("paperId", "")
        external = data.get("externalIds") or {}

        authors = [
            Author(
                name=a.get("name", ""),
                affiliation=next(iter(a.get("affiliations") or []), None),
                author_id=a.get("authorId"),
            )
            for a in data.get("authors") or []
            if a.get("name")
        ]

        pdf_info = data.get("openAccessPdf") or {}
        pdf_url: str | None = pdf_info.get("url") or None

        published_date = _parse_date(data.get("publicationDate"))
        # Fall back to year-only date if publicationDate is absent
        if published_date is None and data.get("year"):
            with contextlib.suppress(ValueError, TypeError):
                published_date = datetime(int(data["year"]), 1, 1, tzinfo=timezone.utc)

        return Paper(
            id=f"ss:{paper_id}",
            title=data.get("title") or "",
            authors=authors,
            abstract=data.get("abstract"),
            published_date=published_date,
            updated_date=None,  # SS API does not expose an update timestamp
            url=data.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}",
            pdf_url=pdf_url,
            doi=external.get("DOI"),
            arxiv_id=external.get("ArXiv"),
            venue=data.get("venue") or None,
            categories=[],  # SS does not expose subject categories in search results
            citation_count=data.get("citationCount"),
            source="semantic_scholar",
        )
