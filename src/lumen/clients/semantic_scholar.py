"""Semantic Scholar REST API client.

Rate limits:
  Without API key: 100 req/5 min (conservative default)
  With API key:    100 req/min
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone

from lumen.clients.base import BaseClient
from lumen.core.models import Author, Paper, SearchResult
from lumen.exceptions import SourceError

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


class SemanticScholarClient(BaseClient):
    """Client for the Semantic Scholar Graph API v1."""

    _semaphore_limit = 5
    _BASE_URL = "https://api.semanticscholar.org/graph/v1"
    _REC_URL = "https://api.semanticscholar.org/recommendations/v1"

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
