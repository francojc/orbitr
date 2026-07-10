"""Karakeep REST API client for private bookmark search."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from orbitr.clients.base import BaseClient
from orbitr.config import normalize_server_url
from orbitr.core.models import Paper, SearchResult
from orbitr.exceptions import ConfigError, SourceError


class KarakeepClient(BaseClient):
    """Read-only client for the Karakeep bookmark search API."""

    def __init__(self, api_key: str, server_url: str) -> None:
        if not api_key:
            raise ConfigError(
                "Karakeep API credentials are not configured.",
                suggestion="Run `orbitr init` or set KARAKEEP_API_KEY.",
            )
        try:
            self.server_url = normalize_server_url(server_url)
        except ValueError as exc:
            raise ConfigError(
                "Karakeep server URL is invalid.",
                suggestion="Set KARAKEEP_SERVER_URL to an http(s) URL, or use `--server`.",
            ) from exc
        super().__init__(api_key=api_key)

    def _default_headers(self) -> dict[str, str]:
        headers = super()._default_headers()
        headers["Authorization"] = f"Bearer {self.api_key}"
        headers["Accept"] = "application/json"
        return headers

    async def search(
        self, query: str, max_results: int = 10, **kwargs: Any
    ) -> SearchResult:
        """Search saved bookmarks."""
        return await self.search_bookmarks(query, max_results)

    async def get_by_id(self, paper_id: str) -> Paper:
        """Karakeep has no paper-by-ID contract in this integration."""
        raise SourceError(
            "Karakeep does not support fetching bookmarks by ID.",
            suggestion="Use `orbitr karakeep search` to locate the bookmark.",
        )

    async def search_bookmarks(self, query: str, limit: int = 10) -> SearchResult:
        """Search bookmarks through ``/api/search-bookmarks``."""
        response = await self._get(
            f"{self.server_url}/api/search-bookmarks",
            params={"q": query, "limit": min(limit, 100)},
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise SourceError(
                "Karakeep returned malformed JSON.",
                suggestion="Retry the command; check the configured server version.",
            ) from exc
        if not isinstance(payload, dict):
            raise SourceError(
                "Karakeep returned an invalid search response.",
                suggestion="Retry the command; check the configured server version.",
            )
        raw_items = payload.get("data", payload.get("bookmarks"))
        if raw_items is None:
            raw_items = []
        if not isinstance(raw_items, list):
            raise SourceError(
                "Karakeep returned an invalid bookmark list.",
                suggestion="Retry the command; check the configured server version.",
            )

        papers: list[Paper] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            try:
                papers.append(self._parse_bookmark(item))
            except (KeyError, TypeError, ValueError):
                continue
        if raw_items and not papers:
            raise SourceError(
                "Karakeep returned no usable bookmark records.",
                suggestion="The server response may have changed; check its API version.",
            )
        total = payload.get("total", payload.get("totalCount", len(papers)))
        return SearchResult(
            papers=papers,
            total_count=total if isinstance(total, int) else len(papers),
            query=query,
            sources=["karakeep"],
        )

    @staticmethod
    def _parse_bookmark(item: dict[str, Any]) -> Paper:
        """Map one Karakeep bookmark into the shared Paper model."""
        bookmark_id = str(item.get("id") or item.get("key") or "")
        title = str(item.get("title") or item.get("url") or "(untitled bookmark)")
        url = str(item.get("url") or "")
        if not bookmark_id or not url:
            raise ValueError("bookmark requires id and url")
        content = item.get("content")
        if isinstance(content, dict):
            abstract = content.get("text") or content.get("excerpt")
        else:
            abstract = item.get("excerpt") or item.get("text")
        tags_raw = item.get("tags", [])
        tags = []
        if isinstance(tags_raw, list):
            for tag in tags_raw:
                if isinstance(tag, str):
                    tags.append(tag)
                elif isinstance(tag, dict) and tag.get("name"):
                    tags.append(str(tag["name"]))
        date_value = item.get("createdAt") or item.get("created_at")
        published = None
        if isinstance(date_value, str):
            try:
                published = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        return Paper(
            id=f"karakeep:{bookmark_id}",
            title=title,
            authors=[],
            abstract=str(abstract) if abstract else None,
            published_date=published,
            url=url,
            categories=tags,
            source="karakeep",
        )
