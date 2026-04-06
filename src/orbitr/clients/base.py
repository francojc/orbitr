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

from orbitr.core.models import Paper, SearchResult
from orbitr.exceptions import SourceError

logger = logging.getLogger(__name__)


def _http_error_message(source: str, status: int) -> tuple[str, str]:
    """Return a ``(message, suggestion)`` pair for a non-retryable HTTP error.

    Args:
        source: Human-readable source/client name.
        status: HTTP status code.

    Returns:
        Tuple of (message, suggestion) for :class:`SourceError`.
    """
    if status == 401:
        return (
            f"{source}: authentication required (HTTP 401).",
            "Run `orbitr init` to configure API credentials.",
        )
    if status == 403:
        return (
            f"{source}: access denied (HTTP 403 Forbidden).",
            (
                "This source may require an API key or your IP is being rate-limited. "
                "Run `orbitr init` to add a Semantic Scholar API key."
            ),
        )
    if status == 404:
        return (
            f"{source}: resource not found (HTTP 404).",
            "The requested paper or endpoint may not exist on this source.",
        )
    if status == 429:
        return (
            f"{source}: rate-limited (HTTP 429 Too Many Requests).",
            "Wait a moment then retry, or add an API key via `orbitr init`.",
        )
    if 500 <= status < 600:
        return (
            f"{source}: server error (HTTP {status}).",
            "The source API is temporarily unavailable. Try again in a few minutes.",
        )
    return (
        f"{source}: unexpected HTTP {status}.",
        "Run `orbitr doctor` to check source connectivity.",
    )


def _exhausted_retry_message(source: str, status: int) -> tuple[str, str]:
    """Return ``(message, suggestion)`` after all retries are exhausted.

    Distinguishes rate-limit exhaustion (429) from server-unavailability
    (5xx) so the user gets an actionable suggestion in both cases.
    """
    if status == 429:
        return (
            f"{source}: rate limit reached after repeated retries (HTTP 429).",
            (
                "Semantic Scholar allows ~1 request/second without an API key. "
                "Add a free API key with `orbitr init` for higher limits (10 req/s)."
            ),
        )
    return (
        f"{source} is unavailable (HTTP {status}).",
        "The source API may be temporarily down. Try again in a few minutes.",
    )


# 429/503: rate-limited or overloaded — always retry with backoff.
# 500/502/504: transient server errors — worth retrying.
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0  # seconds


class BaseClient(ABC):
    """Abstract base for all orbitr API clients."""

    #: Override in subclasses to set a per-source concurrency limit.
    _semaphore_limit: int = 5

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key
        self._semaphore = asyncio.Semaphore(self._semaphore_limit)
        self._circuit_open = False  # True = source is disabled for this invocation

    @property
    def _request_delay(self) -> float:
        """Seconds to sleep before each outgoing request.

        Override in subclasses that need proactive rate limiting.
        Default is 0 (no delay).
        """
        return 0.0

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

        cls_name = self.__class__.__name__

        # Proactive rate-limit: sleep before the first attempt so we stay
        # within the source's requests-per-second budget without relying
        # solely on reactive 429 backoff.
        if delay := self._request_delay:
            await asyncio.sleep(delay)

        async with self._semaphore, httpx.AsyncClient(timeout=15.0) as client:
            for attempt in range(_MAX_RETRIES):
                try:
                    resp = await client.get(url, params=params, headers=_headers)

                    if resp.status_code in _RETRY_STATUSES:
                        if attempt < _MAX_RETRIES - 1:
                            wait = _BACKOFF_BASE * (2**attempt)
                            logger.debug(
                                "%s: HTTP %s — retrying in %.1fs (attempt %d/%d).",
                                cls_name,
                                resp.status_code,
                                wait,
                                attempt + 1,
                                _MAX_RETRIES,
                            )
                            await asyncio.sleep(wait)
                            continue
                        # Exhausted retries on a retryable status.
                        raise SourceError(
                            *_exhausted_retry_message(cls_name, resp.status_code),
                        )

                    # Non-retryable HTTP errors: convert to SourceError immediately.
                    if not resp.is_success:
                        raise SourceError(
                            *_http_error_message(cls_name, resp.status_code),
                        )

                    return resp

                except SourceError:
                    raise  # already formatted — propagate as-is
                except httpx.RequestError as exc:
                    if attempt == _MAX_RETRIES - 1:
                        self._circuit_open = True
                        raise SourceError(
                            f"{cls_name}: network error — {type(exc).__name__}.",
                            suggestion="Check your internet connection and try again.",
                        ) from exc
                    wait = _BACKOFF_BASE * (2**attempt)
                    await asyncio.sleep(wait)

        # Should not reach here, but satisfy type checker.
        raise SourceError(f"{cls_name}: exhausted retries.")  # pragma: no cover

    def _default_headers(self) -> dict[str, str]:
        """Return default HTTP headers. Override in subclasses as needed."""
        return {"User-Agent": "orbitr/0.1.0 (https://github.com/francojc/orbitr)"}
