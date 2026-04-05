"""Abstract base client: retry, rate limiting, and circuit breaking.

All source clients extend BaseClient and inherit:
- Exponential backoff retry on 429 / 503 (3 attempts: 1 s, 2 s, 4 s)
- Per-source rate limiting via asyncio.Semaphore
- Circuit-break per source so partial failures degrade gracefully
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

import httpx

from lumen.core.models import Paper, SearchResult
from lumen.exceptions import SourceError

logger = logging.getLogger(__name__)

_RETRY_STATUSES = {429, 503}
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0  # seconds


class BaseClient(ABC):
    """Abstract base for all lumen API clients."""

    #: Override in subclasses to set a per-source concurrency limit.
    _semaphore_limit: int = 5

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key
        self._semaphore = asyncio.Semaphore(self._semaphore_limit)
        self._circuit_open = False  # True = source is disabled for this invocation

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def search(self, query: str, max_results: int = 10, **kwargs) -> SearchResult:
        """Execute a search query and return a SearchResult.

        Args:
            query: Search string.
            max_results: Maximum number of results to return.
            **kwargs: Source-specific filter arguments.

        Returns:
            SearchResult containing matched papers.
        """

    @abstractmethod
    async def get_by_id(self, paper_id: str) -> Paper:
        """Fetch a single paper by its source-specific identifier.

        Args:
            paper_id: Source-specific paper ID (arXiv ID, Semantic Scholar ID, DOI).

        Returns:
            Paper with all available metadata.
        """

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    async def _get(
        self, url: str, params: dict | None = None, headers: dict | None = None
    ) -> httpx.Response:
        """GET with retry/backoff. Raises SourceError after exhausted retries.

        Args:
            url: Request URL.
            params: Query parameters.
            headers: Additional HTTP headers.

        Returns:
            Successful httpx.Response.

        Raises:
            SourceError: On network failure or exhausted retries.
        """
        if self._circuit_open:
            raise SourceError(
                f"{self.__class__.__name__} is unavailable (circuit open).",
                suggestion="Try --sources to select an alternative source.",
            )

        _headers = self._default_headers()
        if headers:
            _headers.update(headers)

        async with self._semaphore, httpx.AsyncClient(timeout=15.0) as client:
            for attempt in range(_MAX_RETRIES):
                try:
                    resp = await client.get(url, params=params, headers=_headers)
                    if resp.status_code in _RETRY_STATUSES:
                        wait = _BACKOFF_BASE * (2**attempt)
                        logger.debug(
                            "Rate-limited (%s). Retrying in %.1fs.",
                            resp.status_code,
                            wait,
                        )
                        await asyncio.sleep(wait)
                        continue
                    resp.raise_for_status()
                    return resp
                except httpx.RequestError as exc:
                    if attempt == _MAX_RETRIES - 1:
                        self._circuit_open = True
                        raise SourceError(
                            f"Network error contacting {self.__class__.__name__}: {exc}",
                            suggestion="Check your internet connection and try again.",
                        ) from exc
                    wait = _BACKOFF_BASE * (2**attempt)
                    await asyncio.sleep(wait)

        # Should not reach here, but satisfy type checker.
        raise SourceError(
            f"{self.__class__.__name__}: exhausted retries."
        )  # pragma: no cover

    def _default_headers(self) -> dict[str, str]:
        """Return default HTTP headers. Override in subclasses as needed."""
        return {"User-Agent": "lumen/0.1.0 (https://github.com/francojc/lumen)"}
