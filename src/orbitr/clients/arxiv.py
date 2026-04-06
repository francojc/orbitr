"""arXiv API client — Atom feed via feedparser.

Rate limit: 3 requests/second (enforced by semaphore + sleep).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import feedparser

from orbitr.clients.base import BaseClient
from orbitr.core.models import Author, Paper, SearchResult
from orbitr.exceptions import SourceError

#: arXiv ID pattern — strips URL prefix, 'arxiv:' prefix, and version suffix.
_ARXIV_ID_RE = re.compile(
    r"(?:https?://arxiv\.org/abs/|abs/|arxiv:)?([^\s/]+?)(?:v\d+)?$", re.IGNORECASE
)


def _parse_arxiv_id(raw: str) -> str:
    """Extract a bare arXiv ID (e.g. '1706.03762') from a URL or plain string."""
    m = _ARXIV_ID_RE.match(raw.strip())
    return m.group(1) if m else raw.strip()


def _parse_dt(parsed_time: tuple | None) -> datetime | None:
    """Convert a feedparser time-tuple to an aware UTC datetime."""
    if parsed_time is None:
        return None
    return datetime(*parsed_time[:6], tzinfo=timezone.utc)


class ArxivClient(BaseClient):
    """Client for the arXiv Atom feed API."""

    _semaphore_limit = 3
    _BASE_URL = "https://export.arxiv.org/api/query"

    async def search(self, query: str, max_results: int = 10, **kwargs) -> SearchResult:
        """Search arXiv by keyword or field query.

        Args:
            query: arXiv search query string (supports field prefixes: ti:, au:, abs:).
            max_results: Maximum results to return.
            **kwargs: Unused; reserved for future filters.

        Returns:
            SearchResult with matched papers.
        """
        params = {
            "search_query": query,
            "max_results": max_results,
            "sortBy": "relevance",
        }
        resp = await self._get(self._BASE_URL, params=params)
        feed = feedparser.parse(resp.text)

        if feed.get("bozo") and not feed.get("entries"):
            raise SourceError(
                "arXiv returned a malformed Atom feed.",
                suggestion="Check your query syntax or try again later.",
            )

        total = int(feed.feed.get("opensearch_totalresults", 0))  # type: ignore[union-attr]
        papers = [self._parse_entry(e) for e in feed.entries]

        return SearchResult(
            papers=papers,
            total_count=total,
            query=query,
            sources=["arxiv"],
        )

    async def get_by_id(self, paper_id: str) -> Paper:
        """Fetch a paper by arXiv ID.

        Args:
            paper_id: arXiv ID (e.g. '1706.03762' or 'abs/1706.03762').

        Returns:
            Paper with arXiv metadata.

        Raises:
            SourceError: If no paper is found for the given ID.
        """
        arxiv_id = _parse_arxiv_id(paper_id)
        resp = await self._get(self._BASE_URL, params={"id_list": arxiv_id})
        feed = feedparser.parse(resp.text)

        if not feed.entries:
            raise SourceError(
                f"No arXiv paper found for ID '{arxiv_id}'.",
                suggestion="Verify the arXiv ID and try again.",
            )

        return self._parse_entry(feed.entries[0])

    def _parse_entry(self, entry: dict) -> Paper:
        """Parse a feedparser entry into a Paper model.

        Args:
            entry: Single feedparser entry dict.

        Returns:
            Paper instance.
        """
        raw_id = entry.get("id", "")
        arxiv_id = _parse_arxiv_id(raw_id)

        title = " ".join(entry.get("title", "").split())  # collapse whitespace/newlines

        authors = [Author(name=a["name"]) for a in entry.get("authors", [])]

        abstract_raw = entry.get("summary")
        abstract = " ".join(abstract_raw.split()) if abstract_raw else None

        published_date = _parse_dt(entry.get("published_parsed"))
        updated_date = _parse_dt(entry.get("updated_parsed"))

        # URL — prefer the alternate HTML link; fall back to entry.link
        url = entry.get("link", f"https://arxiv.org/abs/{arxiv_id}")
        pdf_url: str | None = None
        for link in entry.get("links", []):
            if link.get("rel") == "alternate":
                url = link["href"]
            elif link.get("type") == "application/pdf":
                pdf_url = link["href"]

        doi: str | None = entry.get("arxiv_doi") or None
        venue: str | None = entry.get("arxiv_journal_ref") or None
        categories = [t["term"] for t in entry.get("tags", [])]

        return Paper(
            id=f"arxiv:{arxiv_id}",
            title=title,
            authors=authors,
            abstract=abstract,
            published_date=published_date,
            updated_date=updated_date,
            url=url,
            pdf_url=pdf_url,
            doi=doi,
            arxiv_id=arxiv_id,
            venue=venue,
            categories=categories,
            citation_count=None,  # arXiv does not provide citation counts
            source="arxiv",
        )
