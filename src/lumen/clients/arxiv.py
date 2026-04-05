"""arXiv API client — Atom feed via feedparser.

Rate limit: 3 requests/second (enforced by semaphore + sleep).
"""

from __future__ import annotations

from lumen.clients.base import BaseClient
from lumen.core.models import Paper, SearchResult


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
        # TODO: implement in Phase 2
        raise NotImplementedError

    async def get_by_id(self, paper_id: str) -> Paper:
        """Fetch a paper by arXiv ID.

        Args:
            paper_id: arXiv ID (e.g. "1706.03762" or "abs/1706.03762").

        Returns:
            Paper with arXiv metadata.
        """
        # TODO: implement in Phase 2
        raise NotImplementedError

    def _parse_entry(self, entry: dict) -> Paper:
        """Parse a feedparser entry into a Paper model.

        Args:
            entry: Single feedparser entry dict.

        Returns:
            Paper instance.
        """
        # TODO: implement in Phase 2
        raise NotImplementedError
