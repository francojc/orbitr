"""Semantic Scholar REST API client.

Rate limits:
  Without API key: 100 req/5 min (conservative default)
  With API key:    100 req/min
"""

from __future__ import annotations

from lumen.clients.base import BaseClient
from lumen.core.models import Paper, SearchResult

_PAPER_FIELDS = (
    "paperId,title,authors,abstract,year,publicationDate,"
    "venue,externalIds,citationCount,url,openAccessPdf"
)
_AUTHOR_FIELDS = "authorId,name,affiliations"


class SemanticScholarClient(BaseClient):
    """Client for the Semantic Scholar Graph API v1."""

    _semaphore_limit = 5
    _BASE_URL = "https://api.semanticscholar.org/graph/v1"

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
        # TODO: implement in Phase 2
        raise NotImplementedError

    async def get_by_id(self, paper_id: str) -> Paper:
        """Fetch a paper by Semantic Scholar ID, DOI, or arXiv ID.

        Accepts prefixes: "DOI:", "ARXIV:", or bare Semantic Scholar paper ID.

        Args:
            paper_id: Paper identifier.

        Returns:
            Paper with Semantic Scholar metadata.
        """
        # TODO: implement in Phase 2
        raise NotImplementedError

    async def get_citations(self, paper_id: str, limit: int = 100) -> list[Paper]:
        """Retrieve papers that cite a given paper.

        Args:
            paper_id: Semantic Scholar paper ID.
            limit: Maximum number of citing papers.

        Returns:
            List of citing Paper instances.
        """
        # TODO: implement in Phase 2
        raise NotImplementedError

    async def get_recommendations(self, paper_id: str, limit: int = 10) -> list[Paper]:
        """Retrieve recommended papers from the Recommendations API.

        Args:
            paper_id: Seed Semantic Scholar paper ID.
            limit: Number of recommendations.

        Returns:
            List of recommended Paper instances.
        """
        # TODO: implement in Phase 2
        raise NotImplementedError

    def _parse_paper(self, data: dict) -> Paper:
        """Parse a Semantic Scholar API paper dict into a Paper model.

        Args:
            data: Raw API response dict for a single paper.

        Returns:
            Paper instance.
        """
        # TODO: implement in Phase 2
        raise NotImplementedError
